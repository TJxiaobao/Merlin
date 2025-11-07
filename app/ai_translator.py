"""
AI翻译模块 - 将自然语言指令翻译成结构化的工具调用
这是"大脑"，负责理解用户意图

Author: TJxiaobao
License: MIT
"""
from openai import OpenAI
from typing import List, Dict, Any, Optional
import json
import logging

from .config import config
from .prompts.manager import get_prompt, get_all_tools, get_tools_by_names

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# 工具分组定义 - 用于关键词路由优化
TOOL_GROUPS = {
    "filling": {
        "keywords": ["设为", "改为", "修改", "复制", "填充", "设置", "全部", "所有"],
        "tools": ["set_column_value", "set_by_condition", "copy_column", "set_by_mapping"]
    },
    "math": {
        "keywords": ["计算", "乘以", "除以", "加", "减", "总价", "利润", "等于", "加上", "减去", "×", "÷", "+", "-"],
        "tools": ["perform_math"]
    },
    "cleaning": {
        "keywords": ["清理", "替换", "空格", "空白", "填充为", "查找", "改成"],
        "tools": ["trim_whitespace", "fill_missing_values", "find_and_replace"]
    },
    "text": {  # v0.0.4 扩展
        "keywords": ["合并", "拆分", "连接", "分割", "大写", "小写", "首字母", "按...拆分", "转为大写", "转为小写"],
        "tools": ["concatenate_columns", "split_column", "change_case"]
    },
    "date": {  # v0.0.4-alpha
        "keywords": ["日期", "年份", "月份", "季度", "星期", "提取"],
        "tools": ["extract_date_part"]
    },
    "structure": {  # v0.0.4-beta 新增
        "keywords": ["删除重复", "去重", "排序", "升序", "降序", "从高到低", "从低到高"],
        "tools": ["drop_duplicates", "sort_by_column"]
    },
    "analysis": {  # v0.0.4-alpha
        "keywords": ["统计", "分布", "总结", "查看", "有哪些", "分析", "汇总", "分组", "聚合", "平均", "求和"],
        "tools": ["get_summary", "group_by_aggregate"]
    }
}


