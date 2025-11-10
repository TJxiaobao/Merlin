# Merlin - AI Excel 助手
# Makefile for Docker operations

.PHONY: help build up down logs restart clean status shell

# ============================================
# 帮助信息
# ============================================
help: ## 显示帮助信息
	@echo "╔═══════════════════════════════════════════╗"
	@echo "║       Merlin Docker 操作命令              ║"
	@echo "╚═══════════════════════════════════════════╝"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

# ============================================
# 构建相关
# ============================================
build: ## 构建 Docker 镜像
	@echo "🔨 构建 Merlin 镜像..."
	DOCKER_BUILDKIT=1 docker compose build
	@echo "✅ 构建完成！"

build-fast: ## 快速构建（使用缓存）
	@echo "⚡ 快速构建 Merlin 镜像..."
	DOCKER_BUILDKIT=1 docker compose build --parallel
	@echo "✅ 快速构建完成！"

rebuild: ## 清理缓存重新构建
	@echo "🧹 清理缓存并重新构建..."
	DOCKER_BUILDKIT=1 docker compose build --no-cache --pull
	@echo "✅ 重新构建完成！"

# ============================================
# 服务管理
# ============================================
up: ## 启动服务
	@echo "🚀 启动 Merlin 服务..."
	DOCKER_BUILDKIT=1 docker compose up -d
	@echo "✅ 服务已启动！"
	@echo "📱 访问地址: http://localhost:1108"

down: ## 停止服务
	@echo "🛑 停止 Merlin 服务..."
	docker compose down
	@echo "✅ 服务已停止！"

restart: ## 重启服务
	@echo "🔄 重启 Merlin 服务..."
	docker compose restart
	@echo "✅ 服务已重启！"

stop: ## 停止服务（保留容器）
	@echo "⏸️  暂停 Merlin 服务..."
	docker compose stop
	@echo "✅ 服务已暂停！"

start: ## 启动已停止的服务
	@echo "▶️  启动 Merlin 服务..."
	docker compose start
	@echo "✅ 服务已启动！"

# ============================================
# 日志和状态
# ============================================
logs: ## 查看实时日志
	docker compose logs -f merlin

logs-tail: ## 查看最近50行日志
	docker compose logs --tail=50 merlin

status: ## 查看服务状态
	@echo "📊 Merlin 服务状态："
	@docker compose ps

# ============================================
# 调试和开发
# ============================================
shell: ## 进入容器 Shell
	@echo "🐚 进入 Merlin 容器..."
	docker compose exec merlin /bin/bash

shell-sh: ## 进入容器 sh（如果bash不可用）
	@echo "🐚 进入 Merlin 容器..."
	docker compose exec merlin /bin/sh

inspect: ## 查看容器详细信息
	docker compose exec merlin python -c "\
import os; \
print('=== 环境变量 ==='); \
print('OPENAI_API_KEY:', os.getenv('OPENAI_API_KEY', 'Not Set')[:20] + '...'); \
print('OPENAI_API_BASE:', os.getenv('OPENAI_API_BASE')); \
print('UPLOAD_DIR:', os.getenv('UPLOAD_DIR')); \
print(); \
print('=== 文件路径 ==='); \
print('Frontend exists:', os.path.exists('/app/frontend/dist')); \
print('App exists:', os.path.exists('/app/app')); \
print('Uploads exists:', os.path.exists('/app/uploads')); \
"

# ============================================
# 清理和维护
# ============================================
clean: ## 清理容器和网络（保留镜像）
	@echo "🧹 清理 Merlin 容器和网络..."
	docker compose down
	@echo "✅ 清理完成！"

clean-all: ## 清理所有（包括镜像和卷）
	@echo "🗑️  清理所有 Merlin 资源..."
	docker compose down -v --rmi all
	@echo "✅ 完全清理完成！"

prune: ## 清理 Docker 系统缓存
	@echo "🧹 清理 Docker 系统缓存..."
	docker system prune -f
	@echo "✅ 缓存清理完成！"

# ============================================
# 部署和更新
# ============================================
deploy: ## 部署服务（构建+启动）
	@echo "🚀 部署 Merlin..."
	$(MAKE) build
	$(MAKE) up
	@echo "✅ 部署完成！访问: http://localhost:1108"

update: ## 更新服务（拉取代码+重新部署）
	@echo "📦 更新 Merlin..."
	git pull
	$(MAKE) down
	$(MAKE) build
	$(MAKE) up
	@echo "✅ 更新完成！"

redeploy: ## 重新部署（停止+清理+构建+启动）
	@echo "♻️  重新部署 Merlin..."
	$(MAKE) down
	$(MAKE) rebuild
	$(MAKE) up
	@echo "✅ 重新部署完成！"

# ============================================
# 备份
# ============================================
backup: ## 备份上传的文件
	@echo "💾 备份文件..."
	@mkdir -p backups
	tar -czf backups/uploads-backup-$$(date +%Y%m%d-%H%M%S).tar.gz uploads/ 2>/dev/null || echo "uploads 目录为空"
	@echo "✅ 备份完成！文件保存在 backups/ 目录"

# ============================================
# 版本信息
# ============================================
version: ## 显示版本信息
	@echo "╔═══════════════════════════════════════════╗"
	@echo "║          Merlin v0.0.5                    ║"
	@echo "╚═══════════════════════════════════════════╝"
	@echo ""
	@docker compose version
	@echo ""
	@docker --version

# ============================================
# 快捷命令
# ============================================
dev: ## 开发模式（带日志）
	@echo "🔧 开发模式启动..."
	DOCKER_BUILDKIT=1 docker compose up --build

prod: deploy ## 生产模式部署（等同于 deploy）
