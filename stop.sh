#!/bin/bash
# Merlin 停止脚本
# Author: TJxiaobao
# License: MIT

echo "🛑 正在停止 Merlin..."
echo ""

# 停止后端
echo "⏹️  停止后端服务..."
pkill -f "uvicorn app.main:app"
if [ $? -eq 0 ]; then
    echo "   ✅ 后端已停止"
else
    echo "   ℹ️  后端未运行"
fi

# 停止前端
echo "⏹️  停止前端服务..."
pkill -f "vite"
if [ $? -eq 0 ]; then
    echo "   ✅ 前端已停止"
else
    echo "   ℹ️  前端未运行"
fi

echo ""
echo "✅ Merlin 已完全停止"

