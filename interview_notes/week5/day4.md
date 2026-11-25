# Week 5 - Day 4: Interview Notes: Production Readiness, Docker, Health Checks and CI

(Builds on Week 3 Day 5, which introduced Docker and Docker Compose.)

## 1. Production Docker image

- Base image `python:3.13-slim`.
- Runs as a **non-root user** (`appuser`).
- `HEALTHCHECK` calls `/health`.
- An `entrypoint.sh` runs `alembic upgrade head` and then starts `uvicorn` on `0.0.0.0:8000`. The container migrates the database on every start.
- `.dockerignore` excludes `.env`, `.venv`, uploads, logs, caches, zip files and result files so secrets and junk never enter the image.

Compose files:

- `docker-compose.yml`: pgvector Postgres, Redis, backend, named volumes for the database and uploads, no source mount, no `--reload`. Secrets only from environment or `.env`.
- `docker-compose.dev.yml`: a development override with a source mount and `--reload`.

---

## 2. Health endpoints

- `GET /health`: liveness. Always 200 and has no dependencies.
- `GET /health/ready`: readiness. Runs `SELECT 1` on the database (503 if down) and pings Redis (if Redis is down it still returns 200 with `redis = "degraded"`).

Liveness answers "is the process alive?" and readiness answers "can it serve requests?".

---

## 3. CI with GitHub Actions

Workflow `ci.yml`: install dependencies, run `pytest`, build the Docker image (no push).

Problems fixed to make it green:

1. **Secret needed at import time.** `voyageai.Client(...)` was created when `utils/embedding.py` was imported. CI had no `VOYAGE_API_KEY`, so test collection failed. Fix: a lazy client that is created on first use.
2. **No `.env` in CI.** Local runs passed because a `.env` file existed. Fix: dummy environment variables in the workflow (a random `SECRET_KEY` of 32+ characters, `ALGORITHM`, dummy provider keys). Tests never call real providers.
3. **Model files are gitignored.** CI runs the download script for the ONNX model and caches the files; torch-dependent tests skip cleanly when torch is missing.
4. **Deprecation warning** for old Node versions: action versions were upgraded.

Proof method: a **fresh clone** with no `.env` and no model files, with only the workflow's variables set, ran 211 tests and the Docker build successfully.

**CI trap:** "Re-run jobs" always re-runs the old commit. A fix only shows up in a new run created by a new push. This caused confusion when an old failing log was posted after the fix had been pushed.

---

## 4. Documentation

- `README.md`: features, mermaid architecture diagram, Docker and bare-metal setup, environment variable table (names only), API overview, roles table, test and benchmark commands, migration commands, known limitations.
- `docs/ARCHITECTURE.md`: sequence diagram of the chat pipeline and a results table taken from real benchmark files.

---

## 5. Interview Questions

### Q1. Why run as a non-root user in Docker?
It limits the damage if the container is compromised.

### Q2. Liveness vs readiness?
Liveness: the process is running. Readiness: dependencies are available so it can serve traffic.

### Q3. Why does Redis down not fail the readiness probe?
Redis is a cache; the app works without it, so it reports `degraded` instead.

### Q4. Why run migrations in the entrypoint?
Each deployment starts with the schema at the latest version, with no manual step.

### Q5. Why did CI fail when local tests passed?
Local runs had a `.env` file and model files that are not in git.

### Q6. How do you make tests independent of secrets?
Lazy clients, dummy environment variables, and mocked providers.

### Q7. What does "re-run jobs" do?
It re-runs the same commit; it does not pick up newer code.

### Q8. How did you prove the CI fix before pushing?
By running the exact CI steps in a fresh clone without `.env` or model files.