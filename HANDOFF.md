# HANDOFF — FacePass FabLab / AAMS

_Read this first if you are continuing this project in a new session._

## Where things stand (as of 23 Aug 2026)

- **Active working copy:** `C:\Users\iambr\OneDrive\Desktop\workspace3`
- **GitHub:** https://github.com/bruce12-glitch/AAMS — force-pushed 23 Aug, commit `a56bbff`, branch `main`. Git credentials are cached in Windows Credential Manager (no PAT needed for push).
- **Stale clone:** `C:\Users\iambr\OneDrive\Desktop\AAMS` is the OLD prototype clone (pre-overwrite). Its `ANALYSIS.md` describes the legacy single-file prototype only. Do not develop there.

## What the project is

FacePass FabLab — anti-proxy facial access + attendance system for SRMIST Fab Lab.
- `fablab-face-attendance/` — FastAPI backend: InsightFace (SCRFD+ArcFace, threshold 0.45), 9-row decision matrix, HMAC-signed QR passes, SQLite (`database/fablab.db`), Telegram alerts, APScheduler, pytest suite. Run: `python run.py` → http://localhost:8000
- `src/` + `index.html` — React/Vite console scaffold on Astryx components (NOT yet wired to the API)
- `legacy/`, `facepass-backend/`, root `server.js` — older generations, reference only

## Known gaps (next work items)

1. Wire React console to backend API (`/api/dashboard/*`, `/api/entry/*`)
2. `enrollment/enroll_user.py` stores a RANDOM placeholder embedding — implement real 5-pose webcam capture
3. `liveness.py` EAR blink detection needs a 68/106-point landmark model
4. `/api/entry` accepts raw embeddings client-side — should accept images and detect server-side
5. CORS is `*`, admin routes have no auth
6. `config.yaml` has placeholder secrets — real values go in `.env`

## Environment notes

- MCP servers bridged in `C:\Users\iambr\.dsh\profiles\web\cordis.patch.yml` (hot-reloaded):
  playwright, sequentialthinking, memory, docker, sqlite (→ fablab.db), github
- **Docker Desktop must be started manually** for the docker MCP tools to work
- **GitHub MCP needs `GITHUB_PERSONAL_ACCESS_TOKEN`** env var — not yet set
- SQLite db verified: 6 users, 9 entry_logs, 5 alerts, 5 occupants, 1 admin_action
