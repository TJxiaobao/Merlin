#!/bin/bash
# Merlin Frontend 启动脚本

echo "🧙 Merlin - AI表格填充助手"
echo "================================"
echo ""

# 检查是否在项目根目录
if [ ! -f "app/main.py" ]; then
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

echo "1️⃣ 启动后端服务..."
source .venv/bin/activate

# 在后台启动后端
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000 > /dev/null 2>&1 &
BACKEND_PID=$!

echo "   ✅ 后端服务已启动 (PID: $BACKEND_PID)"
echo "   📡 API地址: http://localhost:8000"
echo ""

# 等待服务启动
sleep 2

echo "2️⃣ 打开前端界面..."

# 根据操作系统打开浏览器
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    open frontend/index.html
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    xdg-open frontend/index.html
else
    # Windows (Git Bash)
    start frontend/index.html
fi

echo "   ✅ 前端界面已打开"
echo ""
echo "================================"
echo "🎉 Merlin 已启动！"
echo ""
echo "💡 提示："
echo "   - 前端界面应该已自动打开"
echo "   - 如果没有打开，请手动打开: frontend/index.html"
echo "   - API文档: http://localhost:8000/docs"
echo ""
echo "⏹️  停止服务："
echo "   按 Ctrl+C 或运行: kill $BACKEND_PID"
echo "================================"
echo ""

# 等待用户终止
echo "按 Ctrl+C 停止服务..."
trap "echo ''; echo '⏹️  正在停止服务...'; kill $BACKEND_PID 2>/dev/null; echo '✅ 服务已停止'; exit 0" INT

# 保持脚本运行
wait $BACKEND_PID

