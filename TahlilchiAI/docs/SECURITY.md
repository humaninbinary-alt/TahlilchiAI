## Security Checklist

- Enforce JWT authentication on every protected route and validate tenant scope by verifying both `sub` and `tenant_id` claims before executing business logic.
- Require HTTPS/TLS termination at the ingress (e.g., Nginx) and enforce `SECURE` cookies plus HSTS in production.
- Store all credentials (Postgres, Redis, Qdrant, JWT secrets) exclusively in environment variables or secret managers; never bake them into images.
- Use bcrypt via `app.core.security` for password hashing and rotate the `JWT_SECRET_KEY` through a secure secret-management workflow.
- Limit surface area by enabling CORS only for trusted origins and rate limiting for tenants, users, and endpoints at Redis.
- Audit background tasks and Celery workers: isolate broker credentials, enable TLS where supported, and restrict queue access by network policy.
- Enable structured logging with request, tenant, and user context while scrubbing PII and secrets before logs leave the cluster.
- Run dependency vulnerability scans (e.g., `safety`, `pip-audit`) as part of CI and patch critical CVEs immediately.

