# Deployment Guide

**Project:** DataLineage Doctor
**Version:** 2.0 (Production — Linode)
**Date:** April 26, 2026
**Status:** Approved

---

## Overview

DataLineage Doctor runs as a full Docker Compose stack on a single Linode server (16 GB RAM, 6 CPU, 320 GB SSD, 10 GB swap) at **`https://dldoctor.app`**.

Nginx acts as the TLS-terminating reverse proxy. All services run in a shared Docker network. Only ports 22, 80, and 443 are publicly accessible (UFW enforced).

---

## URL Routing

| Public URL | Routes to |
|---|---|
| `https://dldoctor.app/` | Landing page (static, Bioluminescent Abyss theme) |
| `https://dldoctor.app/incidents` | Incidents list dashboard |
| `https://dldoctor.app/incidents/{id}` | Incident detail + lineage graph |
| `https://dldoctor.app/docs` | FastAPI OpenAPI / Swagger UI |
| `https://dldoctor.app/health` | Health check endpoint |
| `https://dldoctor.app/metrics` | Prometheus metrics |
| `https://dldoctor.app/grafana/` | Grafana dashboard |
| `https://dldoctor.app/prometheus/` | Prometheus UI |
| `https://dldoctor.app/openmetadata/` | OpenMetadata UI (judges access) |
| `http://dldoctor.app/*` | 301 redirect → HTTPS |

---

## Docker Compose Stack

### Services

| Service | Image | Role |
|---|---|---|
| `nginx` | `nginx:1.27-alpine` | TLS reverse proxy (ports 80, 443) |
| `app` | Built from `docker/Dockerfile` | FastAPI HTTP server |
| `worker` | Built from `docker/Dockerfile` | Celery RCA task worker |
| `redis` | `redis:7-alpine` | Celery broker + result backend |
| `db` | `postgres:16-alpine` | Local incidents DB |
| `mysql` | `mysql:8` | OpenMetadata metadata store |
| `elasticsearch` | `elasticsearch:8.15.0` | OpenMetadata search backend |
| `openmetadata_server` | `openmetadata/server:1.5.4` | OpenMetadata platform |
| `prometheus` | `prom/prometheus:v2.54.1` | Metrics scraper |
| `grafana` | `grafana/grafana:11.2.2` | Observability dashboard |

### Compose file strategy

```bash
# Production (always both files):
docker compose -f docker-compose.yml -f docker-compose.prod.yml <command>

# Local development (base + override):
docker compose up -d   # docker-compose.override.yml is picked up automatically
```

---

## Server Details

| Property | Value |
|---|---|
| IP | `172.236.169.146` |
| Domain | `dldoctor.app` |
| OS | Ubuntu (Linode) |
| RAM | 16 GB |
| Swap | 10 GB (512M partition + 10G file) |
| Storage | 320 GB SSD |
| Deploy user | `dldoctor` (sudo + docker groups) |
| App directory | `/home/dldoctor/app` |

---

## First-Time Server Setup

### Step 1 — SSH into the server

```bash
ssh dldoctor@172.236.169.146
```

### Step 2 — Run the provisioning script

```bash
cd /home/dldoctor/app   # after cloning (script clones if not present)
bash scripts/server_setup.sh
```

The script:
- Configures UFW (allow 22, 80, 443; deny everything else)
- Clones or pulls the repo
- Creates `.env` from `.env.example`
- Adds monthly certbot renewal cron

### Step 3 — Edit `.env` with production secrets

```bash
nano /home/dldoctor/app/.env
```

Required changes from `.env.example`:

```bash
APP_ENV=production
APP_BASE_URL=https://dldoctor.app

LLM_API_KEY=<your Gemini key>
LLM_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai/
LLM_MODEL=gemini-2.5-flash-preview-04-17
LLM_TIMEOUT_SECONDS=90

OM_JWT_TOKEN=<your OM non-expiring bot token>
# OR use credential fallback:
# OM_ADMIN_EMAIL=admin@open-metadata.org
# OM_ADMIN_PASSWORD=YWRtaW4=

SLACK_ENABLED=false
SLACK_WEBHOOK_URL=<optional>
```

### Step 4 — Obtain SSL certificate (first time only)

Certbot needs port 80 accessible to verify the domain. Start all services **except nginx** first so certbot can use the webroot:

