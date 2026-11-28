# Week 6 - Day 2: Interview Notes: Deployment, Operations and Repository Hygiene

## 1. Deployment stack (all free tier)

| Part | Service |
|---|---|
| Backend (Docker) | Render free web service (512 MB, sleeps after 15 minutes idle) |
| PostgreSQL + pgvector | Neon |
| Redis | Redis Cloud |
| Frontend | Vercel (environment variable `VITE_API_URL`) |
| CI | GitHub Actions |
| Keep-alive | A scheduled GitHub Action that pings `/health` every 10 minutes |

Cold start: after sleeping, the first request can take 30 to 60 seconds; the README says so.

---

## 2. Environment variables and startup failures

Two startup crashes taught how fail-fast checks behave:

1. `REDIS_EXPIRE=3600s` → `int("3600s")` raised `ValueError` and the app died before opening a port. Fix: the value must be a plain number. A tolerant parser was suggested for the code.
2. `SECRET_KEY` missing or too short → the startup validation stopped the app (correct behaviour). Fix: a random 32+ character key and `ALGORITHM` set in the Render environment.

Lesson: the local `.env` is not on the server. Check every environment variable on the host. A migration step in the entrypoint also runs on each start.

Required variable names: `DATABASE_URL`, `REDIS_URL`, `SECRET_KEY`, `ALGORITHM`, `VOYAGE_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`, `DEEPSEEK_API_KEY`, `RERANKER_BACKEND` (image default `onnx`), `VOYAGE_MIN_INTERVAL_SECONDS`, `EMBED_BATCH_TOKENS`.

---

## 3. Keep-alive workflow bug

The scheduled workflow failed with `curl: no URL specified` and `--max-time: command not found`. The `curl` command was split over two lines without a trailing backslash, so the shell treated `--max-time` as a separate command. Fix: one line, `--retry 3 --max-time 60`, and fail the job if the HTTP status is not 200.

---

## 4. CORS

The allowed origins are `localhost:5173` and the Vercel domain. Vercel preview deployments use changing domains, so an `allow_origin_regex` for the project's Vercel pattern was added. A 500 response produced by the catch-all handler bypasses CORS middleware, so the browser can show a CORS error instead of the real 500; request ids in the logs are used to trace it.

---

## 5. Repository hygiene

Issues found and how they were handled:

1. **An archive containing `.env` was committed** (via `git add -A`). It was caught before the first push. The local history was rewritten with `git rm --cached`, `git commit --amend`, `git tag -f`, `git reflog expire` and `git gc --prune=now`. Final checks: `git log --all -- backend.zip backend/.env` printed nothing.
2. **Wrong `.gitignore` patterns**: lines like `backend/.env` placed inside `backend/.gitignore` do not match. Correct patterns: `.env`, `uploads/`, `.venv/`.
3. **`eval/` ignored too broadly**: a rule `eval/` also matched `backend/eval/`; fixed with `/eval/` (root only).
4. **`node_modules` tracked at the repo root** by `git add .`; removed with `git rm -r --cached`.
5. **A symlink** `backend/eval → ../eval` made `git add backend/eval/...` fail ("beyond a symbolic link"); the folder was moved into `backend/`.
6. **Pre-push scans**: list tracked files for `.env`, zip, uploads, `.venv`, model files; `git grep` for API-key patterns. Placeholder keys in tests are fine; real keys mean rotate.
7. Provider keys that were ever shared in an archive should be rotated.

Other hygiene: personal documents (resumes, scorecards) were kept out of benchmarks and out of git; demo accounts for the public demo must be employee-only; old test accounts and their passwords were to be deleted from the database.

---

## 6. Security advisory handling (Ruby2Shell email)

A hosting provider sent an advisory about a Ruby vulnerability. Process followed: check whether any service uses Ruby (the backend is Python on a Python base image, the frontend builds with Node on another host, CI runs Python and curl), confirm the advisory is real, and avoid clicking links inside the email (open the dashboard directly). No action was required.

---

## 7. Observability basics available

- `/health` and `/health/ready`.
- Request ids on unexpected errors.
- Provider health endpoint and warnings in logs for fail-open events (Redis, reranker, rate limits).
- Not yet implemented: metrics, tracing and token-usage tracking (listed as next steps).

---

## 8. Interview Questions

### Q1. Why did the app crash at start on Render?
Environment variables on the host were wrong (`REDIS_EXPIRE=3600s`, missing or short `SECRET_KEY`). The `.env` file does not travel with the code.

### Q2. Why is failing at startup on bad config good?
Misconfiguration is detected immediately instead of causing unpredictable runtime failures.

### Q3. How do you keep a free Render instance awake and what is the catch?
A scheduled ping to `/health`. It stays within the free hours, and GitHub can disable scheduled workflows in inactive repositories; it is a free-tier workaround, not production design.

### Q4. How did you handle a secret that was committed locally?
Removed it from the commit before pushing, rewrote local history, expired the reflog and garbage collected, then verified with `git log --all`. Anything that was ever shared should be rotated.

### Q5. Why does `git add -A` need care?
It stages everything not ignored: archives, local databases, node_modules.

### Q6. What is the difference between a `.gitignore` in a subfolder and in the root?
Patterns are relative to the file's location.

### Q7. How do you deploy schema changes safely?
Migrations in the entrypoint, tested first on a throwaway database; `alembic stamp` for databases created before migrations existed.

### Q8. Why a CORS regex for Vercel previews?
Preview deployments get new domains for each branch or commit.