# HANDOFF — FacePass FabLab / AAMS

_Read this first if you are continuing this project in a new session._

## Where things stand (as of 25 Aug 2026)

- **Working copy:** `C:\Users\iambr\OneDrive\Desktop\AAMS` — synced with `origin/main`.
- **GitHub:** https://github.com/bruce12-glitch/AAMS — branch `main`. Credentials cached in Windows Credential Manager.
- **Repo cleaned:** legacy generations removed (`server.js`, `facepass-backend/`, `legacy/`, `ANALYSIS.md`). Only the FastAPI backend and the React console remain.

## Layout

- `fablab-face-attendance/` — FastAPI backend: InsightFace (SCRFD+ArcFace, threshold 0.45), 9-row decision matrix, HMAC-signed QR passes, SQLite (`database/fablab.db`, gitignored), Telegram alerts, APScheduler. Run: `python run.py` → http://localhost:8000
- Root — React 19 / Vite console: Three.js background (lazy chunk), Framer Motion transitions, polling hooks with mock fallback. Run: `npm run dev` → http://localhost:3000 (proxies `/api` → :8000)
- Python deps live in `fablab-face-attendance/venv` (gitignored) — recreate with `pip install -r requirements.txt`.

## Known gaps (next work items)

1. Wire real webcam capture into `enrollment/enroll_user.py` (stores a placeholder embedding today)
2. `/api/entry` should accept images and detect server-side (currently receives raw embeddings)
3. `liveness.py` EAR blink detection needs a 68/106-point landmark model
4. CORS is `*`, admin routes have no auth — lock down before deployment
5. Real secrets go in `.env` (never committed); `config.yaml` holds placeholders

## Environment notes

- Frontend verified: `npm run build` passes; dev server boots on :3000.
- Backend not yet installed in this clone (`venv/` setup pending); DB schema + seed scripts ready via `python -m scripts.create_db` / `seed_demo_data`.