class AITranslator:
    """AI翻译器 - 使用LLM的Function Calling能力"""
    
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
        
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
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
    
    def _detect_tool_group(self, command: str) -> Optional[str]:
        """
        根据关键词检测用户指令属于哪个工具组
        Args:
            command: 用户指令
        Returns:
            工具组名称，如果未匹配则返回None
        """
        command_lower = command.lower()
        for group_name, group_data in TOOL_GROUPS.items():
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
    
    def get_tools_definition_old_hardcoded(self, filter_tools: Optional[List[str]] = None) -> List[Dict]:
        """
        【已废弃】原来的硬编码版本，保留作为备份
        """
        all_tools_hardcoded = [
            {
                "type": "function",
                "function": {
                    "name": "set_column_value",
                    "description": "给整列赋值，所有行都会被设置为相同的值",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要设置的列名（必须是用户表格中实际存在的列名）"
                            },
                            "value": {
                                "type": "string",
                                "description": "要设置的值，可以是数字（如0.13、100）或文本"
                            }
                        },
                        "required": ["column", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_by_condition",
                    "description": "根据条件筛选行，然后给这些行的指定列赋值",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_column": {
                                "type": "string",
                                "description": "作为条件的列名"
                            },
                            "condition_value": {
                                "type": "string",
                                "description": "条件值，可以是数字或文本"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "要修改的目标列名"
                            },
                            "target_value": {
                                "type": "string",
                                "description": "要设置的目标值，可以是数字（如0.13、100）或文本"
                            },
                            "match_type": {
                                "type": "string",
                                "enum": ["exact", "startswith", "contains"],
                                "description": "匹配类型: exact(精确匹配), startswith(前缀匹配), contains(包含匹配)",
                                "default": "exact"
                            }
                        },
                        "required": ["condition_column", "condition_value", "target_column", "target_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "copy_column",
                    "description": "将一列的值复制到另一列",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_column": {
                                "type": "string",
                                "description": "源列名"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "目标列名"
                            }
                        },
                        "required": ["source_column", "target_column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_by_mapping",
                    "description": "根据映射表批量设置列值。适用场景：同一列的多个不同值需要设置为不同的目标值。例如：'把设备编码为xxxx的价格设为10，yyy的设为20，zzz的设为30'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "condition_column": {
                                "type": "string",
                                "description": "作为条件的列名"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "要修改的目标列名"
                            },
                            "mapping": {
                                "type": "object",
                                "description": "映射关系，键为条件值，值为目标值。例如: {\"xxxx\": \"10\", \"yyy\": \"20\"}。注意：所有值都使用字符串格式"
                            },
                            "match_type": {
                                "type": "string",
                                "enum": ["exact", "startswith", "contains"],
                                "description": "匹配类型: exact(精确匹配), startswith(前缀匹配), contains(包含匹配)",
                                "default": "exact"
                            }
                        },
                        "required": ["condition_column", "target_column", "mapping"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_summary",
                    "description": "统计某列的数据分布情况。适用场景：用户想知道某个字段有哪些值，每个值有多少条数据。例如：'统计设备类型的分布'、'帮我总结设备编码的情况'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要统计的列名"
                            },
                            "top_n": {
                                "type": "string",
                                "description": "返回前N个最常见的值，默认10",
                                "default": "10"
                            }
                        },
                        "required": ["column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "perform_math",
                    "description": "执行数学计算。适用场景：需要对列进行数学运算。例如：'让总价等于数量乘以单价'、'计算利润等于售价减成本'、'把未税单价乘以1.13存入含税单价'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_column": {
                                "type": "string",
                                "description": "结果存储的目标列名（可以是新列或现有列）"
                            },
                            "source_column_1": {
                                "type": "string",
                                "description": "第一个操作数的列名"
                            },
                            "operator": {
                                "type": "string",
                                "enum": ["add", "subtract", "multiply", "divide"],
                                "description": "运算符: add(加), subtract(减), multiply(乘), divide(除)"
                            },
                            "source_column_2_or_number": {
                                "type": "string",
                                "description": "第二个操作数，可以是列名或数字（字符串格式）"
                            },
                            "round_to": {
                                "type": "string",
                                "description": "保留小数位数，可选参数"
                            }
                        },
                        "required": ["target_column", "source_column_1", "operator", "source_column_2_or_number"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "trim_whitespace",
                    "description": "清理列中的首尾空格。适用场景：数据清洗，去除不必要的空格。例如：'清理设备名称列的空格'、'去掉备注列前后的空格'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要清理空格的列名"
                            }
                        },
                        "required": ["column"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "fill_missing_values",
                    "description": "填充空白单元格。适用场景：将列中的空值填充为指定内容。例如：'把备注列的空白单元格填充为N/A'、'把空的状态都改成待处理'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要填充空值的列名"
                            },
                            "fill_value": {
                                "type": "string",
                                "description": "用于填充空值的内容"
                            }
                        },
                        "required": ["column", "fill_value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "find_and_replace",
                    "description": "查找并替换文本。适用场景：批量替换列中的特定文本。例如：'把客户区域列里的北京都替换成华北区'、'把所有的旧名称改成新名称'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column": {
                                "type": "string",
                                "description": "要进行查找替换的列名"
                            },
                            "find_text": {
                                "type": "string",
                                "description": "要查找的文本"
                            },
                            "replace_text": {
                                "type": "string",
                                "description": "替换成的文本"
                            }
                        },
                        "required": ["column", "find_text", "replace_text"]
                    }
                }
            },
            # === v0.0.4-alpha 新增工具 ===
            {
                "type": "function",
                "function": {
                    "name": "concatenate_columns",
                    "description": "合并多列为一列。适用场景：需要将多个列的内容连接起来。例如：'把姓和名合并为全名'、'把区域和城市连接为地址'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "target_column": {
                                "type": "string",
                                "description": "新列的名称"
                            },
                            "source_columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "要合并的源列名数组，例如 ['姓', '名']"
                            },
                            "delimiter": {
                                "type": "string",
                                "description": "连接符，默认为空格。例如：' ' 或 '-' 或 '_'",
                                "default": " "
                            }
                        },
                        "required": ["target_column", "source_columns"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_date_part",
                    "description": "从日期列提取年/月/日/星期/季度。适用场景：分析日期数据。例如：'从订单日期提取月份'、'提取创建时间的年份'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_column": {
                                "type": "string",
                                "description": "源日期列名"
                            },
                            "target_column": {
                                "type": "string",
                                "description": "目标列名（AI智能生成，如 '订单日期_月份'）"
                            },
                            "part_to_extract": {
                                "type": "string",
                                "enum": ["year", "month", "day", "weekday", "quarter"],
                                "description": "要提取的部分：year(年份), month(月份), day(日期), weekday(星期几), quarter(季度)"
                            }
                        },
                        "required": ["source_column", "target_column", "part_to_extract"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "group_by_aggregate",
                    "description": "分组聚合统计（只统计，不修改表格）。适用场景：统计分析。例如：'按设备类型分组，计算平均价格'、'统计每个区域的销售额总和'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "group_by_column": {
                                "type": "string",
                                "description": "分组列名"
                            },
                            "agg_column": {
                                "type": "string",
                                "description": "聚合计算的列名"
                            },
                            "agg_func": {
                                "type": "string",
                                "enum": ["mean", "sum", "count"],
                                "description": "聚合函数：mean(平均值), sum(求和), count(计数)"
                            }
                        },
                        "required": ["group_by_column", "agg_column", "agg_func"]
                    }
                }
            },
            # === v0.0.4-beta 新增工具 ===
            {
                "type": "function",
                "function": {
                    "name": "split_column",
                    "description": "拆分列。按分隔符将一列拆分为多列。适用场景：'把客户信息列按-拆分'、'将全名列按空格拆分为姓和名'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "source_column": {
                                "type": "string",
                                "description": "要拆分的源列名"
                            },
                            "delimiter": {
                                "type": "string",
                                "description": "分隔符，例如 '-' 或 ' '（空格）"
                            },
                            "new_column_names": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "可选的新列名列表。如果用户指定了列名（如'拆分为姓和名'），提取出来。否则留空，系统自动命名"
                            }
                        },
                        "required": ["source_column", "delimiter"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "change_case",
                    "description": "更改列的大小写。适用场景：'把产品编码列全部转为大写'、'把姓名列转为首字母大写'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column_name": {
                                "type": "string",
                                "description": "列名"
                            },
                            "case_type": {
                                "type": "string",
                                "enum": ["upper", "lower", "proper"],
                                "description": "大小写类型：upper(全部大写), lower(全部小写), proper(首字母大写)"
                            }
                        },
                        "required": ["column_name", "case_type"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "drop_duplicates",
                    "description": "删除重复行。适用场景：'删除重复行'、'根据客户邮箱列删除重复数据'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "subset_columns": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "用于判断重复的列。如果用户说'删除重复行'（没指定列），留空表示判断所有列。如果说'根据XX列删除重复'，提取列名"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "sort_by_column",
                    "description": "按列排序。适用场景：'按销售额列降序排序'、'把表格按日期升序排列'",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "column_name": {
                                "type": "string",
                                "description": "排序依据的列名"
                            },
                            "ascending": {
                                "type": "boolean",
                                "description": "是否升序。默认 true(升序)。如果用户说'降序'、'从高到低'，传 false"
                            }
                        },
                        "required": ["column_name"]
                    }
                }
            }
        ]
        
        # 如果提供了过滤列表，只返回指定的工具
        if filter_tools:
            filtered = [tool for tool in all_tools if tool["function"]["name"] in filter_tools]
            logger.info(f"工具过滤：从 {len(all_tools)} 个工具过滤到 {len(filtered)} 个")
            logger.info(f"当前使用工具: {[t['function']['name'] for t in filtered]}")
            return filtered
        
        return all_tools
    
    def build_system_prompt(self, headers: List[str]) -> str:
        """
        构建系统提示词
        Args:
            headers: 用户表格的列名列表
        Returns:
            系统提示词
        """
        # ✅ 从 YAML 加载，代码干净！
        return get_prompt('system_prompts.main', headers=', '.join(headers))
    
    def translate(self, user_command: str, headers: List[str]) -> Dict[str, Any]:
        """
        翻译用户指令为工具调用
        Args:
            user_command: 用户的自然语言指令
            headers: 表格的列名列表
        Returns:
            翻译结果，包含tool_calls或错误信息
        """
        try:
            logger.info(f"开始翻译指令: {user_command}")
            logger.info(f"可用列名: {headers}")
            
            # 检查是否是帮助指令
            help_keywords = ["帮助", "help", "你能做什么", "有什么功能", "怎么用", "功能列表"]
            if user_command.strip().lower() in help_keywords:
                logger.info("用户请求帮助信息")
                # ✅ 从 YAML 加载，代码干净！
                help_message = get_prompt('help_messages.main')
                
                return {
                    "success": True,
                    "is_help": True,
                    "message": help_message
                }
            
            # ⭐️ 关键词路由优化 - 减少Token消耗
            detected_group = self._detect_tool_group(user_command)
            if detected_group:
                # 命中关键词，只使用该组的工具
                filter_tools = TOOL_GROUPS[detected_group]["tools"]
                tools = self.get_tools_definition(filter_tools=filter_tools)
                logger.info(f"✅ 关键词路由优化生效，Token预计减少 60-70%")
            else:
                # 未命中，使用所有工具（兜底）
                tools = self.get_tools_definition()
                logger.info("未命中关键词，使用全量工具")
            
            # 调用AI
            response = self.client.chat.completions.create(
                model=self.model,  # 根据API自动选择模型
                messages=[
                    {"role": "system", "content": self.build_system_prompt(headers)},
                    {"role": "user", "content": user_command}
                ],
                tools=tools,
                tool_choice="auto"  # 让AI自动决用是否使用工具
            )
            
            message = response.choices[0].message
            
            # 检查AI是否调用了工具
            if not message.tool_calls:
                # AI没有调用工具，返回友好提示而不是错误
                # ✅ 从 YAML 加载，代码干净！
                friendly_message = get_prompt('error_messages.router_failed')
                
                logger.info(f"AI未调用工具，返回友好提示")
                return {
                    "success": True,  # 改为 True，因为这不是错误，是正常的 AI 回复
                    "is_friendly_message": True,  # 新增标记
                    "message": friendly_message
                }
            
            # 解析工具调用
            tool_calls = []
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)
                
                tool_calls.append({
                    "tool_name": function_name,
                    "parameters": function_args
                })
                
                # 使用 json.dumps 避免字典中的花括号导致格式化错误
                logger.info(f"AI翻译结果: {function_name}({json.dumps(function_args, ensure_ascii=False)})")
            
            return {
                "success": True,
                "tool_calls": tool_calls
            }
            
        except Exception as e:
            error_msg = f"AI翻译失败: {str(e)}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }


# 创建全局翻译器实例（延迟初始化）
_translator_instance = None

def get_translator() -> AITranslator:
    """获取AI翻译器单例"""
    global _translator_instance
    if _translator_instance is None:
        _translator_instance = AITranslator()
    return _translator_instance

