.PHONY: dev stop clean migrate migrate-om test lint demo logs shell

dev:
	docker compose up -d --build

stop:
	docker compose stop

down:
	docker compose down

clean:
	docker compose down -v

migrate:
	docker compose exec app uv run alembic upgrade head

test:
	docker compose exec app uv run pytest tests/ -v

lint:
	docker compose exec app uv run ruff check .

logs:
	docker compose logs -f app worker

shell:
	docker compose exec app bash

demo:
	@echo "Seed + trigger flow - implemented in Sprint 4"

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --pull always

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down
