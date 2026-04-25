### OM JW Token Generation 

to genrate OM JWT token, we need to curl with demo admin/password of OM. 

```
curl -sS -X POST "http://localhost:8585/api/v1/users/login" \
-H "Content-Type: application/json" \
-d '{"email":"admin@open-metadata.org","password":"YWRtaW4="}'
```

The demo password is "admin" which is needed to be encoded in base-64.

If `make demo` returns 401 while running `scripts/wait_for_om.py`, then update then get a fresh token, update the env, and recreate the app and worker container: `docker compose up -d --force-recreate --no-deps app worker`

note: if image has been chnaged, run: `docker compose up -d --build --force-recreate app worker`