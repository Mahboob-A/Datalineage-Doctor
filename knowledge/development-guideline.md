# Development Guideline

**Project:** DataLineage Doctor
**Version:** 1.0
**Date:** April 17, 2026
**Status:** Approved

---

## Language and Runtime

| Item | Value |
|---|---|
| Language | Python 3.12 |
| Runtime manager | `pyenv` (recommended) or system Python 3.12 |
| Package manager | `uv` — the only permitted tool for installs, locking, and running |

No `pip install` commands directly. All dependency operations go through `uv`.

---

## Package Manager — `uv`

### Install uv

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Common commands

```bash
# Create virtualenv and install all dependencies
uv sync

# Add a new dependency
uv add <package>

# Add a dev-only dependency
uv add --dev <package>

# Remove a dependency
uv remove <package>

# Run a command inside the project virtualenv
uv run pytest
uv run ruff check .
uv run python scripts/seed_demo.py

# Lock dependencies without installing
uv lock
```

### Dependency files

- `pyproject.toml` — all dependencies declared here
- `uv.lock` — the lock file; always committed to git
- Never edit `uv.lock` by hand

---

## Project Dependencies

### Core

```toml
[project]
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.30",
    "celery[redis]>=5.4",
    "redis>=5.0",
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.3",
    "openai>=1.35",
    "httpx>=0.27",
    "jinja2>=3.1",
    "prometheus-client>=0.20",
    "structlog>=24.1",
    "tenacity>=8.3",
]
```

### Dev

```toml
[tool.uv]
dev-dependencies = [
    "pytest>=8.2",
    "pytest-asyncio>=0.23",
    "pytest-mock>=3.14",
    "respx>=0.21",
    "httpx>=0.27",
    "ruff>=0.5",
    "pre-commit>=3.7",
]
```

---

## Linting and Formatting — Ruff

Ruff handles both linting and formatting. No separate Black or isort.

### Config in `pyproject.toml`

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM", "ANN001", "ANN201"]
ignore = ["E501"]

[tool.ruff.format]
quote-style = "double"
indent-style = "space"
```

### Commands

```bash
# Check for lint errors
uv run ruff check .

# Auto-fix lint errors
uv run ruff check --fix .

# Format code
uv run ruff format .

# Check formatting without modifying
uv run ruff format --check .
```

Ruff must pass with zero errors before every commit.

---

## Test Framework — pytest

### Config in `pyproject.toml`

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
python_functions = ["test_*"]
addopts = "-v --tb=short"
```

### Run tests

```bash
# All tests
uv run pytest

# Specific module
uv run pytest tests/test_webhook.py

# With coverage report
uv run pytest --cov=app --cov=agent --cov=om_client --cov-report=term-missing
```

### Test file locations

| What is being tested | File location |
|---|---|
| Webhook routes | `tests/test_webhook.py` |
| Agent loop | `tests/test_agent.py` |
| Individual tools | `tests/test_tools.py` |
| OM client methods | `tests/test_om_client.py` |
| Report persistence | `tests/test_report.py` |
| Celery tasks | `tests/test_worker.py` |
| Dashboard routes | `tests/test_dashboard.py` |
| Shared fixtures | `tests/conftest.py` |

---

## Pre-commit Setup

```bash
# Install hooks
uv run pre-commit install

# Run manually on all files
uv run pre-commit run --all-files
```

### `.pre-commit-config.yaml`

```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.5.0
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.6.0
    hooks:
      - id: check-merge-conflict
      - id: check-added-large-files
      - id: detect-private-key
      - id: end-of-file-fixer
      - id: trailing-whitespace
```

---

## Docker and Compose

- The full local stack is defined in `docker-compose.yml` at the project root
- Every service is containerised; no dev workflow requires a host-installed PostgreSQL or Redis
- The app and worker containers use a shared `Dockerfile`
- OpenMetadata stack is pulled from the official Docker Compose provided by OpenMetadata

### Start the dev stack

```bash
make dev
# or
docker compose up -d
```

### Stop and clean

```bash
docker compose down -v   # removes volumes — use when resetting demo state
docker compose down      # stops containers, keeps volumes
```

### Rebuild after code changes

```bash
docker compose up -d --build app worker
```

---

## Environment Variables

- All environment variables are read by `app/config.py` only via `pydantic-settings`
- No other module calls `os.environ` or `os.getenv` directly
- `.env.example` at the project root lists every required variable with placeholder values
- Copy `.env.example` to `.env` and fill in real values for local development
- `.env` is gitignored; `.env.example` is committed

---

## Logging Standards

- Use `structlog` for all application logging
- Log format: JSON in production, human-readable console format in development
- Every agent tool call must produce a structured log entry with: `tool_name`, `input`, `result_summary`, `duration_ms`
- Use log levels correctly: `DEBUG` for tool call details, `INFO` for task lifecycle, `WARNING` for recoverable failures, `ERROR` for unrecoverable failures
- No `print()` statements in application code

---

## Database Migrations

- `alembic` manages all schema changes
- Never modify the database schema directly via SQL in production
- Every schema change produces a new Alembic revision

```bash
# Generate a new migration
uv run alembic revision --autogenerate -m "add incidents table"

# Apply migrations
uv run alembic upgrade head

# Rollback one step
uv run alembic downgrade -1
```

---

## Pre-commit Checklist

Before every `git commit`:

- [ ] `uv run ruff check .` passes with zero errors
- [ ] `uv run ruff format --check .` passes
- [ ] `uv run pytest` passes
- [ ] No secrets in staged files
- [ ] No `print()` statements in application code
- [ ] No commented-out code blocks
- [ ] Progress file updated if a sprint ticket was completed

---

## Documentation Update Rules

- When a non-obvious architectural decision is made, add a note to the relevant `knowledge/` doc before closing the ticket
- Project understanding overviews (`knowledge/project-understanding/`) must be updated at the end of every sprint — 100–200 words maximum
- Sprint progress files must be updated immediately after each ticket completes — not in batches
- Never rewrite a knowledge doc from scratch mid-project; edit in place to preserve history
