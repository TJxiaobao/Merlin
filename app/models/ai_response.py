"""
AI 响应模型定义
统一 AI 翻译器的返回数据结构

Author: TJxiaobao
License: MIT
Version: 0.0.6
"""
import json
import logging
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from enum import Enum

logger = logging.getLogger(__name__)


class AIResponseType(str, Enum):
    """AI 响应类型枚举"""
    TOOL_CALLS = "tool_calls"              # 正常的工具调用
    CLARIFICATION = "clarification"         # 需要澄清
    HELP = "help"                          # 帮助信息
    FRIENDLY_MESSAGE = "friendly_message"   # 友好提示（AI 未调用工具）
    ERROR = "error"                        # 错误
    TASK_LIST = "task_list"                # 任务列表（Coordinator 拆分结果）


class ToolCall(BaseModel):
    """单个工具调用"""
    tool_name: str = Field(..., description="工具名称")
    parameters: Dict[str, Any] = Field(..., description="工具参数")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tool_name": "set_by_condition",
                "parameters": {
                    "condition_column": "类别",
                    "condition_value": "机械硬盘 HDD",
                    "target_column": "含税单价",
                    "target_value": "10",
                    "match_type": "contains"
                }
            }
        }


class ClarificationRequest(BaseModel):
    """澄清请求"""
    question: str = Field(..., description="向用户提出的问题")
    options: List[str] = Field(default_factory=list, description="可选项列表")
    original_command: Optional[str] = Field(None, description="原始指令")
    file_id: Optional[str] = Field(None, description="文件 ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "您说的'价格'是指哪一列？",
                "options": ["未税单价", "参考报价", "含税单价"],
                "original_command": "把价格改为10",
                "file_id": "abc123"
            }
        }


class AIResponse(BaseModel):
    """
    AI 翻译器统一响应模型
    
    所有 AI 翻译结果都使用此结构，确保类型安全和一致性
    """
    success: bool = Field(..., description="是否成功")
    response_type: AIResponseType = Field(..., description="响应类型")
    
    # 工具调用相关（response_type = TOOL_CALLS）
    tool_calls: Optional[List[ToolCall]] = Field(None, description="工具调用列表")
    
    # 澄清请求相关（response_type = CLARIFICATION）
    clarification: Optional[ClarificationRequest] = Field(None, description="澄清请求")
    
    # 任务列表相关（response_type = TASK_LIST）
    task_list: Optional[List[str]] = Field(None, description="子任务列表")
    
    # 消息相关（response_type = HELP / FRIENDLY_MESSAGE / ERROR）
    message: Optional[str] = Field(None, description="消息内容")
    
    # 错误相关（response_type = ERROR）
    error: Optional[str] = Field(None, description="错误详情")
    error_code: Optional[str] = Field(None, description="错误代码")
    
    # 元数据
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="额外的元数据")
    
    class Config:
        json_schema_extra = {
            "examples": [
                {
                    "title": "工具调用示例",
                    "value": {
                        "success": True,
                        "response_type": "tool_calls",
                        "tool_calls": [
                            {
                                "tool_name": "set_column_value",
                                "parameters": {
                                    "column": "税率",
                                    "value": "0.13"
                                }
                            }
                        ],
                        "metadata": {
                            "routing_path": "路径 A",
                            "tool_group": "filling"
                        }
                    }
                },
                {
                    "title": "澄清请求示例",
                    "value": {
                        "success": True,
                        "response_type": "clarification",
                        "clarification": {
                            "question": "您说的'价格'是指哪一列？",
                            "options": ["未税单价", "参考报价"]
                        }
                    }
                },
                {
                    "title": "错误示例",
                    "value": {
                        "success": False,
                        "response_type": "error",
                        "error": "AI 翻译失败：超时",
                        "error_code": "TRANSLATION_TIMEOUT"
                    }
                }
            ]
        }
    
    @classmethod
    def from_openai_response(cls, message, error_messages: Dict[str, str] = None) -> 'AIResponse':
        """
        从 OpenAI/Moonshot 的 Function Calling 响应创建 AIResponse
        统一转换逻辑，避免代码重复
        
        Args:
            message: OpenAI message 对象（包含 tool_calls 和 content）
            error_messages: 错误消息字典（用于加载 YAML 提示词）
        
        Returns:
            AIResponse 对象
        """
        try:
            # 情况1: AI 没有调用工具 → 友好提示
            if not message.tool_calls:
                content = message.content or "AI 未返回有效响应"
                logger.info(f"AI 未调用工具，返回友好提示")
                return create_friendly_message_response(content)
            
            # 情况2: 检查是否是澄清请求
            first_tool = message.tool_calls[0]
            if first_tool.function.name == "ask_clarification_question":
                args = json.loads(first_tool.function.arguments)
                logger.info(f"🔍 AI 请求澄清: {args.get('question_to_user', '')}")
                return create_clarification_response(
                    question=args.get("question_to_user", ""),
                    options=args.get("ambiguous_options", [])
                )
            
            # 情况3: 正常工具调用 → 解析为 ToolCall Pydantic 对象
            tool_calls = []
            for tc in message.tool_calls:
                tool_name = tc.function.name
                parameters = json.loads(tc.function.arguments)
                
                # 直接使用 tool_name 和 parameters 创建 ToolCall 对象
                tool_call = ToolCall(
                    tool_name=tool_name,
                    parameters=parameters
                )
                tool_calls.append(tool_call)
                
                # 日志输出
                logger.info(f"AI 翻译结果: {tool_name}({json.dumps(parameters, ensure_ascii=False)})")
            
            return create_tool_calls_response(tool_calls)
            
        except json.JSONDecodeError as e:
            logger.error(f"⚠️ JSON 解析失败: {e}")
            return create_error_response(
                f"AI 响应格式错误: {str(e)}",
                error_code="JSON_PARSE_ERROR"
            )
        except Exception as e:
            logger.error(f"⚠️ 转换 AI 响应失败: {e}")
            return create_error_response(
                f"AI 响应转换失败: {str(e)}",
                error_code="RESPONSE_CONVERSION_ERROR"
            )


