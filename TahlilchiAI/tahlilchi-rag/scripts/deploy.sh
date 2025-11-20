#!/bin/bash
# Production deployment script for TahlilchiAI RAG System

set -euo pipefail

COMPOSE="docker compose -f docker-compose.prod.yml"
LOG_FILE=${DEPLOY_LOG_FILE:-/var/log/tahlilchi/deploy.log}

log() {
  echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

if [ ! -f .env.production ]; then
  log "ERROR: .env.production file missing"
  exit 1
fi

log "Starting deployment workflow"

log "1) Backing up database"
./scripts/backup-postgres.sh

log "2) Pulling latest code"
git pull --ff-only

log "3) Building updated images"
$COMPOSE build

log "4) Stopping application containers"
$COMPOSE stop api celery-worker celery-beat || true

log "5) Applying migrations"
$COMPOSE run --rm api alembic upgrade head

log "6) Starting updated services"
$COMPOSE up -d api celery-worker celery-beat nginx

log "7) Running health checks"
./scripts/health-check.sh

log "8) Removing old images"
docker image prune -f

log "Deployment completed successfully"
