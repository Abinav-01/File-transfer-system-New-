# File transfer System


DropVault is a secure, ephemeral file sharing platform designed for local-only deployment.

## Overview
DropVault allows users to upload files and generate temporary shareable download links. Links can expire after a configured duration, optionally require a password, and optionally enforce a maximum number of downloads.

## Technologies
- **Frontend**: Next.js, React, TypeScript, Tailwind CSS
- **Backend**: Python, FastAPI, SQLAlchemy, Pydantic
- **Database & Services**: PostgreSQL, Redis, MinIO (S3-compatible API), Celery
- **Infrastructure**: Docker, Docker Compose

## Architecture
The project follows a monorepo structure:
- `/frontend`: Next.js frontend application.
- `/backend`: FastAPI backend application and Celery workers, structured with a layered architecture (API, core, models, schemas, services, repositories).

## Local Setup Instructions

1. Ensure Docker and Docker Compose are installed on your system.
2. Clone the repository.
3. Copy `.env.example` to `.env` (optional, as defaults are provided in docker-compose).
4. Run the application and apply migrations:
   ```bash
   docker compose up --build -d
   docker compose exec -T backend alembic upgrade head
   ```
5. Access the services:
   - Frontend: `http://localhost:3000`
   - Backend API Docs: `http://localhost:8000/docs`
   - MinIO Console: `http://localhost:9001` (Credentials: admin/password)

## Current Functionality
Uploads, protected downloads, download limits, management-token deletion, periodic cleanup, Redis rate limits, the Next.js frontend, and local automation scripts are implemented. The `/health` endpoint reports PostgreSQL, Redis, and MinIO availability.

## Background cleanup and rate limits

Celery Beat schedules `app.workers.tasks.cleanup_expired_uploads` every 300 seconds by default; the worker runs it. Cleanup removes MinIO objects for expired uploads and uploads whose download limit was reached. Expired ACTIVE records become `EXPIRED`; limit-reached records keep `DOWNLOAD_LIMIT_REACHED`. Repeated cleanup is safe because deleting an absent MinIO object succeeds. Each upload is processed separately, so a failed object does not stop the rest.

Redis applies fixed-window limits by client IP: 100 uploads/hour and 120 downloads/hour. Five incorrect passwords for one link from one IP block further attempts for 15 minutes. Successful protected downloads clear failures. Configure `UPLOAD_RATE_LIMIT`, `UPLOAD_RATE_WINDOW_SECONDS`, `DOWNLOAD_RATE_LIMIT`, `DOWNLOAD_RATE_WINDOW_SECONDS`, `PASSWORD_FAILURE_LIMIT`, `PASSWORD_FAILURE_WINDOW_SECONDS`, and `CLEANUP_INTERVAL_SECONDS` through environment variables. The app uses the direct connection IP, not an untrusted forwarded header. If Redis is unavailable, uploads and downloads return HTTP 503 (`Rate limiting unavailable`); the service fails closed rather than silently bypassing limits. Celery also needs Redis and resumes scheduled work when it returns.

## Local scripts

Run from any directory with `python /path/to/DropVault/scripts/<name>.py --help`. Scripts find the project root from their own location.

| Script | Purpose | Example |
| --- | --- | --- |
| `setup_dev.py` | Validate Compose configuration; `--start` builds/starts services and applies migrations | `python scripts/setup_dev.py --start` |
| `seed_database.py` | Upload three sample files through the API and print their share and management tokens | `python scripts/seed_database.py` |
| `generate_test_files.py` | Generate text, JSON, empty, and configurable binary samples | `python scripts/generate_test_files.py --output test-files --max-size-mb 5` |
| `cleanup_expired.py` | Run the cleanup function immediately in the backend container | `python scripts/cleanup_expired.py` |
| `health_check.py` | Print PASS/FAIL for backend, PostgreSQL, Redis, and MinIO | `python scripts/health_check.py` |
| `run_tests.py` | Run isolated backend pytest with coverage and JUnit XML; optionally frontend lint | `python scripts/run_tests.py --frontend` |

The Compose-backed scripts require Docker Compose and running services. All scripts return a nonzero exit code on failure.

## Logs and metrics

Backend request and domain logs are JSON. Each HTTP response has an `X-Request-ID` header. Request logs use route templates (for example `/api/files/{share_token}/download`) so share tokens are not logged. Domain logs use upload IDs and safe reason codes; passwords, hashes, management tokens, and file bytes are never logged.

Example lines (IDs are illustrative):

