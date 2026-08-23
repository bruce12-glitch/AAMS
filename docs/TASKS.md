# Open tasks — claim one before coding

Agents: **pick a single open P0/P1 row**, write your name/id in `Claimed by`, and do not edit files owned by another open claim.

When you finish: mark Status `done`, add a one-line note, and open/update the PR.

| ID | Priority | Task | Own these files | Do not touch | Status | Claimed by |
|---|---|---|---|---|---|---|
| T01 | P0 | Real enrollment: 5 quality-gated poses → 3 float32 embeddings + consent + token row | `enrollment/*`, `api/routes_users.py` | `app/access_policy.py`, `src/*` | open | |
| T02 | P0 | `POST /api/entry/process` accepts an image/frame; detect server-side | `api/routes_entry.py`, `app/identity.py` | `enrollment/*` | open | |
| T03 | P0 | Mode B uses `QRManager.verify_token` (HMAC + expiry) then user lookup | `app/identity.py`, `app/qr_manager.py` | `src/*` | open | |
| T04 | P0 | On GRANTED → `mark_inside`; on `alert_type` → save + Telegram | `api/routes_entry.py`, `app/alerts.py` | `enrollment/*` | open | |
| T05 | done | `pending` payment is unpaid; noface before grant; tailgate+unpaid stays unpaid | `app/access_policy.py` | — | **done** | arena session |
| T06 | P1 | Blink liveness: 106-pt or FaceMesh over 5s × 5fps | `app/liveness.py` | `app/access_policy.py` | open | |
| T07 | P1 | Camera singleton + 5s no-frame → SYSTEM FAULT + manual register | `app/camera.py`, `api/routes_dashboard.py` | `src/pages/UsersPage.jsx` | open | |
| T08 | P1 | Admin auth on mutating `/api/admin/*` and user delete | `api/routes_admin.py`, `api/routes_users.py`, `app/main.py` | `app/face_engine.py` | open | |
| T09 | P1 | Retention job: logs 90d, alert images 30d, reports 1y | `app/scheduler.py`, new `scripts/purge_retention.py` | `src/*` | open | |
| T10 | P2 | Port pipeline / door screen / charts from `legacy/console-fragment.html` | `src/pages/*`, `src/ui.jsx` | `app/*` | open | |
| T11 | P2 | Door JSON payload on entry response | `api/routes_entry.py`, `src/pages/LivePage.jsx` | `enrollment/*` | open | |

## Rules

1. One ID per agent at a time.
2. If two agents need the same file, the later agent waits or takes a different ID.
3. Do not reseed the database (`--force`) unless the human asked.
4. Keep `python -m pytest tests/ -q` green for files you did not mean to break.
5. Live loop must still work: console scenario → SQLite → Logs/Alerts/Occupants.
