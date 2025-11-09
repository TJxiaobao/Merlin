# Merlin - AI Excel 助手
# Makefile for easy Docker operations

.PHONY: help build up down logs restart clean test

help: ## 显示帮助信息
	@echo "Merlin Docker 操作命令："
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""

build: ## 构建 Docker 镜像
	@echo "🔨 构建 Merlin 镜像..."
	docker-compose build

up: ## 启动服务
	@echo "🚀 启动 Merlin 服务..."
	docker-compose up -d
	@echo "✅ 服务已启动！"
	@echo "📱 访问: http://localhost:8000"

down: ## 停止服务
	@echo "🛑 停止 Merlin 服务..."
	docker-compose down

logs: ## 查看日志
	docker-compose logs -f

restart: ## 重启服务
	@echo "🔄 重启 Merlin 服务..."
	docker-compose restart

clean: ## 清理容器和镜像
	@echo "🧹 清理 Docker 资源..."
	docker-compose down -v
	docker rmi merlin:latest 2>/dev/null || true
	@echo "✅ 清理完成！"

update: ## 更新并重启服务
	@echo "📦 更新 Merlin..."
	git pull
	docker-compose up -d --build
	@echo "✅ 更新完成！"

shell: ## 进入容器 Shell
	docker-compose exec merlin /bin/bash

status: ## 查看服务状态
	docker-compose ps

test: ## 运行测试
	docker-compose exec merlin python test.py quick

# 开发相关
dev-build: ## 构建并启动（带日志）
	docker-compose up --build

dev-logs: ## 查看实时日志
	docker-compose logs -f merlin

# 生产环境
prod-up: ## 生产环境启动
	docker-compose -f docker-compose.yml up -d --build
	@echo "✅ 生产环境已启动！"

# 备份和恢复
backup: ## 备份上传的文件
	@echo "💾 备份文件..."
	tar -czf uploads-backup-$$(date +%Y%m%d-%H%M%S).tar.gz uploads/
	@echo "✅ 备份完成！"

# 版本信息
version: ## 显示版本信息
	@echo "Merlin v0.1.0"
	@docker-compose version

