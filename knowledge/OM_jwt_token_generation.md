# OpenMetadata Authentication Guide

## Token Lifetime

OpenMetadata **user** JWTs expire in **1 hour** by default (`exp - iat = 3600s`).

---

## Auth Strategy (Priority Order)

### Option A — Non-Expiring Bot Token ✅ Recommended

Create a bot user + bot entity once. The generated token **never expires** and requires zero maintenance.

```bash
# 1. Login to get a temporary admin token
TOKEN=$(curl -sS -X POST "http://localhost:8585/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@open-metadata.org","password":"YWRtaW4="}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['accessToken'])")

# 2. Create the bot USER (isBot=true)
curl -sS -X POST "http://localhost:8585/api/v1/users" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "datalineage-doctor-bot",
    "displayName": "DataLineage Doctor Bot",
    "email": "dld-bot@open-metadata.org",
    "isBot": true,
    "roles": []
  }'

# 3. Create the BOT entity (botUser is a string — the user name)
curl -sS -X POST "http://localhost:8585/api/v1/bots" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "datalineage-doctor-bot",
    "displayName": "DataLineage Doctor Bot",
    "description": "Service account for DataLineage Doctor",
    "botUser": "datalineage-doctor-bot"
  }'

# 4. Generate a non-expiring token for the bot
curl -sS -X GET \
  "http://localhost:8585/api/v1/users/generateBotToken/datalineage-doctor-bot" \
  -H "Authorization: Bearer $TOKEN"
```

Copy the `JWTToken` from step 4 into `.env`:

```
OM_JWT_TOKEN=<paste token here>
```

---

### Option B — Runtime Credential Login (automatic fallback)

If `OM_JWT_TOKEN` is **empty**, `OMClient` and `wait_for_om.py` will automatically call
`POST /api/v1/users/login` using `OM_ADMIN_EMAIL` + `OM_ADMIN_PASSWORD` at startup.
The token is cached in-process and refreshed automatically on any `401` response.

**No container restarts needed. No manual token rotation.**

```
# .env — Option B
OM_JWT_TOKEN=
OM_ADMIN_EMAIL=admin@open-metadata.org
OM_ADMIN_PASSWORD=YWRtaW4=   # base64("admin") — OM demo default
```

---

## Common Error Patterns

| Error | Cause | Fix |
|---|---|---|
| `401` in `wait_for_om.py` | Static token expired | Use bot token (Option A) or leave `OM_JWT_TOKEN` empty (Option B) |
| `400 Cannot deserialize botUser` | Passed an object to `botUser` field | `botUser` must be a **string** (the user name), not a JSON object |
| `401` mid-run in OMClient | 1h user token expired | Auto-refreshed — no action needed with Option B |



--> NOTE: if API based bot creation fails, create a bot in UI -> settings -> Bot 