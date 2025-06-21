# ---- Config ----
PROJECT_NAME = orator
COMPOSE = docker-compose
DOCKER = docker
ENV_FILE = Backend/.env

# ---- Targets ----

.PHONY: help
help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "Common targets:"
	@echo "  up             Start all services"
	@echo "  build          Build all containers (uses .env)"
	@echo "  down           Stop all containers and remove volumes"
	@echo "  reset          Full reset: down + prune + rebuild"
	@echo "  shell-api      Enter FastAPI container"
	@echo "  shell-celery   Enter Celery container"
	@echo "  shell-flower   Enter Flower container"
	@echo "  logs           Show container logs"
	@echo "  test           Run pytest inside FastAPI container"
	@echo "  flower-ui      Open Flower monitoring dashboard"
	@echo "  clean          Clean Docker images & volumes"

up:
	$(COMPOSE) --env-file $(ENV_FILE) up --build

build:
	$(COMPOSE) --env-file $(ENV_FILE) build

down:
	$(COMPOSE) down -v

reset:
	$(COMPOSE) down --remove-orphans -v
	docker system prune -af --volumes
	$(COMPOSE) build --no-cache
	$(COMPOSE) up --force-recreate

logs:
	$(COMPOSE) logs -f

shell-api:
	$(DOCKER) exec -it $(PROJECT_NAME)-api bash

shell-celery:
	$(DOCKER) exec -it $(PROJECT_NAME)-celery bash

shell-flower:
	$(DOCKER) exec -it $(PROJECT_NAME)-flower sh

test:
	$(DOCKER) exec -it $(PROJECT_NAME)-api pytest Test/

flower-ui:
	@echo "Opening Flower dashboard at http://localhost:5555"
	open http://localhost:5555|| xdg-open http://localhost:5555|| echo "Visit manually: http://localhost:5555"

