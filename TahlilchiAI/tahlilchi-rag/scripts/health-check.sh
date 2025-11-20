#!/bin/bash
# Comprehensive health check script for production environment.

set -euo pipefail

API_URL=${API_URL:-"https://api.tahlilchi.com"}
HEALTH_ENDPOINTS=("/health" "/health/ready")
LOG_FILE=${HEALTH_LOG_FILE:-/var/log/tahlilchi/health-check.log}

log() {
  echo "$(date -Iseconds) $1" | tee -a "$LOG_FILE"
}

check_endpoint() {
  local endpoint=$1
  log "Checking API endpoint ${API_URL}${endpoint}"
  if ! curl -sf "${API_URL}${endpoint}" > /dev/null; then
    log "ERROR: Endpoint ${endpoint} is unhealthy"
    return 1
  fi
  return 0
}

check_service() {
  local name=$1
  local command=$2
  log "Checking ${name}"
  if ! eval "$command" > /dev/null 2>&1; then
    log "ERROR: ${name} check failed"
    return 1
  fi
  return 0
}

STATUS=0

for endpoint in "${HEALTH_ENDPOINTS[@]}"; do
  check_endpoint "$endpoint" || STATUS=1
done

check_service "PostgreSQL" "PGPASSWORD=$POSTGRES_PASSWORD psql -h $POSTGRES_SERVER -U $POSTGRES_USER -d $POSTGRES_DB -c 'SELECT 1'"
if [ $? -ne 0 ]; then STATUS=1; fi

check_service "Redis" "redis-cli -h $REDIS_HOST -p $REDIS_PORT -a $REDIS_PASSWORD ping"
if [ $? -ne 0 ]; then STATUS=1; fi

check_service "Qdrant" "curl -sf $QDRANT_URL/health"
if [ $? -ne 0 ]; then STATUS=1; fi

check_service "Ollama" "curl -sf $OLLAMA_BASE_URL/api/tags"
if [ $? -ne 0 ]; then STATUS=1; fi

log "Checking Celery workers"
if ! docker compose -f docker-compose.prod.yml ps celery-worker | grep -q "Up"; then
  log "ERROR: Celery worker not running"
  STATUS=1
fi

log "Checking disk usage"
DISK_USAGE=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
if [ "$DISK_USAGE" -gt 85 ]; then
  log "WARNING: Disk usage critical (${DISK_USAGE}%)"
  STATUS=1
fi

log "Checking memory usage"
MEM_USAGE=$(free | awk '/Mem:/ {printf("%.0f", $3/$2 * 100.0)}')
if [ "$MEM_USAGE" -gt 85 ]; then
  log "WARNING: Memory usage critical (${MEM_USAGE}%)"
  STATUS=1
fi

if [ $STATUS -eq 0 ]; then
  log "All checks passed"
else
  log "One or more checks failed"
fi

exit $STATUS
