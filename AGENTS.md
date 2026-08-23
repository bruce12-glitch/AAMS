# Agent instructions — FacePass FabLab (AAMS)

Read this file **before any edit**. Then claim a row in [`docs/TASKS.md`](docs/TASKS.md).
You are extending a **working live prototype**. Do not start over.

Spec bible: [`docs/SPEC_DEVELOPMENT_ANALYSIS.md`](docs/SPEC_DEVELOPMENT_ANALYSIS.md)

## First 5 minutes (every agent)

```bash
# from repo root
cd fablab-face-attendance
python -m venv .venv && source .venv/bin/activate   # skip venv if it exists
pip install -r requirements-api.txt
python -m scripts.create_db
python -m scripts.seed_demo_data --if-empty
python -m pytest tests/ -q
```

Frontend (separate terminal):

```bash
npm install
npm run dev          # 0.0.0.0:3000  — proxies /api and /health to :8000
```

Both at once:

```bash
bash scripts/start-live.sh
```

`start-live.sh` **does not wipe the DB**. Use `FORCE_SEED=1 bash scripts/start-live.sh` only when the human wants a reset.

## What must stay green

A reviewer opens the Vite preview and sees **API online**. Clicking a Live scenario writes SQLite and the Logs / Alerts / Occupants panels update.

If you break that loop, fix it before you stop.

```bash
curl -s localhost:8000/health
curl -s localhost:3000/health
cd fablab-face-attendance && python -m pytest tests/ -q
```

Safe tests (no InsightFace, no webcam):

- `test_access_policy.py` `test_embeddings.py` `test_alerts.py` `test_proxy_detection.py` `test_qr_manager.py`

**Never** instantiate `FaceEngine()` in a unit test.

## Product (do not dilute)

Anti-proxy access for SRMIST Fab Lab.

- Mode **B**: signed QR + face 1:1. Other enrolled face = **PROXY**.
- Mode **A**: face-only 1:N.
- Policy: `app/access_policy.py` (§11.2). **RQ3: unpaid silently accepted = 0** (`pending` counts as unpaid).
- Side effects: `entry_logs`, optional Telegram, occupancy, door copy.

## Live servers

| Process | Bind | Port |
|---|---|---|
| FastAPI | `0.0.0.0` | 8000 |
| Vite | `0.0.0.0` | 3000 |

Browser talks **only** to the Vite origin via relative `/api` (`src/api/client.js`). Never `fetch('http://localhost:8000/...')`.
`vite.config.js` already has `allowedHosts: true`. Do not tighten CORS to a desktop origin.

## Honesty board

| Layer | Status |
|---|---|
| React console wired to API | yes |
| Simulate TC01–TC08 persists | yes |
| Policy + pending / noface / unpaid+tailgate | yes (T05 done) |
| Real webcam GRANT | **no** — T01/T02 |
| Liveness blink | **no** — T06 |
| HMAC QR used in `/entry/process` | **no** — T03 |
| Telegram on real process() | **no** — T04 |

Do **not** revert the console to hardcoded John Doe rows.

## Map

```
AGENTS.md                    you are here
docs/TASKS.md                claim list
docs/SPEC_DEVELOPMENT_ANALYSIS.md
src/                         Vite console
  ui.jsx                     Astryx wrappers (use this)
  api/client.js              relative /api only
  pages/LivePage.jsx         simulate + KPIs
fablab-face-attendance/
  app/access_policy.py       §11.2
  app/embeddings.py          float32 cosine — NO insightface
  app/identity.py            Mode A / B
  app/face_engine.py         InsightFace, lazy
  app/liveness.py            stub
  api/routes_*.py
  enrollment/                stub
  requirements-api.txt       live API (no 500MB models)
  requirements.txt           full vision stack
legacy/console-fragment.html UX copy / TC ids
```

`facepass-backend/` and `legacy/` are reference only.

## Multi-agent rules

1. Claim **one** ID in `docs/TASKS.md` before coding.
2. Stay inside that row’s “Own these files”.
3. Keep matching importable **without InsightFace** (`app/embeddings.py`).
4. New entry APIs take an **image**, not a client embedding.
5. Do not load `buffalo_l` in `__init__`.
6. Do not drop/recreate tables. Additive schema only.
7. Secrets stay in `.env`. Never commit tokens.
8. Do not force-push `main`. Do not `--force` seed unless asked.
9. Policy change ⇒ update `tests/test_access_policy.py`.

## Conventions

- Python 3.10+, FastAPI, sqlite3, no ORM.
- Embeddings: **float32 × 512** via `app/embeddings.py`.
- Tags: `authorized | proxy | unpaid | unknown | spoof | tailgate | noface`.
- Decisions: `GRANTED | DENIED`. Threshold **0.45**.
- React: import UI from `src/ui.jsx` (wraps Astryx). There is **no** `Box` or `Table.Header` on `@astryxdesign/core` — do not import those from the kit.

## Done for a slice

1. Vite preview shows API online.
2. Your route works from `/docs`.
3. `pytest tests/ -q` still passes.
4. `docs/TASKS.md` row marked `done`.
