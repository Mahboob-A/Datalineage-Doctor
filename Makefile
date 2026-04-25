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
	@echo "⏳ Waiting for OpenMetadata to be ready..."
	@docker compose exec app uv run python scripts/wait_for_om.py
	@echo "🌱 Seeding demo data..."
	@docker compose exec app uv run python scripts/seed_demo.py
	@echo "💥 Triggering DQ failure..."
	@docker compose exec app uv run python scripts/trigger_demo.py
	@echo "⏳ Waiting for RCA to complete..."
	@docker compose exec app uv run python scripts/wait_for_incident.py
	@echo "✅ Incident complete — view at http://localhost:8000"
	@open http://localhost:8000 || xdg-open http://localhost:8000 || true

prod:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --pull always

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down
