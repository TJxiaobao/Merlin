"""
Merlin ASGI 应用入口
整合 FastAPI + Socket.IO

Author: TJxiaobao
License: MIT
"""
from .main import app
from .websocket import sio
import socketio

# ⭐️ 创建包装的 ASGI 应用
# Socket.IO 会拦截 /socket.io/* 路径，其他请求转发给 FastAPI
application = socketio.ASGIApp(
    socketio_server=sio,
    other_asgi_app=app,
    socketio_path='/socket.io'
)

# 用于 uvicorn 启动
# 使用方式: uvicorn app.asgi:application --reload

