# HANDOFF — FacePass FabLab / AAMS

_Read this first if you are continuing this project in a new session._

## Where things stand (as of 25 Aug 2026)

- **Working copy:** `C:\Users\iambr\OneDrive\Desktop\AAMS` — synced with `origin/main`.
- **GitHub:** https://github.com/bruce12-glitch/AAMS — branch `main`. Credentials cached in Windows Credential Manager.
- **Repo cleaned:** legacy generations removed (`server.js`, `facepass-backend/`, `legacy/`, `ANALYSIS.md`). Only the FastAPI backend and the React console remain.

## Verified working (25 Aug 2026)

- Backend venv at `fablab-face-attendance/venv`; `pytest` 12/12 passing.
- Server boots without models; CV engine lazy-loads — confirmed `buffalo_l` downloaded & loaded.
- Real image entry verified end-to-end: Lena test photo → SCRFD detected 1 face → ArcFace embedding → 1:N match → UNKNOWN denial + alert + evidence photo saved.
- Frontend `npm run build` passes; Members page has Enroll modal (photo upload → server-side embeddings → signed QR); Live Monitor has Snapshot Entry Test (real `/api/entry/process`).

## Layout

- `fablab-face-attendance/` — FastAPI backend: InsightFace (SCRFD+ArcFace, threshold 0.45), 9-row decision matrix, HMAC-signed QR passes, SQLite (`database/fablab.db`, gitignored), Telegram alerts, APScheduler. Run: `python run.py` → http://localhost:8000
- Root — React 19 / Vite console: Three.js background (lazy chunk), Framer Motion transitions, polling hooks with mock fallback. Run: `npm run dev` → http://localhost:3000 (proxies `/api` → :8000)
- Key modules: `app/vision.py` (image decode → pipeline), `app/liveness.py` (106-pt blink EAR), `app/security.py` (CORS + X-Admin-Token), `POST /api/users/enroll`.

## Known gaps (next work items)

1. **Human-in-the-loop only:** physically run webcam enrollment CLI with volunteers (`python -m enrollment.enroll_user`), collect real consent forms, mount hardware.
2. Blink liveness thresholds need calibration against a real webcam burst (config in `app/liveness.py`).
3. Threshold calibration study (RQ1): enroll 10–20 users, plot genuine vs impostor distributions.
4. Set real secrets in `.env` (Telegram token/chat id, QR secret, admin password) before any live demo.
5. Optional: RTSP/IP-camera source for the entrance instead of USB webcam.

## Environment notes

- Frontend verified: `npm run build` passes; dev server boots on :3000.
- Backend not yet installed in this clone (`venv/` setup pending); DB schema + seed scripts ready via `python -m scripts.create_db` / `seed_demo_data`.
