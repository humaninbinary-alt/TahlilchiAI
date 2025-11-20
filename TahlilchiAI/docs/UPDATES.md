## Update & Deployment Procedure

1. **Pre-flight**
   - Branch from `main`, run `black`, `isort`, `ruff` (or `flake8`), and `pytest`.
   - Verify alembic migrations are up-to-date: `alembic revision --autogenerate` (if needed) then `alembic upgrade head`.

2. **Dependency changes**
   - Update `requirements.txt`, rebuild local images, and run `pip check`.
   - Capture dependency diffs in the release notes and run `safety check` before merging.

3. **Docker build**
   - `docker-compose build api worker` followed by `docker-compose up -d`.
   - Run integration tests against the stack; ensure Qdrant, Redis, Postgres containers pass health checks.

4. **Database migrations**
   - Apply migrations in production via `docker-compose exec api alembic upgrade head`.
   - Monitor logs for failures; roll back using the exported snapshot if necessary.

5. **Post-deploy**
   - Smoke test critical flows (document upload, retrieval, streaming answer).
   - Verify monitoring dashboards and alerts remain green. If regressions occur, roll back using the previous image tag and note follow-up tasks here.

