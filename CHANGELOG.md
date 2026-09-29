# Changelog

All notable changes to AAMS / FacePass FabLab are documented here.
Format follows Keep a Changelog; versioning is SemVer-ish (0.x while prototype).

## [Unreleased]

### Added — Auth
- Console sign-in is now **SRMIST email + password**: `users.password_hash`
  (PBKDF2-SHA256, 200 k iterations, random salt), `POST /api/auth/login`
  verifies server-side, admin password reset at `POST /api/users/{id}/password`
- Enrollment and member creation accept a password; every API response strips
  hashes. Seed script takes `SEED_MEMBER_PASSWORD`
- Live-site backend linking: `VITE_API_URL` / `AAMS_API_URL` repository secret
  flips the Pages build from demo to live

### Added — Console
- Telegram communication portal (`Communicate` page + `POST /api/notify/send`)
- Occupant names on the dashboard; single documented camera handoff step

### Changed — Design
- Warm institutional theme across the console: ivory/paper backgrounds, brass
  accent, teal→brass rules under headers and titles, gradient primary buttons,
  paper sidebar with raised active nav, colour-bar stat cards, redesigned
  tables/inputs/modals; subtle film-grain texture on the background layer

### Fixed
- Institutional header pills truncated their labels ("DIRECTORATE OF
  ENTRE…"): short display names with full names as tooltips, horizontal
  lockup with brass–teal spine, strip scrolls instead of clipping
- Occupancy report `GROUP BY HOUR()` → `strftime('%H', …)` (was HTTP 500)
- Members table showed every member as face-less: `enrolled` was derived
  after the embeddings were blanked
- Valid SRMIST addresses rejected on the live site when Pages answered 404 HTML

### Security
- Admin guard on routes that previously had none: QR pass generation
  (bearer credential), alert approve/acknowledge, occupancy exit/scan
- Sign-in brute-force limit: 10 attempts/min per mail ID, 50/min per IP,
  `429 + Retry-After`, applied before the database query
- Upload validation: `user_id` path-safety allowlist, ≤10 photos per
  enrollment, ≤8 MB base64 and ≤40 MP per decoded frame, ≤12 liveness frames
- Console admin actions prompt for the token on `401` and remember it,
  instead of failing silently

## [0.1.0] — 2026-08-25

First tagged prototype. Full anti-proxy access-control loop working end-to-end.

### Added — Core
- InsightFace pipeline (SCRFD detection → quality gates → ArcFace 512-d embeddings)
- Token+face and face-only entry with §11.2 nine-row decision matrix
- HMAC-signed QR passes, server-side verification
- Blink liveness via 106-pt landmarks; temporal openness analysis
- Enrollment: photo-upload API + interactive webcam CLI (quality-gated)
- Occupancy tracking with timeout logic; Telegram alerts (§15 formats); APScheduler daily report
- SQLite schema per §16 (6 tables) + seed/backup scripts

### Added — Console
- React 19 + Vite console: Three.js scene, Framer Motion, 6 pages
- Enroll Member modal (photo upload → server embeddings → signed QR result)
- Snapshot Entry Test driving the real CV pipeline from the browser
- Offline mock fallback so UI renders without the backend

### Added — Ops & research (audit hardening, Aug 2026)
- GitHub Actions CI: pytest (pinned CI subset) + vite build
- Docker packaging: API image, nginx-served console, compose volumes for DB/photos/models
- Security: constant-time admin token compare, per-IP rate limiting, cheap `/health`,
  `/model-status` without model download, restricted CORS
- Privacy: nightly retention purge (entry logs >90 d, alert images >30 d)
- RQ1 threshold-calibration study tool (`scripts/calibrate_threshold.py`)
- SECURITY.md threat model; internal-use LICENSE

### Known gaps
- Zero real users enrolled; liveness/thresholds need field calibration
- TLS must be terminated at a reverse proxy (see SECURITY.md)
- Admin token in localStorage (roadmap: httpOnly session)
