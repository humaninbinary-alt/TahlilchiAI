#!/bin/bash
# PostgreSQL restore procedure for production.

set -euo pipefail

if [ $# -ne 1 ]; then
  echo "Usage: $0 <backup-file.sql.gz>"
  exit 1
fi

BACKUP_FILE=$1
DATABASE_URL=${DATABASE_URL:-"postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_SERVER:$POSTGRES_PORT/$POSTGRES_DB"}
LOG_FILE=${RESTORE_LOG_FILE:-/var/log/tahlilchi/restore.log}

if [ ! -f "$BACKUP_FILE" ]; then
  echo "Backup file not found: $BACKUP_FILE"
  exit 1
fi

log() {
  echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

log "Stopping application services"
docker compose -f docker-compose.prod.yml down api celery-worker celery-beat || true

log "Dropping existing database"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_SERVER" -U "$POSTGRES_USER" -c "DROP DATABASE IF EXISTS $POSTGRES_DB;"
log "Creating fresh database"
PGPASSWORD="$POSTGRES_PASSWORD" psql -h "$POSTGRES_SERVER" -U "$POSTGRES_USER" -c "CREATE DATABASE $POSTGRES_DB;"

log "Restoring backup from $BACKUP_FILE"
gunzip -c "$BACKUP_FILE" | PGPASSWORD="$POSTGRES_PASSWORD" psql "$DATABASE_URL"

log "Running migrations"
docker compose -f docker-compose.prod.yml run --rm api alembic upgrade head

log "Starting application services"
docker compose -f docker-compose.prod.yml up -d api celery-worker celery-beat

log "Restore completed successfully"
