# AAMS — FacePass FabLab

**Smart Anti-Proxy Facial Access and Attendance Management System** for the SRMIST Fab Lab.

Two components:

| Directory | What it is |
|---|---|
| `fablab-face-attendance/` | FastAPI backend — InsightFace (SCRFD + ArcFace) recognition, SQLite, HMAC-signed QR tokens, Telegram alerts, APScheduler daily reports, pytest suite |
| `src/` + `index.html` | React 19 console (Vite) — Three.js animated scene, Framer Motion transitions, live-polling dashboard with offline fallback |

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

The dev server proxies `/api/*` to `http://localhost:8000`, so run the backend first for live data.
Without a backend the console still renders fully populated sample data ("Demo Data" badge).

### Frontend stack

- React 19 + Vite 8
- `three` + `@react-three/fiber` — particle field / wireframe background (lazy-loaded, DPR-capped)
- `framer-motion` — page transitions, staggered lists, animated counters
- No CSS framework — design tokens in `src/styles/global.css`

### Console pages

| Page | Purpose |
|---|---|
| Dashboard | KPIs, recent activity, occupants inside, latest alerts |
| Live Monitor | Camera/pipeline status + entry-scenario simulator (`POST /api/entry/simulate`) |
| Entry Logs | Filterable trail of every access attempt |
| Alerts | Security alerts by severity with acknowledge action |
| Members | Enrolled users with payment/consent status |
| Reports | Daily summary, security events, retention policy |

## Backend architecture

```
fablab-face-attendance/
├── app/                     # Core modules
│   ├── main.py              # FastAPI app + CORS + startup wiring
│   ├── config.py            # config.yaml + .env loader
│   ├── database.py          # SQLite schema (6 tables) + helpers
│   ├── face_engine.py       # InsightFace SCRFD + ArcFace, quality checks, 1:N search
│   ├── liveness.py          # Blink detection via Eye Aspect Ratio (EAR)
│   ├── identity.py          # Token+face (1:1) and face-only (1:N) verification
│   ├── access_policy.py     # §11.2 decision matrix (9 rows)
│   ├── occupancy.py         # Inside/outside tracking with timeout
│   ├── alerts.py            # Telegram bot integration
│   ├── qr_manager.py        # HMAC-signed QR passes
│   └── scheduler.py         # APScheduler — 20:00 daily report
├── api/                     # Route modules (entry, users, alerts, occupants, reports, dashboard, admin)
├── enrollment/              # CLI enrollment (capture → quality check → embeddings)
├── scripts/                 # create_db, seed_demo_data, generate_qr, backup_db
└── tests/                   # pytest suite
```

## Testing

```bash
cd fablab-face-attendance
python -m pytest tests/ -v
```

## Known gaps / next work

1. Wire real webcam capture into `enrollment/enroll_user.py` (currently stores placeholder embedding)
2. `/api/entry` should accept images and detect server-side instead of receiving raw embeddings
3. Liveness blink detection needs a 68/106-point landmark model
4. Restrict CORS + add admin auth before any real deployment

See `HANDOFF.md` for environment notes.
