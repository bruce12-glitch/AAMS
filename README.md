# AAMS — FacePass FabLab

**Smart Anti-Proxy Facial Access and Attendance Management System** for the SRMIST Fab Lab.

This repository contains three generations of the project:

| Directory | What it is | Status |
|---|---|---|
| `fablab-face-attendance/` | **Main system** — FastAPI backend with InsightFace recognition, SQLite, Telegram alerts, APScheduler, tests | Active development |
| `src/` + `App.jsx` | React (Vite) console front-end built on Astryx Design components | Scaffold |
| `index.html` + `server.js` | Original single-file HTML/JS console prototype (static demo) | Legacy |
| `facepass-backend/` | Phase-1 webcam face-matching experiment script | Legacy |
| `legacy/` | Recovered fragment of a newer console UI found corrupted in the workspace tar | Reference only |

## Quick start — backend

```bash
cd fablab-face-attendance
python -m venv venv
venv\Scripts\activate        # Windows (or source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env       # then edit secrets
python -m scripts.create_db
python -m scripts.seed_demo_data   # optional demo data
python run.py                # API on http://localhost:8000 (docs at /docs)
```

First run downloads InsightFace `buffalo_l` models (~500 MB) into `models/insightface/`.

## Quick start — frontend

```bash
npm install
npm run dev                  # Vite dev server on http://localhost:3000
```

The React app uses `@astryxdesign/core` + `@astryxdesign/theme-neutral` (see `src/main.jsx`
for the required CSS imports). The legacy static prototype still works via `npm start`
(node `server.js`, port 3000 — stop Vite first, they share the port).

## Backend architecture

```
fablab-face-attendance/
├── app/                     # Core modules
│   ├── main.py              # FastAPI app + CORS + startup wiring
│   ├── config.py            # config.yaml + .env loader
│   ├── database.py          # SQLite schema (6 tables) + helpers
│   ├── face_engine.py       # InsightFace SCRFD + ArcFace, quality checks, 1:N search
│   ├── liveness.py          # Blink detection via Eye Aspect Ratio (EAR)
│   ├── identity.py          # 1:1 token+face and 1:N face-only verification
│   ├── access_policy.py     # 9-row decision matrix (§11.2) + state machine
│   ├── occupancy.py         # Inside/exit/timeout tracking (§14)
│   ├── alerts.py            # Telegram alerts with photo evidence (§15)
│   ├── reports.py           # Daily/weekly/proxy/unpaid/occupancy reports
│   ├── scheduler.py         # APScheduler: 8 PM report, 5-min timeouts, 23:00 backup
│   ├── qr_manager.py        # HMAC-SHA256 signed QR tokens (§27.3)
│   ├── camera.py            # Threaded webcam capture at controlled FPS
│   └── utils.py
├── api/                     # FastAPI routers: entry, users, alerts, occupants,
│                            # reports, dashboard, admin
├── enrollment/              # CLI enrollment (5 poses → 3 embeddings + QR)
├── scripts/                 # create_db, seed_demo_data, backup_db, generate_qr
├── tests/                   # pytest: decision matrix, proxy detection, matching,
│                            # occupancy, alert formatting
├── config.yaml              # Thresholds, camera, alerts, security settings
└── .env.example             # Telegram token/chat, QR secret, admin password
```

### Key design points

- **Decision matrix** (`access_policy.py`): 9 rows covering authorized, unpaid, proxy,
  no-face, invalid-token variants, unknown, spoof, and tailgating — each mapped to a
  decision, reason, alert type, and log tag.
- **Match threshold 0.45** (cosine similarity, ArcFace embeddings, 3 stored per user).
- **Signed QR passes**: HMAC-SHA256 over `{user_id, issued_at, expires_at}` with 24 h TTL.
- **Privacy**: consent flag recorded at enrollment; user deletion purges embeddings.

## Known issues / TODO

- `liveness.py` uses InsightFace 5-point landmarks — EAR blink detection needs a
  68/106-point model for production reliability (noted in code).
- `enrollment/enroll_user.py` stores a **random placeholder embedding** — real webcam
  capture of 5 poses is not yet implemented.
- `api/routes_entry.py` accepts raw embeddings from the client; production should accept
  an image/frame and run detection server-side.
- CORS is `allow_origins=['*']` and admin routes have no auth yet — restrict before deploy.
- `config.yaml` ships with placeholder secrets (`CHANGE_THIS...`); real values belong in `.env`.
- `routes_dashboard.py /live` constructs a fresh `CameraManager` per request instead of
  sharing a running instance.
- The React front-end is a static scaffold; wiring it to the API endpoints is the next step
  (see `fablab-face-attendance/README.md` § Frontend Integration).

## Tests

```bash
cd fablab-face-attendance
python -m pytest tests/ -v
```

## License

SRMIST FabLab — internal use.
