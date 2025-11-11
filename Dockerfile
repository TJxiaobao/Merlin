# Merlin - AI Excel 助手
# Multi-stage build for optimal image size

# ============================================
# Stage 1: Build Frontend
# ============================================
FROM node:18-alpine AS frontend-builder

WORKDIR /app/frontend

# 配置 npm 使用国内镜像源（显著加速）
RUN npm config set registry https://registry.npmmirror.com

# Copy frontend package files
COPY frontend/package.json frontend/package-lock.json ./

# Install dependencies with optimizations
# --prefer-offline: 优先使用本地缓存
# --no-audit: 跳过安全审计（加快速度）
# --progress=false: 减少日志输出
RUN npm ci --prefer-offline --no-audit --progress=false

# Copy frontend source
COPY frontend/ ./

# Build frontend
RUN npm run build && \
    # 构建后立即删除 node_modules，减少镜像大小
    rm -rf node_modules

# ============================================
# Stage 2: Python Backend
# ============================================
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# 配置 apt 使用国内镜像源（加速系统依赖安装）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources 2>/dev/null || \
    sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python requirements
COPY requirements.txt .

# Install Python dependencies with optimizations
# --no-cache-dir: 不保存缓存，减少镜像大小
# pip install 使用国内镜像源加速（阿里云源，更稳定）
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip config set install.trusted-host mirrors.aliyun.com && \
    pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY app/ ./app/
COPY start.sh ./
COPY stop.sh ./

# Copy frontend build from previous stage
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# Create necessary directories
RUN mkdir -p uploads && \
    chmod +x start.sh stop.sh

# Environment variables (can be overridden)
ENV PYTHONUNBUFFERED=1
ENV UPLOAD_DIR=/app/uploads
ENV OPENAI_API_KEY=""
ENV OPENAI_API_BASE="https://api.moonshot.cn/v1"

# Expose ports
EXPOSE 8000 1108

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/')"

# Start command
CMD ["python", "-m", "uvicorn", "app.asgi:application", "--host", "0.0.0.0", "--port", "8000"]

