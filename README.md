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
npm run lint                 # ESLint — must be clean before committing
```

The dev server proxies `/api/*` to `http://localhost:8000`, so run the backend first for live data.
Without a backend the console still renders fully populated sample data ("Demo Data" badge).

### Two build targets

One environment flag separates the on-premises deployment from the public demo:

```bash
npm run build                # lab target  — base '/', API proxy, health probe active
npm run build:pages          # Pages target — base '/AAMS/', no backend, no network calls
```

`VITE_TARGET=pages` compiles out the API health probe and disables every data
hook, so the static site issues **zero** backend requests. Actions that need
the API (enrolment, payment changes, re-keying, snapshot CV, alert acks) report
that they are unavailable instead of failing with an opaque network error.

> **Base path note.** The Pages target hardcodes `/AAMS/` in `vite.config.js`.
> That must be an absolute path — with a relative base, the SPA fallback
> served for a deep link like `/AAMS/alerts` resolves `./assets/x.js` against
> `/AAMS/alerts/` and 404s, blanking the page. If the repository is ever
> renamed, update `PAGES_BASE` to match.

### Run the test-case simulator safely

`Live Monitor` → *Scenario Simulator* exercises the decision pipeline without a
camera. With no backend it falls back to the local simulation constants in
`src/api/client.js`.

### Quick start — Docker (API + console, one command)

```bash
docker compose up --build
# API  -> http://localhost:8000  (/health is orchestrator-safe)
# Web  -> http://localhost:8090  (nginx serves console + proxies /api)
```

Volumes persist the SQLite database, evidence photos and the InsightFace model
cache across rebuilds. TLS termination guidance: see `SECURITY.md`.

### Frontend stack

- React 19 + Vite 8
- `three` + `@react-three/fiber` — particle field / wireframe background (lazy-loaded, DPR-capped)
- `framer-motion` — page transitions, staggered lists, animated counters
- No CSS framework — design tokens in `src/styles/global.css`

### Why the console has an ESLint config

`react/jsx-no-undef` is load-bearing, not decoration. Vite does not resolve JSX
identifiers, so an unimported component — `<IconFace />` used without an
`import` — compiles successfully and only throws at runtime, unmounting the
React tree to a blank page. That exact fault shipped once. `npm run lint` now
fails the build in both CI and the Pages deploy workflow.

The console also carries two error boundaries (`AppBoundary` for the shell,
`BackgroundBoundary` for the decorative WebGL scene) so a single component
fault shows a readable message instead of a black rectangle.

### Public demo

`https://bruce12-glitch.github.io/AAMS/` — static build, placeholder data only.

> **Never put real student data in `src/api/mock.js`.** It is compiled into the
> public JavaScript bundle. Sample records use obviously synthetic identifiers
> (`SAMPLE-0001`) for exactly this reason. Real data belongs in the database
> behind the API.

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

1. **Human-in-the-loop only:** physically run webcam enrollment with volunteers (`python -m enrollment.enroll_user`) or use the Members → ＋ Enroll modal with photos
2. Calibrate blink-liveness thresholds against a real webcam frame burst
3. Threshold calibration study (RQ1) once real users are enrolled
4. Set real secrets in `.env` before any live demo (Telegram, QR secret, admin password)

## Pilot kit

Everything needed to run the one-week field pilot lives in `docs/pilot/`:

| File | Purpose |
|---|---|
| `PILOT_RUNBOOK.md` | Day-by-day plan from approvals to report |
| `CONSENT_FORM_TEMPLATE.md` | Printable §26.2 consent form |
| `GO_LIVE_CHECKLIST.md` | Secrets/TLS/AI sanity gates before opening the door |
| `TEST_REPORT_TEMPLATE.md` | RQ1–RQ6 results tables for the final report |

See also: `SECURITY.md` (threat model + TLS), `CHANGELOG.md`.

Everything else is implemented and verified: image-based entry (server-side detect/embed/match), signed-QR verification, blink **and** head-motion liveness over frame bursts, offline alert retry, retention enforcement, latency metrics (`/api/dashboard/latency`), lost-token re-keying, data-export endpoint, CORS restriction, admin token auth.
