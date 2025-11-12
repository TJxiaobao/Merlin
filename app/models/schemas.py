"""
数据模型定义
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


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