# 便捷构造函数

def create_tool_calls_response(
    tool_calls: List[ToolCall],
    metadata: Optional[Dict[str, Any]] = None
) -> AIResponse:
    """创建工具调用响应
    
    Args:
        tool_calls: ToolCall 对象列表（而非字典列表）
        metadata: 可选的元数据
    
    Returns:
        AIResponse 对象
    """
    return AIResponse(
        success=True,
        response_type=AIResponseType.TOOL_CALLS,
        tool_calls=tool_calls,  # 直接使用 ToolCall 对象列表
        metadata=metadata or {}
    )


def create_clarification_response(
    question: str,
    options: List[str] = None,
    original_command: str = None,
    file_id: str = None
) -> AIResponse:
    """创建澄清请求响应"""
    return AIResponse(
        success=True,
        response_type=AIResponseType.CLARIFICATION,
        clarification=ClarificationRequest(
            question=question,
            options=options or [],
            original_command=original_command,
            file_id=file_id
        )
    )


def create_help_response(message: str) -> AIResponse:
    """创建帮助信息响应"""
    return AIResponse(
        success=True,
        response_type=AIResponseType.HELP,
        message=message
    )


def create_friendly_message_response(message: str) -> AIResponse:
    """创建友好提示响应"""
    return AIResponse(
        success=True,
        response_type=AIResponseType.FRIENDLY_MESSAGE,
        message=message
    )


def create_task_list_response(tasks: List[str]) -> AIResponse:
    """创建任务列表响应"""
    return AIResponse(
        success=True,
        response_type=AIResponseType.TASK_LIST,
        task_list=tasks
    )


def create_error_response(
    error: str,
    error_code: str = None
) -> AIResponse:
    """创建错误响应"""
    return AIResponse(
        success=False,
        response_type=AIResponseType.ERROR,
        error=error,
        error_code=error_code
    )


# 类型守卫（Type Guards）

def is_tool_calls_response(response: AIResponse) -> bool:
    """检查是否是工具调用响应"""
    return response.response_type == AIResponseType.TOOL_CALLS


def is_clarification_response(response: AIResponse) -> bool:
    """检查是否是澄清请求响应"""
    return response.response_type == AIResponseType.CLARIFICATION


def is_error_response(response: AIResponse) -> bool:
    """检查是否是错误响应"""
    return response.response_type == AIResponseType.ERROR


def is_task_list_response(response: AIResponse) -> bool:
    """检查是否是任务列表响应"""
    return response.response_type == AIResponseType.TASK_LIST

