#!/bin/bash
# Automated PostgreSQL backup script for production.

set -euo pipefail

TIMESTAMP=$(date +"%Y%m%d-%H%M%S")
BACKUP_DIR=${BACKUP_DIR:-/backups/postgres}
RETENTION_DAYS=${RETENTION_DAYS:-30}
DATABASE_URL=${DATABASE_URL:-"postgresql://$POSTGRES_USER:$POSTGRES_PASSWORD@$POSTGRES_SERVER:$POSTGRES_PORT/$POSTGRES_DB"}
LOG_FILE=${BACKUP_LOG_FILE:-/var/log/tahlilchi/backup.log}

mkdir -p "$BACKUP_DIR"
mkdir -p "$(dirname "$LOG_FILE")"

log() {
  echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

BACKUP_FILE="${BACKUP_DIR}/pg-backup-${TIMESTAMP}.sql.gz"

log "Starting PostgreSQL backup to $BACKUP_FILE"

PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
  --dbname="$DATABASE_URL" \
  --format=plain \
  --no-owner \
  --no-privileges \
  | gzip > "$BACKUP_FILE"

log "Backup completed: $BACKUP_FILE"

find "$BACKUP_DIR" -name 'pg-backup-*.sql.gz' -mtime +${RETENTION_DAYS} -delete

log "Removed backups older than ${RETENTION_DAYS} days"

if [ -n "${S3_BUCKET:-}" ]; then
  log "Uploading backup to S3 bucket $S3_BUCKET"
  aws s3 cp "$BACKUP_FILE" "s3://${S3_BUCKET}/postgres/"
fi

log "Backup script finished successfully"