```bash
cd /home/dldoctor/app

# Start everything except nginx
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d \
  app worker db redis mysql elasticsearch execute-migrate-all openmetadata_server prometheus grafana

# Obtain the certificate
make certbot-init
```

### Step 5 — Start the full stack (including nginx)

```bash
make prod
```

### Step 6 — Run database migrations

```bash
make prod-migrate
```

### Step 7 — Verify

```bash
curl https://dldoctor.app/health
# Expected: {"status": "ok"}
```

---

## GitOps CI/CD

Every push to `main` triggers the GitHub Actions workflow at `.github/workflows/deploy.yml`.

### Flow

```
Push to main
    │
    ▼
Job: test
  - Install uv + dependencies
  - Run pytest (all 60+ tests must pass)
    │
    ▼ (on success)
Job: deploy
  - SSH into 172.236.169.146 as dldoctor
  - git pull origin main
  - docker compose build app worker
  - docker compose up -d
  - alembic upgrade head
  - curl https://dldoctor.app/health (smoke test)
```

### GitHub Secrets Setup

Go to: `https://github.com/Mahboob-A/Datalineage-Doctor/settings/secrets/actions`

Add three repository secrets:

| Secret name | Value |
|---|---|
| `LINODE_HOST` | `172.236.169.146` |
| `LINODE_USER` | `dldoctor` |
| `LINODE_SSH_KEY` | Contents of your `~/.ssh/dldoctor_deploy` private key file |

**Generate the SSH key pair** (run once on your Mac):

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/dldoctor_deploy
# No passphrase

# Copy the PUBLIC key to the Linode server:
ssh-copy-id -i ~/.ssh/dldoctor_deploy.pub dldoctor@172.236.169.146

# Copy the PRIVATE key content for GitHub:
cat ~/.ssh/dldoctor_deploy   # paste this entire output into LINODE_SSH_KEY secret
```

---

## Production Makefile Commands

```bash
make prod             # Build + start full prod stack (with Nginx)
make prod-down        # Stop prod stack
make prod-logs        # Tail app, worker, nginx logs
make prod-migrate     # Run Alembic migrations in prod
make certbot-init     # Obtain SSL certificate (first time only)
make certbot-renew    # Renew SSL certificate + reload nginx
```

---

## Local Development Setup (unchanged)

```bash
# Prerequisites: Docker Desktop, Python 3.12, uv
git clone https://github.com/Mahboob-A/Datalineage-Doctor.git
cd Datalineage-Doctor
cp .env.example .env
# Edit .env (LLM_API_KEY minimum)
make dev
make migrate
curl http://localhost:8000/health
```

Local endpoints: `http://localhost:8000` (app), `http://localhost:8585` (OM), `http://localhost:3000` (Grafana), `http://localhost:9090` (Prometheus).

---

## Environment Variables

All variables documented in `.env.example`. Key production-only additions:

| Variable | Production value |
|---|---|
| `APP_ENV` | `production` |
| `APP_BASE_URL` | `https://dldoctor.app` |
| `GF_SERVER_ROOT_URL` | `https://dldoctor.app/grafana` (set in `docker-compose.prod.yml`) |
| `GF_SERVER_SERVE_FROM_SUB_PATH` | `true` (set in `docker-compose.prod.yml`) |

---

## SSL Certificate Renewal

Let's Encrypt certs expire every 90 days. Renewal is automated via monthly cron:

```
0 3 1 * *  cd /home/dldoctor/app && make certbot-renew
```

To renew manually:
```bash
make certbot-renew
```

---

## Health Checks

| Endpoint | Expected |
|---|---|
| `GET https://dldoctor.app/health` | `{"status": "ok"}` |
| `GET https://dldoctor.app/metrics` | Prometheus text format |
| `GET https://dldoctor.app/docs` | FastAPI Swagger UI |

---

## Known Constraints

- The OpenMetadata stack (Elasticsearch + MySQL + OM server) takes 2–3 minutes to become healthy on first start
- Minimum 8 GB RAM required; this server has 16 GB + 10 GB swap — fully sufficient
- OM served via Nginx subpath (`/openmetadata/`) may have some static asset issues due to OM's SPA routing; direct server access via SSH tunnel remains an option if needed
- `make certbot-init` must be run before the first `make prod` (nginx won't start without the cert files)
