.PHONY: help build up down logs test clean

help:
	@echo "Available commands:"
	@echo "  make build    - Build Docker images"
	@echo "  make up       - Start all services"
	@echo "  make down     - Stop all services"
	@echo "  make logs     - View logs"
	@echo "  make test     - Run API tests"
	@echo "  make clean    - Remove all containers and volumes"

build:
	cd docker && docker-compose build

up:
	cd docker && docker-compose up -d
	@echo "Services starting..."
	@echo "Backend will be available at http://localhost:8000"
	@echo "API docs at http://localhost:8000/docs"

down:
	cd docker && docker-compose down

logs:
	cd docker && docker-compose logs -f

logs-backend:
	docker logs -f doc-backend

logs-postgres:
	docker logs -f doc-postgres

logs-qdrant:
	docker logs -f doc-qdrant

test:
	@echo "Testing health endpoint..."
	curl -s http://localhost:8000/health | python3 -m json.tool

clean:
	cd docker && docker-compose down -v
	rm -rf data/postgres/* data/qdrant/* data/uploads/*

restart: down up
