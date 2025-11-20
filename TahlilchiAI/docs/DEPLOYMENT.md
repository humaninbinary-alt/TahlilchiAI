# Deployment Guide

## 1. System Requirements
### Hardware
- CPU: 4+ cores (8+ recommended)
- RAM: 16GB minimum (32GB recommended)
- Storage: 100GB SSD (separate volume for backups)

### Operating System
- Ubuntu 22.04 LTS (or latest LTS equivalent)
- Kernel updated and security patches applied

### Software Versions
- Docker Engine 24.0+
- Docker Compose Plugin 2.20+
- Python 3.11+ (for scripts)
- AWS CLI (if uploading backups)

## 2. Pre-deployment Checklist
- [ ] Server provisioned and access secured
- [ ] Firewall rules applied (allow 22,80,443)
- [ ] SSL certificates issued (Let's Encrypt or managed)
- [ ] DNS records configured (api, admin domains)
- [ ] Backup storage configured (local path + remote bucket)
- [ ] Monitoring stack ready (Prometheus/Grafana or external)
- [ ] Alerting configured (email/SMS/Slack)
- [ ] Secrets generated and stored securely (Password manager / secret manager)

## 3. Initial Setup
1. Clone repository: `git clone <repo>`
2. Copy environment file: `cp .env.production.example .env.production`
3. Populate secrets (JWT, DB, Redis, tokens)
4. Pull Ollama model (optional offline): `docker compose run --rm ollama ollama pull qwen2.5:7b`
5. Initialize PostgreSQL schema: `docker compose run --rm api alembic upgrade head`
6. Create initial admin user (via API or SQL script)

## 4. Deployment Steps
1. **Backup**: `./scripts/backup-postgres.sh`
2. **Pull code**: `git pull --ff-only`
3. **Build**: `docker compose -f docker-compose.prod.yml build`
4. **Stop old containers**: `docker compose stop api celery-worker celery-beat`
5. **Migrate**: `docker compose run --rm api alembic upgrade head`
6. **Start services**: `docker compose up -d api celery-worker celery-beat nginx`
7. **Health check**: `./scripts/health-check.sh`
8. **Verify**: Access `/health/ready`, `/metrics`, admin dashboard

Troubleshooting tips:
- Use `docker compose logs -f api` for API issues
- Ensure `.env.production` is mounted and values correct
- Confirm nginx pointing to internal API network

## 5. Post-Deployment Verification
- Access API docs (via HTTPS) and ensure 200 OK
- Login as admin, validate authentication
- Upload test document (PDF) and confirm processing
- Run chat query and check streaming responses
- Confirm logs (app/error) show no exceptions
- Confirm `/metrics` exposes Prometheus data

## 6. Operational Maintenance
### Daily
- Review logs (app/error/nginx)
- Check monitoring dashboard and alerts
- Ensure backups completed successfully

### Weekly
- Review metrics (latency, error rates)
- Validate rate limiting and security events
- Check storage usage for uploads/backups

### Monthly
- Update dependencies and base images
- Test restore procedure in staging
- Rotate secrets (Database, Redis, JWT) if policy requires

## 7. Troubleshooting
### Common Issues
| Symptom | Possible Causes | Resolution |
|---------|----------------|-----------|
| API unhealthy | DB connection failure | Check DB logs, ensure credentials and firewall |
| High latency | LLM server busy | Scale Celery workers / allocate more CPU/RAM |
| Document processing stuck | Qdrant unreachable | Check network routes and health checks |
| SSL errors | Cert expired/mismatch | Renew certs, reload nginx |

### Logs Locations
- `logs/app.log`, `logs/error.log`
- `logs/nginx/access.log`, `logs/nginx/error.log`
- Docker logs: `docker compose logs -f <service>`

### Rollback Procedure
1. Stop new services: `docker compose down`
2. Restore DB: `./scripts/restore-postgres.sh <backup>`
3. Checkout previous git tag: `git checkout <tag>`
4. Deploy again using `scripts/deploy.sh`
5. Verify health and metrics

### Escalation
- On-call engineer contacts: [team email / Slack channel]
- Document incidents and remediation steps
