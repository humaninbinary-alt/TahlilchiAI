## Monitoring & Alerting

- **API layer (FastAPI)**
  - Export request latency, throughput, and error rates via the `/metrics` endpoint. Track P95 latency < 2s, 5xx rate < 1%.
  - Instrument SSE streaming to emit open-connection counts and completion rates.

- **Background jobs**
  - Emit Celery task metrics: queue depth, success/failure counts, processing duration per pipeline stage (parse, embed, index).
  - Alert when pending document jobs exceed 50 per tenant or when average task duration doubles relative to baseline.

- **Database & Vector Store**
  - Monitor Postgres connections, slow queries, and replication lag. Add alerts for connection pool exhaustion and WAL disk usage.
  - Track Qdrant RAM usage, collection sizes, and snapshot failures.

- **Rate limiting & security**
  - Observe Redis latency and keyspace hits/misses; alert on sudden spikes in blocked requests (possible abuse).
  - Ship authentication failures and permission-denied events to a SIEM for anomaly detection.

- **Infrastructure**
  - Use container health checks plus uptime probes (via `scripts/health-check.sh`) to detect crashed services quickly.
  - Tie alerts to on-call rotations with clear runbooks referencing this document.

