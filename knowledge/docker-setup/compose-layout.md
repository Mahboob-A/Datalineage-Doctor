# Docker Compose Layout (Base + Dev + Prod)

This repo uses a **3-file Compose setup** to support both:

- a fast **hot-reload dev** workflow (bind mounts + reload)
- a **production-safe** workflow (image-only, no mounts, no reload)

## Files

### `docker-compose.yml` (base)

- Shared stack configuration for all environments.
- Defines **all services** (app, worker, db, redis, mysql, elasticsearch, OpenMetadata).
- Uses an **image reference** for `app` and `worker`:
  - `image: ${APP_IMAGE:-datalineage-doctor:dev}`

This keeps the base file “build-agnostic” and lets dev/prod decide how images are produced.

### `docker-compose.override.yml` (dev)

Automatically applied by Docker Compose when you run `docker compose up`.

Adds for `app` + `worker`:

- `build:` from `docker/Dockerfile`
- bind mount code: `.:/app`
- named volume for venv: `app_venv:/app/.venv`
- hot reload:
  - app: `uvicorn --reload`
  - worker: restart-on-change via `watchfiles`

### `docker-compose.prod.yml` (prod)

- Image-only deployment for `app` and `worker`
- Requires `APP_IMAGE` to be set (prebuilt image)
- Adds `restart: unless-stopped`
- Uses non-reload commands (worker uses `--concurrency=2`)

## Why we mount `/app/.venv` as a named volume in dev

In dev we bind mount `.:/app`. That **replaces** the container’s `/app` directory with your host checkout.

If the container created a virtualenv at `/app/.venv`, the bind mount would **hide** it, causing missing deps at runtime.

The fix is to mount a separate named volume at `/app/.venv`:

- `app_venv:/app/.venv`

So you get:

- live source edits from the host
- a persistent container-managed virtualenv not shadowed by the bind mount

## Commands

### Dev (hot reload)

Uses `docker-compose.yml` + `docker-compose.override.yml` automatically:

```bash
make dev
```

### Prod-like (image-only)

Requires a prebuilt image:

```bash
export APP_IMAGE=your-registry/datalineage-doctor:tag
make prod
```

Bring it down:

```bash
export APP_IMAGE=your-registry/datalineage-doctor:tag
make prod-down
```

## Dockerfile location

The Docker build uses:

- `docker/Dockerfile`

Dev override explicitly sets:

- `build.context: .`
- `build.dockerfile: docker/Dockerfile`

