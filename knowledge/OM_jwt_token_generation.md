### OM JW Token Generation 

to genrate OM JWT token, we need to curl with demo admin/password of OM. 

```
curl -sS -X POST "http://localhost:8585/api/v1/users/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@open-metadata.org","password":"YWRtaW4="}'
```

The demo password is "admin" which is needed to be encoded in base-64.