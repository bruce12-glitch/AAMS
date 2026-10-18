# AAMS showcase handoff

Repository: https://github.com/bruce12-glitch/AAMS
Initial reviewed base: `main` at `f0e2ce4503fa7c6c476118b925e616e65d6e28cb`.
Feature release: PR #8 merged at `9a0a6aed1547a8a49292680ccd3c8ecb58739653`.

## Current local prototype work — 18 October 2026

Oracle/public deployment is paused at the user's request. Continuous laptop webcam attendance is already in main through PR #11. The local-prototype update adds an administrator Dashboard setup panel, nonblocking face-model initialization with retry, personal Telegram chat support with one-use pairing, and a Windows launcher that reuses saved configuration and opens the website. It preserves the separate administrator/shared credentials and exact SRMIST domain restriction.

Local verification of this update: 145 backend tests pass; the separate opt-in real-model test also passes with actual `buffalo_l` models and the public NASA astronaut fixture. That test covers normal photo quality checks, enrollment, face-only identity match, attendance/occupancy, duplicate suppression, checkout/re-entry, expired-payment denial, empty frames and notification queuing. It uses isolated data and disabled real Telegram delivery. Still-image testing explicitly bypasses blink liveness. Frontend lint, production build and static Pages build pass. CI additionally exercises the browser setup/pairing/webcam flows, Windows repeat startup and real-model inference inside the full Docker image; consult the update's PR for its final results.

The Telegram screenshot supplied by the user shows a successful earlier test/report, followed by an `Attendance` message with no reply. The implementation sends AAMS notifications; it does not implement conversational attendance commands. Personal-chat pairing now lets the administrator select the correct recipient through a fresh private `/start` link without manually retrieving a chat ID. Pairing never sends to an arbitrary correspondent or modifies an existing webhook. The live bot token must be entered privately in the local application; a real current delivery has not been claimed.

Laptop acceptance sequence: launch Docker Desktop and Start-AAMS.cmd, sign in, initialize the model on Dashboard, connect Telegram in Communicate and confirm a test arrives, add a consenting member with active payment and enroll webcam photos, then start Live Monitor webcam attendance. Confirm the member's name, attendance log, occupancy and one Telegram entry message. Check out the member before demonstrating re-entry. The remaining physical tests are laptop camera permission/device access, normal live blink detection, recognition in the room's lighting and actual phone receipt.

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

Telegram now supports personal chats and groups. Current credentials, destination pairing and actual receipt still need to be completed privately in the laptop application. No real current delivery has been claimed. The other features do not require a configured bot.

Public hosting is paused pending the local prototype demonstration. The existing Oracle package has not been deployed and no paid resource or public domain has been provisioned. A later deployment needs persistent storage and an always-running process for scheduled reports. Physical webcam access and liveness/recognition calibration need the lab hardware and consented volunteers. Snapshot liveness bypass is a prototype feature. Review pretrained model licensing before commercial use.

New timestamps are written as UTC and displayed/reported in IST. Historical naive timestamps are treated as UTC; assess any existing Windows-local database before importing real historical records. No historical user data was rewritten.
