"""
API 层 - 对外接口
包含 FastAPI 应用、WebSocket 和 ASGI 配置

Author: TJxiaobao
License: MIT
Version: 0.0.6
"""

from .main import app
from .websocket import sio

__all__ = ["app", "sio"]

