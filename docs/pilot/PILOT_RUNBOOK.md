# Pilot Runbook — FacePass FabLab (One-Week Plan)

Goal: take v0.1.0 from "works" to "validated" with real users, per spec §37.

## Day 0 — Approvals & logistics (human)
- [ ] Written permission from Fab Lab In-charge (+ HOD if needed)
- [ ] Camera placement decided (eye-level+, 1–1.5 m, no backlight — §31.1)
- [ ] 10–20 volunteers recruited; consent forms printed (see template)

## Day 1 — Environment go-live
```bash
# On the entrance machine (or Docker):
cd fablab-face-attendance
python -m venv venv && venv\Scripts\activate      # Linux: source venv/bin/activate
pip install -r requirements.txt
copy .env.example .env                             # then fill REAL values:
#   API_ADMIN_PASSWORD=  QR_SECRET_KEY=  TELEGRAM_BOT_TOKEN=  TELEGRAM_CHAT_ID=
python -m scripts.create_db
python run.py                                      # http://localhost:8000/health must say ok
```
Frontend: `npm ci && npm run dev` (or `docker compose up`).
Signage posted at the door (§31.3 wording is in the spec).

## Day 2 — Enrollment day (human-heavy)
- [ ] Collect signed consent forms first
- [ ] Enroll each volunteer via Members → ＋ Enroll (3–5 photos each:
      front + slight angles; good lighting)
- [ ] Verify each person's QR pass renders; hand out / store passes
- [ ] Spot-check recognition: Live Monitor → Snapshot Entry Test per user

## Day 3 — Calibration (agentic-assisted)
```bash
python -m scripts.calibrate_threshold --targets 0.01 0.001
```
- [ ] Record genuine/impostor means, d′, recommended threshold
- [ ] Update `config.yaml → face.match_threshold`; restart API
- [ ] Check GET `/api/dashboard/latency` → p95 under 3000 ms?

## Day 4–5 — Live operation
- [ ] System runs the full working day unattended
- [ ] Telegram group receives alerts; verify one of each type by controlled tests:
      proxy (friend's token), unpaid (expired member), unknown (outsider face)
- [ ] Watch Logs page for false rejects; retry logic behaving (§30.1)

## Day 6 — Data collection for the report
- Export: entries, alerts, occupancy, latency metrics, calibration numbers
- Fill `docs/pilot/TEST_REPORT_TEMPLATE.md`

## Day 7 — Review & decision
- Meet the In-charge with the test report
- Decide: extend pilot / fix list / Tier-2 hardening

## Rollback / fallback at any point
Manual register at the door. Kill switch: stop uvicorn/container;
data stays on volumes/disk.
