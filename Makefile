# StockSage 常用命令封装
# 用法：make <target>，例如 `make test`、`make dev`

.PHONY: help install test lint fmt typecheck check dev build clean docker-build docker-up docker-down

help:
	@echo "StockSage Makefile commands:"
	@echo "  install      安装依赖（含 dev 工具链）"
	@echo "  test         跑后端测试套件"
	@echo "  lint         ruff 检查（不修复）"
	@echo "  fmt          ruff format + ruff fix"
	@echo "  typecheck    mypy 类型检查"
	@echo "  check        lint + typecheck + test 一键全跑（PR 前用）"
	@echo "  dev          启动后端 dev server (uvicorn --reload)"
	@echo "  build        前端 vite 构建"
	@echo "  clean        清理 __pycache__ / .pytest_cache / dist"
	@echo "  docker-build 构建 docker 镜像"
	@echo "  docker-up    docker compose up（启动 backend + frontend）"
	@echo "  docker-down  docker compose down"

install:
	pip install ".[dev]"
	cd frontend && npm install

test:
	PYTHONPATH=. pytest -q

lint:
	ruff check backend tests

fmt:
	ruff format backend tests
	ruff check --fix backend tests

typecheck:
	mypy backend

check: lint typecheck test

dev:
	PYTHONPATH=. uvicorn backend.main:app --reload

build:
	cd frontend && npm run build

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache .mypy_cache frontend/dist

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
