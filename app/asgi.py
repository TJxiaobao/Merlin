"""
Merlin ASGI 应用入口（兼容层）
从 app/api/asgi.py 导入，保持向后兼容

Author: TJxiaobao
License: MIT
Version: 0.0.6
"""

# 从新位置导入
from .api.asgi import application

__all__ = ["application"]

