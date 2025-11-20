## Backup & Restore

1. **Database (PostgreSQL)**
   - Run `scripts/backup-postgres.sh` nightly; store dumps in encrypted object storage with 30-day retention.
   - For point-in-time recovery, enable WAL archiving to cloud storage; verify restore drills monthly by replaying WAL onto a staging instance.
   - Keep Alembic migrations in sync with database state; never skip migrations during restore rehearsals.

2. **Vector Store (Qdrant)**
   - Snapshot collections (`qdrant.snapshots.create`) after every successful indexing batch and replicate snapshots to cold storage.
   - During recovery, recreate the container, restore snapshots, then replay any queued document-processing jobs.

3. **Redis / Celery**
   - Persist rate-limit counters only if SLAs require; otherwise treat Redis as ephemeral. For Celery, re-queue unfinished jobs after cluster restarts.

4. **Documents & Uploads**
   - Store user uploads under `data/uploads/` on shared storage with versioned backups. Keep `.gitkeep` placeholders so the directories stay tracked.

5. **Disaster Recovery Test**
   - Quarterly, execute a full DR test: provision new infrastructure, restore Postgres snapshot, restore Qdrant snapshot, and replay Celery jobs. Capture RTO/RPO gaps and feed them back into runbooks.