```json
{"timestamp":"2026-09-18T16:42:33+00:00","level":"INFO","request_id":"606c7b75-8515-49c5-8502-515831a088fe","message":"UPLOAD_CREATED","event":"UPLOAD_CREATED","upload_id":"2e690439-67ab-47b4-a57d-3a18d07687c6"}
{"timestamp":"2026-09-18T16:42:33+00:00","level":"INFO","request_id":"606c7b75-8515-49c5-8502-515831a088fe","message":"HTTP_REQUEST","method":"POST","path":"/api/uploads","status_code":201,"duration_ms":179.36}
```

To follow one request:

```bash
curl -i http://localhost:8000/health
# Copy the X-Request-ID response header, then:
docker compose logs backend | grep 'YOUR-REQUEST-ID'
```

`GET /metrics` returns Prometheus-compatible text backed by Redis, shared between the API and Celery worker. Available counters are HTTP requests, uploads, successful and rejected downloads, expired files, manual deletions, cleanup failures, and rate-limit rejections. HTTP duration is exposed as a count and sum in seconds. Metrics are cumulative while the Redis data persists; `/metrics` returns 503 when Redis is unavailable. Ordinary metrics writes are best-effort so a telemetry outage does not undo a successful upload, download, deletion, or cleanup. No Grafana service is required.

```bash
curl http://localhost:8000/metrics
docker compose logs -f backend celery-worker
```

## Automated tests

Run the complete backend suite with `python scripts/run_tests.py`. The script starts dedicated PostgreSQL, Redis, and MinIO test containers with no published ports, runs Alembic migrations, then removes the containers and volumes. Each API and integration test clears the test database, Redis database, and MinIO bucket before and after execution. Development data is not touched.

Tests live in `backend/tests/unit`, `backend/tests/api`, and `backend/tests/integration`; reusable service fixtures are in `backend/tests/fixtures`. The test image includes Pytest, pytest-asyncio, pytest-cov, and httpx. Results are written to [backend/test-results/htmlcov/index.html](backend/test-results/htmlcov/index.html) and `backend/test-results/junit.xml`; terminal branch-aware coverage is printed during the run. Use `python scripts/run_tests.py --frontend` to run frontend lint afterward.

## Browser journeys

Install frontend dependencies and the Playwright Chromium browser once, then run the isolated E2E stack from the repository root:

```bash
cd frontend && npm ci && npx playwright install chromium && cd ..
python3 scripts/run_e2e.py
```

The script builds and starts a separate Docker Compose project (`dropvault-e2e`) with PostgreSQL, Redis, MinIO, backend, and frontend; applies migrations; runs five browser journeys at `http://127.0.0.1:3100`; and removes the test containers and volumes even if a test fails. Port 3100 must be free. Docker Compose, Node.js/npm, Python 3, and Chromium installed through Playwright are required. `python3 scripts/run_e2e.py --help` shows CLI options; use `--headed` to watch the browser. It exits nonzero on startup or test failure.

The journeys cover a normal download, password rejection and success, a one-download limit, dashboard deletion, and an expired link created by an isolated test fixture. Results are in `frontend/playwright-report/index.html`. Failed tests capture screenshots and traces under `frontend/test-results/`; both output directories are ignored by Git. Open a trace with `cd frontend && npx playwright show-trace test-results/<test-directory>/trace.zip`.

## Continuous integration

GitHub Actions runs validation on pull requests and pushes to `main`. It builds and tests the application only; it does not deploy it.

```text
Git push / PR
    ↓
Static checks (Ruff, TypeScript, ESLint)
    ↓
Unit and API tests (coverage + JUnit XML)
    ↓
Integration tests (PostgreSQL, Redis, MinIO; concurrent final download)
    ↓
Frontend production build
    ↓
Playwright browser journeys
    ↓
Docker Compose configuration and image builds
    ↓
PASS
```

The workflow is in `.github/workflows/ci.yml`. The GitHub repository root must be this directory so Actions can see the workflow and both applications. Its two backend test jobs use separate Docker Compose projects and write HTML coverage and JUnit reports. The E2E job uploads its HTML report and, on failure, screenshots and traces. Reports are retained as GitHub Actions artifacts for 14 days. Each stage fails the pipeline on a failed check, test, or build. To reproduce the backend test stages locally, use `python3 scripts/run_tests.py`; run `python3 scripts/run_e2e.py` for the browser stage and `docker compose build backend celery-worker celery-beat frontend` for the image build stage.
