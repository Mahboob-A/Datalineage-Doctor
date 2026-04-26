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
	docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml down

prod-mini-restart:
	@echo "==> Restarting production app and worker..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml restart app worker
	@echo "✅ Production app and worker restarted."

prod-nginx-restart:
	@echo "==> Restarting production nginx..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml restart nginx
	@echo "✅ Production nginx restarted."

prod-full-restart:
	@echo "==> Restarting production full stack..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml restart
	@echo "✅ Production full stack restarted."

prod-logs:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml logs -f app worker nginx

prod-migrate:
	docker compose -f docker-compose.yml -f docker-compose.prod.yml exec app uv run alembic upgrade head

certbot-init:
	@echo "==> Getting SSL certificate for dldoctor.app (standalone mode)..."
	@echo "==> Nginx must NOT be running. Port 80 must be free."
	@mkdir -p /home/dldoctor/certs /home/dldoctor/certbot-www
	docker run --rm \
	  -p 80:80 \
	  -v /home/dldoctor/certs:/etc/letsencrypt \
	  certbot/certbot certonly --standalone \
	  -d dldoctor.app \
	  --non-interactive --agree-tos -m admin@dldoctor.app \
	  --no-eff-email
	@echo "==> Certificate obtained at /home/dldoctor/certs/"
	@echo "==> Now run: make prod"

certbot-renew:
	@echo "==> Renewing SSL certificate..."
	docker compose -f docker-compose.yml -f docker-compose.prod.yml stop nginx
	docker run --rm \
	  -p 80:80 \
	  -v /home/dldoctor/certs:/etc/letsencrypt \
	  certbot/certbot renew --standalone --quiet
	docker compose -f docker-compose.yml -f docker-compose.prod.yml start nginx
	@echo "==> Certificate renewed and nginx reloaded."
