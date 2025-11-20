.PHONY: help build up down logs restart clean migrate pull-model scale-workers

help:
	@echo "TahlilchiAI RAG System - Docker Commands"
	@echo "========================================="
	@echo "make build          - Build all Docker images"
	@echo "make up             - Start all services"
	@echo "make down           - Stop all services"
	@echo "make logs           - View logs (all services)"
	@echo "make logs-api       - View API logs"
	@echo "make logs-worker    - View Celery worker logs"
	@echo "make restart        - Restart all services"
	@echo "make clean          - Stop and remove all containers, volumes"
	@echo "make migrate        - Run database migrations"
	@echo "make pull-model     - Pull Ollama model"
	@echo "make scale-workers  - Scale Celery workers to 3"
	@echo "make ps             - Show running containers"
	@echo "make shell          - Open shell in API container"

build:
	docker-compose -f docker-compose.prod.yml build

up:
	docker-compose -f docker-compose.prod.yml up -d

down:
	docker-compose -f docker-compose.prod.yml down

logs:
	docker-compose -f docker-compose.prod.yml logs -f

logs-api:
	docker-compose -f docker-compose.prod.yml logs -f api

logs-worker:
	docker-compose -f docker-compose.prod.yml logs -f celery-worker

restart:
	docker-compose -f docker-compose.prod.yml restart

clean:
	docker-compose -f docker-compose.prod.yml down -v
	docker system prune -f

migrate:
	docker-compose -f docker-compose.prod.yml exec api alembic upgrade head

pull-model:
	docker-compose -f docker-compose.prod.yml exec ollama ollama pull qwen2.5:7b

scale-workers:
	docker-compose -f docker-compose.prod.yml up -d --scale celery-worker=3

ps:
	docker-compose -f docker-compose.prod.yml ps

shell:
	docker-compose -f docker-compose.prod.yml exec api /bin/bash
