"""
AI翻译模块 - 将自然语言指令翻译成结构化的工具调用
这是"大脑"，负责理解用户意图

Author: TJxiaobao
License: MIT
Version: 0.0.6
"""

from openai import OpenAI
from typing import List, Dict, Any, Optional
import json
import logging

from ..config.settings import config
from ..prompts.manager import get_prompt, get_all_tools, get_tools_by_names, get_tool_groups, get_routing_config
from ..models.ai_response import (
    AIResponse,
    create_tool_calls_response,
    create_clarification_response,
    create_help_response,
    create_friendly_message_response,
    create_task_list_response,
    create_error_response
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AIUnderstandingError(Exception):
    """AI 理解失败异常 - 用于触发上下文重试机制"""
    pass


class AITranslator:
    """AI翻译器 - 使用LLM的Function Calling能力
    
    新增：三阶段 AI 架构
    - 阶段1：总指挥（Coordinator）- 拆分复合指令
    - 阶段2-3：路由 + 专家（现有逻辑）
    """
    
    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化AI翻译器
        Args:
            api_key: API密钥，如果为None则从配置读取
            base_url: API基础URL，支持兼容OpenAI接口的服务
        """
        self.api_key = api_key or config.OPENAI_API_KEY
        self.base_url = base_url or config.OPENAI_API_BASE
        
        if not self.api_key:
            raise ValueError("请设置OPENAI_API_KEY环境变量")
        
        # 禁用OpenAI SDK的自动重试，我们自己控制重试逻辑
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            max_retries=0  # ⭐️ 禁用自动重试
        )
        
        # 智能选择模型
        self.model = self._select_model()
        logger.info(f"AI翻译器初始化完成，使用API: {self.base_url}")
        logger.info(f"使用模型: {self.model}")
    
    def _select_model(self) -> str:
        """
        根据 API Base URL 智能选择模型
        Returns:
            模型名称
        """
        if "moonshot" in self.base_url.lower():
            # Kimi / 月之暗面
            return "moonshot-v1-8k"
        elif "deepseek" in self.base_url.lower():
            # DeepSeek
            return "deepseek-chat"
        else:
            # OpenAI 或其他
            return "gpt-4o-mini"
    
    def _get_tool_groups(self) -> Dict[str, Any]:
        """获取工具分组配置"""
        try:
            return get_tool_groups()
        except:
            # 如果加载失败，返回空字典
            logger.warning("⚠️ 工具分组配置加载失败，将使用所有工具")
            return {}
    
    def _detect_tool_group(self, command: str) -> Optional[str]:
        """
        根据关键词检测用户指令属于哪个工具组
        Args:
            command: 用户指令
        Returns:
            工具组名称，如果未匹配则返回None
        """
        command_lower = command.lower()
        tool_groups = self._get_tool_groups()
        
        for group_name, group_data in tool_groups.items():
            for keyword in group_data["keywords"]:
                if keyword in command_lower:
                    logger.info(f"关键词路由命中: '{keyword}' → {group_name} 组")
                    return group_name
        return None
    
    def get_tools_definition(self, filter_tools: Optional[List[str]] = None) -> List[Dict]:
        """
        获取可用的工具（Function Calling的schema）
        这是告诉AI它可以使用哪些工具
        
        Args:
            filter_tools: 可选的工具名称列表，如果提供则只返回这些工具
        
        注意：为了兼容不同的AI服务（Kimi不支持数组类型定义），
        这里统一使用string类型，AI会自动处理数字
        """
        # ✅ 从 YAML 加载，代码极度干净！
        if filter_tools:
            filtered = get_tools_by_names(filter_tools)
            logger.info(f"工具过滤：使用 {len(filtered)} 个工具")
            logger.info(f"当前使用工具: {[t['function']['name'] for t in filtered]}")
            return filtered
        
        all_tools = get_all_tools()
        logger.info(f"使用所有工具：{len(all_tools)} 个")
        return all_tools

    def build_system_prompt(self, headers: List[str], expert_type: str = None) -> str:
        """
        构建系统提示词（基础信息 + 专家提示词）
        Args:
            headers: 用户表格的列名列表
            expert_type: 专家类型（填充/数学/清洗等），如果为None则只返回基础提示词
        Returns:
            系统提示词
        """
        # ⭐️ 使用新的通用基础提示词，说明表格列名和基本规则
        base_prompt = get_prompt('system_prompts.general_base', headers=', '.join(headers))
        
        # 如果指定了专家类型，追加专家提示词
        if expert_type:
            expert_prompt = get_prompt(f'system_prompts.{expert_type}_expert')
            return base_prompt + "\n\n" + expert_prompt
        
        return base_prompt
    
    def _is_complex_command(self, command: str) -> bool:
        """
        智能判断是否是复合指令（需要总指挥拆分）
        
        Args:
            command: 用户输入的指令
        
        Returns:
            True 如果是复合指令，False 如果是简单指令
        """
        # 从 YAML 加载复合指令标记
        routing_config = get_routing_config()
        complex_markers = routing_config.get('complex_markers', [])
        
        command_lower = command.lower()
        
        for marker in complex_markers:
            if marker.lower() in command_lower:
                logger.info(f"🔍 检测到复合指令标记: '{marker}'")
                return True
        
        # 简单指令（长度 < 50 且没有特征）
        if len(command) < 50:
            logger.info("✅ 指令较短且无复合特征，判定为简单指令")
            return False
        
        logger.info("⚠️  指令较长，走总指挥路径以确保准确")
        return True
    
    def _is_contextual_command(self, command: str, history: List[Dict[str, str]] = None) -> bool:
        """
        智能判断是否是依赖上下文的指令（增强版）
        
        Args:
            command: 用户输入的指令
            history: 历史对话记录
        
        Returns:
            True 如果依赖上下文，False 如果不依赖
        """
        # 从 YAML 加载上下文依赖标记
        routing_config = get_routing_config()
        contextual_markers = routing_config.get('contextual_markers', [])
        
        command_lower = command.lower()
        
        # 1. 检查强制上下文标记（代词）
        for marker in contextual_markers:
            if marker.lower() in command_lower:
                logger.info(f"🔍 检测到上下文依赖标记: '{marker}'")
                return True
        
        # 2. ⭐️ 新增：延续性词汇检测
        continuation_markers = ["也", "还", "再", "同样", "一样", "继续", "接着", "另外", "同时"]
        for marker in continuation_markers:
            if marker in command:
                logger.info(f"🔍 检测到延续性词汇: '{marker}'")
                return True
        
        # 3. ⭐️ 智能上下文推断：如果指令包含引号，很可能在引用刚才的结果
        import re
        quoted_terms = re.findall(r'["""](.*?)["""]', command)
        if quoted_terms and history and len(history) > 0:
            logger.info(f"🧠 智能上下文推断: 指令包含引用 '{quoted_terms[0]}'，可能引用历史结果")
            return True
        
        # 4. ⭐️ 新增：短指令倾向检测（指令很短时，更可能依赖上下文）
        # 阈值设为7：像"改为10"（4字符）会被判为依赖上下文，但"把税率设为0.13"（9字符）不会
        # todo 过于生硬
        if len(command) < 7 and history and len(history) > 0:
            logger.info(f"🧠 短指令检测: 指令长度 {len(command)} < 7，倾向携带上下文")
            return True
        
        logger.info("✅ 未检测到明显上下文依赖特征")
        return False
    
    def _call_coordinator(self, command: str, history: List[Dict[str, str]] = None) -> Optional[List[str]]:
        """
        调用总指挥 AI 拆分复合指令
        
        Args:
            command: 用户的复合指令
            history: 历史对话记录（可选）
        
        Returns:
            拆分后的指令列表，如果拆分失败返回 None
        """
        try:
            logger.info("🎯 调用总指挥（Coordinator）拆分指令")
            
            # 从 YAML 加载总指挥的 prompt 和 tools
            coordinator_prompt = get_prompt('system_prompts.coordinator')
            coordinator_tools = get_tools_by_names(['execute_tasks_in_order'])
            
            # 构造消息列表（可能包含历史）
            messages = [{"role": "system", "content": coordinator_prompt}]
            
            if history:
                logger.info(f"📚 注入历史上下文，共 {len(history)} 条消息")
                messages.extend(history)
            
            messages.append({"role": "user", "content": command})
            
            # 输出完整的 AI 请求日志
            logger.info("=" * 60)
            logger.info("📤 AI 请求 (Coordinator)")
            logger.info(f"Model: {self.model}")
            logger.info(f"Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
            logger.info("=" * 60)
            
            # 调用 AI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=coordinator_tools,
                tool_choice={
                    "type": "function",
                    "function": {"name": "execute_tasks_in_order"}
                }  # 强制调用指定工具，不允许文本回复
            )

            message = response.choices[0].message
            
            # 输出 AI 响应日志
            logger.info("=" * 60)
            logger.info("📥 AI 响应 (Coordinator)")
            logger.info(f"Finish Reason: {response.choices[0].finish_reason}")
            logger.info(f"Has Tool Calls: {bool(message.tool_calls)}")
            if message.tool_calls:
                for tc in message.tool_calls:
                    logger.info(f"Tool: {tc.function.name}")
                    logger.info(f"Arguments: {tc.function.arguments}")
            logger.info("=" * 60)
            
            # 检查是否调用了工具
            if not message.tool_calls:
                logger.warning("总指挥未调用工具，降级为单一指令处理")
                return None
            
            # 解析工具调用
            tool_call = message.tool_calls[0]
            if tool_call.function.name == "execute_tasks_in_order":
                args = json.loads(tool_call.function.arguments)
                tasks = args.get("tasks", [])
                
                if not tasks:
                    logger.warning("总指挥返回空任务列表")
                    return None
                
                logger.info(f"🎯 任务拆分成功，共 {len(tasks)} 个子任务:")
                for i, task in enumerate(tasks, 1):
                    logger.info(f"  {i}. {task}")
                
                return tasks
            else:
                logger.warning(f"总指挥调用了错误的工具: {tool_call.function.name}")
                return None
                
        except Exception as e:
            logger.error(f"总指挥调用失败: {e}")
            return None
    
    def _call_ai_router(self, command: str) -> Optional[str]:
        """
        调用 AI 路由来决定工具组（两级路由的第二级）
        
        Args:
            command: 用户的指令
        
        Returns:
            工具组名称（filling/math/cleaning/text/date/structure/analysis），如果失败返回 None
        """
        try:
            logger.info("🤖 调用 AI 路由（关键词未命中，使用 AI 兜底）")
            
            # 从 YAML 加载路由 AI 的 prompt 和 tools
            router_prompt = get_prompt('system_prompts.router')
            router_tool_names = [
                'route_to_filling',
                'route_to_math',
                'route_to_cleaning',
                'route_to_text',
                'route_to_date',
                'route_to_structure',
                'route_to_analysis'
            ]
            router_tools = get_tools_by_names(router_tool_names)
            
            # 构造消息
            messages = [
                {"role": "system", "content": router_prompt},
                {"role": "user", "content": command}
            ]
            
            # 输出 AI 请求日志
            logger.info("=" * 60)
            logger.info("📤 AI 请求 (Router)")
            logger.info(f"Model: {self.model}")
            logger.info(f"Command: {command}")
            logger.info("=" * 60)
            
            # 调用 AI
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=router_tools,
                tool_choice="required"  # 强制调用工具
            )
            
            message = response.choices[0].message
            
            # 输出 AI 响应日志
            logger.info("=" * 60)
            logger.info("📥 AI 响应 (Router)")
            logger.info(f"Finish Reason: {response.choices[0].finish_reason}")
            if message.tool_calls:
                tool_name = message.tool_calls[0].function.name
                logger.info(f"Tool: {tool_name}")
            logger.info("=" * 60)
            
            # 检查是否调用了工具
            if not message.tool_calls:
                logger.warning("AI 路由未调用工具")
                return None
            
            # 解析工具名：route_to_filling → filling
            tool_call = message.tool_calls[0]
            tool_name = tool_call.function.name
            
            if tool_name.startswith("route_to_"):
                group_name = tool_name.replace("route_to_", "")
                logger.info(f"🎯 AI 路由结果: {group_name}")
                return group_name
            else:
                logger.warning(f"AI 路由返回了错误的工具: {tool_name}")
                return None
                
        except Exception as e:
            logger.error(f"AI 路由调用失败: {e}")
            return None
    
    def translate_single_task(self, user_command: str, headers: List[str], history: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """
        公开方法：翻译单个任务（供WebSocket调用）
        """
        return self._translate_single_task(user_command, headers, history)
    
    def _translate_single_task(self, user_command: str, headers: List[str], history: List[Dict[str, str]] = None) -> AIResponse:
        """
        翻译单个任务为工具调用（内部方法）
        
        这是原来的 translate() 逻辑，现在作为子函数被新的 translate() 调用
        
        Args:
            user_command: 用户的自然语言指令（单一任务）
            headers: 表格的列名列表
            history: 历史对话记录
        Returns:
            AIResponse: 统一的响应对象
        """
        try:
            
            # 检查是否是帮助指令
            help_keywords = ["帮助", "help", "你能做什么", "有什么功能", "怎么用", "功能列表"]
            if user_command.strip().lower() in help_keywords:
                logger.info("用户请求帮助信息")
                # ✅ 从 YAML 加载，代码干净！
                help_message = get_prompt('help_messages.main')
                return create_help_response(help_message)
            
            # ⭐️ 两级路由优化 - 关键词优先，AI 兜底
            # 第一级：关键词路由（快速，0 延迟）
            detected_group = self._detect_tool_group(user_command)
            
            if detected_group:
                # 命中关键词，只使用该组的工具
                tool_groups = self._get_tool_groups()
                filter_tools = tool_groups[detected_group]["tools"]
                tools = self.get_tools_definition(filter_tools=filter_tools)
                logger.info(f"✅ 【第一级路由】关键词命中: {detected_group}，Token预计减少 60-70%")
            else:
                # 第二级：AI 路由（智能兜底）
                logger.info("⚠️ 【第一级路由】关键词未命中，启动第二级 AI 路由")
                ai_routed_group = self._call_ai_router(user_command)
                
                if ai_routed_group:
                    # AI 路由成功
                    tool_groups = self._get_tool_groups()
                    filter_tools = tool_groups[ai_routed_group]["tools"]
                    tools = self.get_tools_definition(filter_tools=filter_tools)
                    logger.info(f"✅ 【第二级路由】AI 路由成功: {ai_routed_group}，Token预计减少 60-70%")
                else:
                    # AI 路由也失败，降级到所有工具（最后兜底）
                    tools = self.get_tools_definition()
                    logger.info("⚠️ 【第二级路由】AI 路由失败，降级使用全量工具")
            
            # 构造消息列表（可能包含历史）
            messages = [{"role": "system", "content": self.build_system_prompt(headers)}]
            
            if history:
                logger.info(f"📚 注入历史上下文，共 {len(history)} 条消息")
                messages.extend(history)
            
            messages.append({"role": "user", "content": user_command})
            
            # 输出完整的 AI 请求日志
            logger.info("=" * 60)
            logger.info("📤 AI 请求 (Single Task)")
            logger.info(f"Model: {self.model}")
            logger.info(f"Messages: {json.dumps(messages, ensure_ascii=False, indent=2)}")
            logger.info(f"Tools Count: {len(tools)}")
            logger.info("=" * 60)
            
            # 调用AI
            response = self.client.chat.completions.create(
                model=self.model,  # 根据API自动选择模型
                messages=messages,
                tools=tools,
                tool_choice="auto"  # 让AI自动决用是否使用工具
            )
            
            message = response.choices[0].message
            
            # 输出 AI 响应日志
            logger.info("=" * 60)
            logger.info("📥 AI 响应 (Single Task)")
            logger.info(f"Finish Reason: {response.choices[0].finish_reason}")
            logger.info(f"Has Tool Calls: {bool(message.tool_calls)}")
            if message.tool_calls:
                for tc in message.tool_calls:
                    logger.info(f"Tool: {tc.function.name}")
                    logger.info(f"Arguments: {tc.function.arguments}")
            if message.content:
                logger.info(f"Content: {message.content}")
            logger.info("=" * 60)
            
            # ⭐️ 使用统一的转换器（方案3优化）
            return AIResponse.from_openai_response(message)
            
        except Exception as e:
            error_msg = f"AI翻译失败: {str(e)}"
            logger.error(error_msg)
            return create_error_response(error_msg, error_code="TRANSLATION_FAILED")
    
    def translate(self, user_command: str, headers: List[str], history: List[Dict[str, str]] = None) -> List[AIResponse]:
        """
        【新】主入口：翻译用户指令为工具调用列表
        
        实现三阶段 AI 架构 + 智能分流 + 上下文感知路由：
        1. 智能判断：是简单指令还是复合指令？是否依赖上下文？
        2. 简单指令 + 无上下文依赖：直接走快速路径（_translate_single_task，无history）
        3. 简单指令 + 有上下文依赖：走快速路径但带上 history
        4. 复合指令：走总指挥路径（拆分 → 循环翻译）
        
        Args:
            user_command: 用户的自然语言指令（可能是单一或复合指令）
            headers: 表格的列名列表
            history: 历史对话记录（可选）
        
        Returns:
            指令列表，每个元素是一个 Dict，包含 success、tool_calls 等
            格式：[{"success": True, "tool_calls": [...]}, ...]
        """
        try:
            logger.info(f"📝 收到指令: {user_command}")
            
            # 第一步：智能判断是否是复合指令
            is_complex = self._is_complex_command(user_command)
            
            # 第二步：智能判断是否依赖上下文
            is_contextual = self._is_contextual_command(user_command, history=history)
            
            # 第三步：决策路由
            if not is_complex and not is_contextual:
                # 【路径 A】简单指令 + 无明显上下文依赖
                # ⭐️ 优化：携带最近1轮历史（而不是全部历史），提高准确性且控制 Token
                recent_history = history[-2:] if history and len(history) >= 2 else history
                
                # 改进日志：即使是空历史也要说明策略
                if recent_history and len(recent_history) > 0:
                    logger.info(f"🚀 【路径 A】简单指令，携带最近1轮历史（共{len(recent_history)}条消息）")
                else:
                    logger.info("🚀 【路径 A】简单指令（首次请求，无历史）→ 后续将自动携带最近1轮")
                
                result = self._translate_single_task(user_command, headers, history=recent_history)
                return [result]
            
            elif not is_complex and is_contextual:
                # 【路径 B】简单但依赖上下文的指令（如"把它们改为0.1"）
                logger.info(f"🧠 【路径 B】简单指令 + 明显依赖上下文，直接翻译（带完整 history，共{len(history) if history else 0}条）")
                result = self._translate_single_task(user_command, headers, history=history)
                return [result]
            
            else:
                # 【路径 C】复合指令，走总指挥路径
                logger.info("🎯 【路径 C】复合指令，调用总指挥拆分")
                tasks = self._call_coordinator(user_command, history=history)
                
                if not tasks or len(tasks) == 1:
                    # 总指挥拆分失败或只有一个任务，降级到路径 B
                    logger.info("降级为单一指令处理（带 history）")
                    result = self._translate_single_task(user_command, headers, history=history)
                    return [result]
                
                # ⭐️ 返回子任务列表，让上层（WebSocket）控制翻译节奏和实时显示
                logger.info(f"🔄 已拆分为 {len(tasks)} 个子任务")
                from ..models.ai_response import create_task_list_response
                return [create_task_list_response(tasks)]  # 返回包含任务列表的 AIResponse
            
        except Exception as e:
            error_str = str(e)
            
            # ⭐️ 如果是429错误，直接抛出让上层（WebSocket）处理重试
            if "429" in error_str or "rate_limit" in error_str.lower():
                logger.warning(f"⏳ 检测到429限流错误，抛出异常触发重试")
                raise  # 重新抛出异常
            
            # 其他错误，返回错误结果
            logger.error(f"translate() 主方法失败: {e}")
            return [create_error_response(
                f"指令翻译失败: {str(e)}",
                error_code="TRANSLATE_FAILED"
            )]


# 创建全局翻译器实例（延迟初始化）
_translator_instance = None

def get_translator() -> AITranslator:
    """获取AI翻译器单例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = AITranslator()
    return _translator_instance

