"""
数据模型定义
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ExecuteCommandRequest(BaseModel):
    """执行指令请求"""
    file_id: str
    command: str  # 用户的自然语言指令


class ExecuteCommandResponse(BaseModel):
    """执行指令响应"""
    success: bool
    message: str
    execution_log: List[str]
    download_url: Optional[str] = None
    error: Optional[str] = None


class UploadFileResponse(BaseModel):
    """上传文件响应"""
    success: bool
    file_id: str
    headers: List[str]
    total_rows: int
    message: str


class ToolCall(BaseModel):
    """AI翻译出的工具调用"""
    tool_name: str
    parameters: Dict[str, Any]

