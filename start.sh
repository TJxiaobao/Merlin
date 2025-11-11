#!/bin/bash
# Merlin 一键启动脚本 (Vite 架构)
# Author: TJxiaobao
# License: MIT

echo "🧙 Merlin - AI表格填充助手"
echo "================================"
echo "版本: v0.1.0-alpha (Vite 架构)"
echo ""

# 检查是否在项目根目录
if [ ! -f "app/api/main.py" ]; then
    echo "❌ 错误：请在项目根目录运行此脚本"
    exit 1
fi

# 检查 Python 环境
if [ ! -d ".venv" ]; then
    echo "❌ 错误：未找到虚拟环境"
    echo "   请先运行: python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# 检查配置
if [ ! -f ".env" ]; then
    echo "⚠️  警告：未找到 .env 文件"
    echo "   请先运行: python setup.py"
    echo ""
    read -p "是否现在配置? (y/N): " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        source .venv/bin/activate
        python setup.py
    else
        exit 1
    fi
fi

# 检查 Node.js 和 npm
if ! command -v node &> /dev/null; then
    echo "❌ 错误：未找到 Node.js"
    echo "   请先安装 Node.js: https://nodejs.org/"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "❌ 错误：未找到 npm"
    exit 1
fi

# 检查前端依赖
if [ ! -d "frontend/node_modules" ]; then
    echo "📦 首次运行，正在安装前端依赖..."
    cd frontend
    npm install
    if [ $? -ne 0 ]; then
        echo "❌ 前端依赖安装失败"
        exit 1
    fi
    cd ..
    echo "   ✅ 前端依赖安装完成"
    echo ""
fi

# 清理可能存在的旧进程
echo "🧹 清理旧进程..."
pkill -9 -f "uvicorn app" 2>/dev/null
pkill -9 -f "vite" 2>/dev/null

# 清理占用端口的进程
echo "🔍 检查端口占用..."
PORT_8000=$(lsof -ti :8000)
PORT_1108=$(lsof -ti :1108)

if [ ! -z "$PORT_8000" ]; then
    echo "   清理 8000 端口 (PID: $PORT_8000)"
    kill -9 $PORT_8000 2>/dev/null
fi

if [ ! -z "$PORT_1108" ]; then
    echo "   清理 1108 端口 (PID: $PORT_1108)"
    kill -9 $PORT_1108 2>/dev/null
fi

sleep 1
echo "   ✅ 清理完成"

echo ""
echo "1️⃣ 启动后端服务（WebSocket 流式响应）..."
source .venv/bin/activate

# ⭐️ 在后台启动后端（使用 asgi:application 整合 Socket.IO）
nohup python -m uvicorn app.asgi:application --reload --host 127.0.0.1 --port 8000 > backend.log 2>&1 &
BACKEND_PID=$!

echo "   ✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo "   📡 API地址: http://localhost:8000"
echo "   📝 日志文件: backend.log"
echo ""

# 等待后端启动
sleep 2

echo "2️⃣ 启动前端开发服务器..."

# 在后台启动前端
cd frontend
nohup npm run dev > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

echo "   ✅ 前端服务已启动 (PID: $FRONTEND_PID)"
echo "   🌐 访问地址: http://localhost:1108"
echo "   📝 日志文件: frontend.log"
echo ""

# 等待前端启动
sleep 3

echo "================================"
echo "🎉 Merlin 已启动！"
echo ""
echo "💡 访问方式："
echo "   - 前端界面: http://localhost:1108"
echo "   - API文档:  http://localhost:8000/docs"
echo ""
echo "📊 进程信息："
echo "   - 后端 PID: $BACKEND_PID"
echo "   - 前端 PID: $FRONTEND_PID"
echo ""
echo "📝 日志文件："
echo "   - 后端: backend.log"
echo "   - 前端: frontend.log"
echo ""
echo "⏹️  停止服务："
echo "   运行: ./stop.sh"
echo "   或: kill $BACKEND_PID $FRONTEND_PID"
echo "================================"
echo ""

# 自动打开浏览器（如果不会自动跳转可以取消注释）
#echo "🌐 正在打开浏览器..."
#sleep 2
#if [[ "$OSTYPE" == "darwin"* ]]; then
#    # macOS
#    open http://localhost:1108
#elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
#    # Linux
#    xdg-open http://localhost:1108
#else
#    # Windows (Git Bash)
#    start http://localhost:1108
#fi

echo ""
echo "✅ 启动完成！浏览器应该已自动打开"
echo "   如果没有，请手动访问: http://localhost:1108"
echo ""
echo "💡 提示："
echo "   - 修改代码会自动热更新"
echo "   - 查看日志: tail -f backend.log 或 tail -f frontend.log"
echo "   - 停止服务: ./stop.sh"
echo ""

