# Changelog

All notable changes to AAMS / FacePass FabLab are documented here.
Format follows Keep a Changelog; versioning is SemVer-ish (0.x while prototype).

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
