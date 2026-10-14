# AAMS showcase handoff

Repository: https://github.com/bruce12-glitch/AAMS
Reviewed base: `main` at `f0e2ce4503fa7c6c476118b925e616e65d6e28cb`.

## Delivered source

Student add/edit and separate photo enrollment now work together. Profiles include contact and academic fields, account status and payment expiry. Duplicate emails and invalid profile fields are rejected. Student and entry CSV exports, QR download/re-key, manual checkout, daily/weekly/occupancy summaries, incident acknowledgment and Telegram communication remain behind authenticated access.

The administrator impersonation defect is fixed: a shared member credential cannot claim the administrator address. Production startup fails closed without valid signing/authentication settings. Production entry processing requires a signed session and rejects caller-supplied raw embeddings. Disabled accounts lose read access. The exact `@srmist.edu.in` domain restriction remains in frontend and backend; a shared-password gate does not prove mailbox ownership.

The review also fixed signed QR lookup, expiry enforcement, unsafe malformed-QR handling, pose-axis ordering, occupancy records missing their status/duration, SQLite timestamp comparisons, IST reporting/display, misleading static KPI trends, liveness enforcement for multiple-face requests, overlapping polling, scheduler lifecycle, Telegram retry behavior and SQLite WAL backups. Student announcements are separated from security incident counts. Live views never replace failed requests with fictitious sample attendance.

Telegram setup is available in Communicate with administrator-only credential saving, destination verification, test/announcement/report sends and delivery history. Credentials persist on the private database volume with restrictive file permissions and are excluded from Git and API responses. Validation errors and transport logs do not echo credentials. Student creation/enrollment, granted entries, security events and daily IST summaries use a durable delivery queue. Failed sends retry every five minutes; queue claims prevent concurrent duplicate sends. Daily summaries have a date-based deduplication key. Ambiguous network failures can still cause redelivery because Telegram provides no application idempotency key. Pending messages expire after 24 hours.

## Verification completed locally

- 109 backend tests pass, including student CRUD/roles, private Telegram settings, notification retry/claim handling, real Telegram SDK response parsing with a controlled transport, timestamp boundaries, WAL backup restore, signed-pass admission/revocation, payment expiry, disabled accounts, capture notifications, pose axes and liveness policy.
- Frontend lint and both production/static build targets pass.
- Chromium browser checks pass for domain rejection, administrator login, student add/edit, enrollment/QR/CSV, snapshot entry, occupancy checkout, notification queuing, all seven pages, mobile layout and member permissions. No browser runtime exceptions were observed. CI browser tests control only the model-inference boundary and do not send to a real Telegram group.
- The full Python dependency set installs and the actual InsightFace `buffalo_l` model initializes. A qualified public model fixture passes real-image enrollment, signed-QR face entry, occupancy/log persistence, expired-payment denial and old-pass denial after re-key. This is functional validation, not a biometric accuracy or anti-spoofing study.
- `git diff --check` passes. The high-severity source-map-js advisory was fixed by updating the locked dependency to 1.2.2; npm audit now reports zero vulnerabilities across all dependencies.

Local checks used Node 24 and Python 3.12; Dockerfiles and CI use matching major versions. Docker is unavailable in this workspace. A GitHub Actions Docker smoke job is included to build/start nginx + API, verify login and prove student persistence across restart. Its result must be checked separately from local tests.

## Repository review and boundaries

At the initial review, nine remote branches were present and no PRs were open. All branches are preserved. `windows-edge-webcam` has the same tree as the reviewed main despite different ancestry; `fixed-showcase-auth` carries older behavior and should not be merged wholesale. Arena branches hold earlier generations; two earlier Codex branches are already in main ancestry.

The completion changes are intended for a separate GitHub branch/PR. Main is not merged or rewritten. The existing published website is not updated by a branch push. Pages publication is manual in the proposed workflow. No production database, Telegram group, hosting settings or public deployment has been changed.

## Remaining external setup

The actual Telegram bot token and group ID are unavailable in this workspace. No real group delivery has been claimed. An administrator must configure the authorized group in Communicate, verify its title and send the test; a successful delivery record is the final evidence of posting permissions and connectivity.

Public hosting still requires approval and a selected host/hostname. Run the private Docker stack and verify TLS/origin configuration before enabling the tunnel/TLS profiles or dispatching Pages publication. The API needs persistent storage and an always-running process for scheduled reports. Physical webcam access and liveness/recognition calibration need the lab hardware and consented volunteers. Snapshot liveness bypass is a prototype feature. Review pretrained model licensing before commercial use.

New timestamps are written as UTC and displayed/reported in IST. Historical naive timestamps are treated as UTC; assess any existing Windows-local database before importing real historical records. No historical user data was rewritten.
