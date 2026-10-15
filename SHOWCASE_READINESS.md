# AAMS showcase handoff

Repository: https://github.com/bruce12-glitch/AAMS
Initial reviewed base: `main` at `f0e2ce4503fa7c6c476118b925e616e65d6e28cb`.
Feature release: PR #8 merged at `9a0a6aed1547a8a49292680ccd3c8ecb58739653`.

## Delivered source

Student add/edit and separate photo enrollment now work together. Profiles include contact and academic fields, account status and payment expiry. Duplicate emails and invalid profile fields are rejected. Student and entry CSV exports, QR download/re-key, manual checkout, daily/weekly/occupancy summaries, incident acknowledgment and Telegram communication remain behind authenticated access.

The administrator impersonation defect is fixed: a shared member credential cannot claim the administrator address. Production startup fails closed without valid signing/authentication settings. Production entry processing requires a signed session and rejects caller-supplied raw embeddings. Disabled accounts lose read access. The exact `@srmist.edu.in` domain restriction remains in frontend and backend; a shared-password gate does not prove mailbox ownership.

The review also fixed signed QR lookup, expiry enforcement, unsafe malformed-QR handling, pose-axis ordering, occupancy records missing their status/duration, SQLite timestamp comparisons, IST reporting/display, misleading static KPI trends, liveness enforcement for multiple-face requests, overlapping polling, scheduler lifecycle, Telegram retry behavior and SQLite WAL backups. Student announcements are separated from security incident counts. Live views never replace failed requests with fictitious sample attendance.

Telegram setup is available in Communicate with administrator-only credential saving, destination verification, test/announcement/report sends and delivery history. Credentials persist on the private database volume with restrictive file permissions and are excluded from Git and API responses. Validation errors and transport logs do not echo credentials. Student creation/enrollment, granted entries, security events and daily IST summaries use a durable delivery queue. Failed sends retry every five minutes; queue claims prevent concurrent duplicate sends. Daily summaries have a date-based deduplication key. Ambiguous network failures can still cause redelivery because Telegram provides no application idempotency key. Pending messages expire after 24 hours.

## Verification completed locally

- 125 backend tests pass, including student CRUD/roles, private Telegram settings, notification retry/claim handling, real Telegram SDK response parsing with a controlled transport, timestamp boundaries, WAL backup restore, signed-pass admission/revocation, payment expiry, disabled accounts, capture notifications, pose axes, liveness policy, static-file boundaries and persistent hosted-runtime configuration.
- Frontend lint and both production/static build targets pass.
- Chromium browser checks pass for domain rejection, administrator login, student add/edit, enrollment/QR/CSV, snapshot entry, occupancy checkout, notification queuing, all seven pages, mobile layout and member permissions. No browser runtime exceptions were observed. CI browser tests control only the model-inference boundary and do not send to a real Telegram group.
- The full Python dependency set installs and the actual InsightFace `buffalo_l` model initializes. A qualified public model fixture passes real-image enrollment, signed-QR face entry, occupancy/log persistence, expired-payment denial and old-pass denial after re-key. This is functional validation, not a biometric accuracy or anti-spoofing study.
- `git diff --check` passes. The high-severity source-map-js advisory was fixed by updating the locked dependency to 1.2.2; npm audit now reports zero vulnerabilities across all dependencies.

Local checks used Node 24 and Python 3.12; Dockerfiles and CI use matching major versions. Docker is unavailable in this workspace. All four GitHub Actions checks for PR #8 passed, including the real Docker build/start, nginx proxy and student persistence across restart. The hosted-image update adds a fifth check that destroys and recreates the complete website/API container and verifies retained student records, photos and session keys on its volume; check its run separately from the earlier release.

## Repository review and boundaries

At the initial review, nine remote branches were present and no PRs were open. All branches are preserved. `windows-edge-webcam` has the same tree as the reviewed main despite different ancestry; `fixed-showcase-auth` carries older behavior and should not be merged wholesale. Arena branches hold earlier generations; two earlier Codex branches are already in main ancestry.

The feature completion changes were reviewed and merged through PR #8 following the user's go-ahead. Existing branches were preserved. Pages publication remains manual. No production database, Telegram group, hosting account settings or public deployment has been changed.

`Dockerfile.showcase` now packages the website and API on one port. The launcher keeps database/photos/model cache and generated signing keys on one persistent directory, enforces production mode, refuses unsafe storage paths and preserves pre-existing photos. Static hosting exposes only the built website. The API-only and local Compose targets retain their existing behavior. See [deploy/HOSTING.md](deploy/HOSTING.md).

## Remaining external setup

Telegram bot/group setup is deferred at the user's request. No real group delivery has been claimed. The other features do not require a configured bot.

Public hosting is authorized but still needs an Oracle Cloud Always Free account and private administrator/member authentication variables. The deployment package now targets one always-free Oracle A1 VM with a persistent volume, Caddy HTTPS and a free DuckDNS hostname; no paid resource or public domain has been provisioned. The API needs persistent storage and an always-running process for scheduled reports. Physical webcam access and liveness/recognition calibration need the lab hardware and consented volunteers. Snapshot liveness bypass is a prototype feature. Review pretrained model licensing before commercial use.

New timestamps are written as UTC and displayed/reported in IST. Historical naive timestamps are treated as UTC; assess any existing Windows-local database before importing real historical records. No historical user data was rewritten.
