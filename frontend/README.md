# DropVault frontend

Next.js, TypeScript, and Tailwind CSS interface for temporary file sharing.

## Pages

- `/` — upload a file with expiration, download limit, and optional password.
- `/success/[id]` — display the share link and management controls after upload.
- `/d/[token]` — public download page with password and link-state handling.
- `/dashboard` — files created in this browser, with status and management actions.

The browser stores the upload ID, management token, share token, and display metadata in localStorage. Management tokens are never included in public links. Clearing browser storage removes this browser's management access. There are no accounts.

## Run locally

Start the backend on port 8000. Then run `npm install` and `npm run dev` from this directory. The frontend runs at `http://localhost:3000` and proxies `/backend/*` to `http://127.0.0.1:8000`.

For Docker Compose, run `docker compose up --build` from the repository root. Compose sets `BACKEND_INTERNAL_URL=http://backend:8000`; the browser still calls the frontend's same-origin `/backend/*` path.

## Checks

Run `npm run lint` and `npm run build`. The production build uses webpack so it works in restricted local environments where Turbopack's CSS worker cannot bind a port.

## Browser automation

From the repository root, install dependencies with `cd frontend && npm ci && npx playwright install chromium && cd ..`, then run `python3 scripts/run_e2e.py`. The script uses isolated Docker services on port 3100, runs the five Playwright journeys, and tears down their test data. Run `python3 scripts/run_e2e.py --help` for options. Inspect `playwright-report/index.html` after a run; failure screenshots and traces are in `test-results/`. These directories are ignored by Git. See the root README for requirements and details.
