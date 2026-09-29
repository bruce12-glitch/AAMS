# AAMS — FacePass FabLab

[![Live Demo](https://img.shields.io/badge/🌐_Live_Demo-Visit_the_Site-14b8a6?style=for-the-badge)](https://bruce12-glitch.github.io/AAMS/)
[![CI](https://github.com/bruce12-glitch/AAMS/actions/workflows/ci.yml/badge.svg)](https://github.com/bruce12-glitch/AAMS/actions/workflows/ci.yml)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](fablab-face-attendance/)
[![React 19](https://img.shields.io/badge/React-19-61DAFB?style=flat-square&logo=react&logoColor=black)](src/)

> ### 🌐 Visit the live website: [bruce12-glitch.github.io/AAMS](https://bruce12-glitch.github.io/AAMS/)
> Interactive demo of the console (sample data, no backend needed).
> Sign in with any `@srmist.edu.in` address + any 6-character password.

**Smart Anti-Proxy Facial Access and Attendance Management System** for the
SRMIST Fab Lab — face recognition at the door, live occupancy, security
alerts over Telegram, and a calm, classic console designed for daily
operations.

| Component | Description |
|---|---|
| `fablab-face-attendance/` | FastAPI backend — InsightFace recognition, SQLite, signed QR passes, Telegram alerts, scheduled reports, pytest suite |
| `src/` + `index.html` | React 19 console (Vite) — subtle classic 3D backdrop, motion-respecting transitions, live data with offline demo fallback |

## ✨ Features

- **Face-based entry** — server-side detect → quality gate → ArcFace match → policy decision, with token+face and face-only modes
- **Anti-proxy & liveness** — blink (EAR) and head-motion checks over frame bursts, spoof/tailgate/unknown detection
- **SRMIST-only access** — console sign-in and member enrollment accept only `@srmist.edu.in` mail IDs; mutating APIs additionally require an admin token
- **Live occupancy** — who is inside right now, with names, entry times and automatic timeout exits
- **Telegram communication portal** — send announcements to the lab group from the console, with delivery status and a full audit trail
- **Reports & audit** — daily/weekly/proxy/unpaid/occupancy reports, filterable entry logs, severity-graded alerts, retention enforcement
- **Signed QR passes** — HMAC-signed 24 h passes with lost-token revoke-and-reissue

## 🖥️ Console pages

| Page | Purpose |
|---|---|
| Dashboard | KPIs, recent activity, occupants inside (with names), latest alerts |
| Live Monitor | Camera/pipeline status, snapshot entry test, scenario simulator |
| Entry Logs | Filterable trail of every access attempt |
| Alerts | Security alerts by severity, with acknowledge action |
| Members | Enrolled users — payment, consent and QR-pass management |
| Reports | Daily summary, security events, occupancy, retention policy |
| Communicate | Telegram announcements with channel status and delivery outcome |

## 🚀 Quick start

### Backend (FastAPI)

```bash
cd fablab-face-attendance
python -m venv venv
venv\Scripts\activate        # Windows (or: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env       # then set real secrets (see below)
python -m scripts.create_db
python -m scripts.seed_demo_data   # optional demo data
python run.py                # API on http://localhost:8000 (docs at /docs)
```

> First run downloads the InsightFace `buffalo_l` models (~500 MB) into
> `models/insightface/`. The CV engine loads lazily — the API boots and
> serves immediately; image endpoints warm it up on first use.

### Frontend (React console)

```bash
npm install
npm run dev                  # dev server on http://localhost:3000
npm run lint                 # ESLint — must be clean before committing
```

The dev server proxies `/api/*` to `http://localhost:8000`, so run the
backend first for live data. Without a backend the console renders
populated sample data (badged "Demo Data").

### Docker (API + console, one command)

```bash
docker compose up --build
# API -> http://localhost:8000   (/health is orchestrator-safe)
# Web -> http://localhost:8090   (nginx serves the console + proxies /api)
```

Volumes persist the SQLite database, evidence photos and the model cache
across rebuilds. TLS guidance: see [`SECURITY.md`](SECURITY.md).

### Build targets

```bash
npm run build                # lab target   — base '/', live API + health probe
npm run build:pages          # Pages target — base '/AAMS/', static demo, zero backend calls
```

> The Pages target hardcodes `/AAMS/` in `vite.config.js` (must stay an
> absolute path for deep links). If the repository is renamed, update
> `PAGES_BASE` to match.

## 🔗 Linking the live site to the backend

The Pages build is a self-contained demo by default. To run it against
the real backend (sign-in verification, enrollment, live data):

1. Host the API (lab machine, `docker compose`, or any HTTPS host) and
   allow the Pages origin in CORS (`ALLOWED_ORIGINS` includes
   `https://bruce12-glitch.github.io`)
2. Repository **Settings → Secrets and variables → Actions** → add
   `AAMS_API_URL` = `https://<your-api-host>` (no trailing slash)
3. Push to `main` — the workflow injects it as `VITE_API_URL` and the
   site switches from demo mode to live mode

Leave the secret unset (or delete it) to return to the zero-backend demo.

## 🔐 Authentication

- Console sign-in, member enrollment and `POST /api/auth/login` accept
  **only `@srmist.edu.in`** addresses — every other domain is rejected
  with a clear message, on both frontend and backend.
- Sign-in is **email + password** (minimum 6 characters). The server
  stores only a PBKDF2-SHA256 hash (200 000 iterations, random salt) in
  `users.password_hash`; plain-text passwords are never logged, returned
  or persisted. Wrong passwords are rejected by the API, never by a
  frontend shortcut.
- Without a backend (the public Pages demo) the same rule is enforced
  locally: SRMIST address plus any 6-character password opens the
  console; real 400/403 verdicts from an API are always honoured.
- Mutating API routes require the `X-Admin-Token` header matching
  `API_ADMIN_PASSWORD` in `fablab-face-attendance/.env`. With no password
  configured the API runs in loudly-logged dev-open mode.

## 📷 Connecting the camera

The only step needed to go live on the lab host:

1. Set `camera.source` (USB index `0`, or an RTSP URL) and
   `capture.enabled: true` in `fablab-face-attendance/config.yaml`
2. Restart the API (`python run.py`)

Recognized members are then recorded automatically with their names, and
the dashboard occupancy updates in real time. The Live Monitor page shows
this guidance while the camera is offline; the snapshot test and scenario
simulator work without any camera.

## 💬 Telegram setup

1. Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in
   `fablab-face-attendance/.env`, and `alerts.telegram_enabled: true`
   in `config.yaml`
2. Restart the API — the Communicate page reports the channel as ready

Until then, announcements are stored in the alerts table with the reason
shown, so nothing is ever silently dropped. A daily summary is delivered
at 20:00 via the scheduler.

## 🧱 Backend architecture

```
fablab-face-attendance/
├── app/                     # Core modules
│   ├── main.py              # FastAPI app + CORS + startup wiring
│   ├── auth.py              # SRMIST-only email rule (single source of truth)
│   ├── config.py            # config.yaml + .env loader
│   ├── database.py          # SQLite schema + helpers
│   ├── face_engine.py       # InsightFace SCRFD + ArcFace, quality checks
│   ├── liveness.py          # Blink (EAR) + head-motion detection
│   ├── identity.py          # Token+face (1:1) and face-only (1:N) matching
│   ├── access_policy.py     # Decision matrix
│   ├── occupancy.py         # Inside/outside tracking with timeout
│   ├── alerts.py            # Telegram bot + announcements
│   ├── qr_manager.py        # HMAC-signed QR passes
│   ├── capture_service.py   # Background camera loop (owns the device)
│   └── scheduler.py         # APScheduler — 20:00 daily report
├── api/                     # Routes: entry, users, alerts, occupants,
│                            # reports, dashboard, admin, auth, notify
├── enrollment/              # CLI enrollment (capture → quality → embeddings)
├── scripts/                 # create_db, seed_demo_data, generate_qr, backup_db
└── tests/                   # pytest suite (47 tests)
```

Frontend: React 19 + Vite 8 · `three` + `@react-three/fiber` (lazy,
DPR-capped classic backdrop) · `framer-motion` (reduced-motion aware) ·
no CSS framework — design tokens in `src/styles/global.css`.

## ✅ Testing

```bash
cd fablab-face-attendance
python -m pytest tests/ -v
```

CI runs the backend suite plus frontend lint and both build targets on
every push to `main`; the Pages demo redeploys automatically.

## 🧪 Field pilot

Everything for the one-week pilot lives in [`docs/pilot/`](docs/pilot/):

| File | Purpose |
|---|---|
| `PILOT_RUNBOOK.md` | Day-by-day plan from approvals to report |
| `CONSENT_FORM_TEMPLATE.md` | Printable biometric consent form |
| `GO_LIVE_CHECKLIST.md` | Secrets / TLS / AI sanity gates before opening the door |
| `TEST_REPORT_TEMPLATE.md` | Results tables for the final report |

See also [`SECURITY.md`](SECURITY.md) (threat model + TLS) and
[`CHANGELOG.md`](CHANGELOG.md).

> ⚠️ **Privacy:** never put real student data in `src/api/mock.js` — it
> ships in the public JavaScript bundle. Samples use synthetic IDs
> (`SAMPLE-0001`). Real data belongs in the database behind the API.

## 📄 License

See [`LICENSE`](LICENSE).
