# NBA Teammate Chain

A full-stack NBA teammate-link game built with React, TypeScript, FastAPI, `nba_api`, and `pandas`.

<img width="1895" height="898" alt="image" src="https://github.com/user-attachments/assets/208a7935-a671-4bfb-a87a-28cd59fefde0" />


## Setup

```powershell
npm install
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Optional Google login:

```powershell
$env:VITE_GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
$env:GOOGLE_CLIENT_ID="your-google-client-id.apps.googleusercontent.com"
```

## Run

In one terminal:

```powershell
uvicorn backend.app:app --reload --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
npm run web
```

Open `http://127.0.0.1:5173`.

The backend uses live NBA data when `nba_api` can reach stats.nba.com. A small fallback dataset keeps the app usable if the API is unavailable during local development.

## GitHub Pages

`.github/workflows/deploy.yml` builds and deploys the Vite frontend to GitHub Pages on pushes to `main`.

GitHub Pages only hosts static frontend files. The FastAPI backend still needs a separate host for `/api/*` and `/ws/*`. After deploying the backend, set a repository variable named `VITE_API_BASE` to that backend URL before the Pages workflow runs.

For the live-player queue, the backend must run as a single process because queue and room state is stored in memory. On Render, use this start command:

```bash
uvicorn backend.app:app --host 0.0.0.0 --port $PORT --workers 1
```

If `VITE_API_BASE` is changed, rerun the GitHub Pages workflow so the static frontend picks up the backend URL.
