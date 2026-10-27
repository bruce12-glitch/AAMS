# AAMS — FacePass Fab Lab

A React/Vite console and FastAPI service for the SRMIST Fab Lab. The prototype includes student profiles, face enrollment, signed QR passes, laptop webcam attendance, occupancy, security alerts and reporting. Work currently focuses on the local prototype; Oracle hosting is paused.

**Demonstrating soon?** Follow [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md) for the no-terminal setup, five-minute presentation, duplicate test, Telegram checks and quick recovery steps. Demo data checks run in isolated tests, not in your real member database.

## Showcase features

- SRMIST-only sign-in. Members use a privately configured shared access credential; the configured administrator uses a different private administrator credential. The shared credential does not grant administrator privileges.
- Add and edit student ID, full name, SRMIST email, phone, department, year, section, member type, payment status/expiry and account status. Student creation does not require biometric enrollment.
- Enroll face photos or capture webcam photos after consent. The server validates images, runs InsightFace, saves embeddings, and issues a signed QR pass. Display/download/re-key passes; old passes are rejected after re-keying.
- Process signed QR + face or face-only snapshots. Expired payments are denied. Granted entries update occupancy and logs; administrators can check students out.
- Filter the latest 500 entry logs and export CSV. Export student records. View daily, weekly, security and occupancy reports. Times display in IST.
- Configure a personal Telegram chat or group privately in **Communicate**, verify its identity, send a test or announcement, and inspect delivery history. Personal-chat pairing uses a private, one-use `/start` link that expires after five minutes. Announcements, student additions/enrollments, granted entries and security alerts use a persistent queue. Failed deliveries remain queued and retry automatically. The daily summary runs at the configured IST time; default 20:00. Background camera notifications are queued for the next retry cycle.
- Clear loading/error states. Live pages retain the last real response on outages instead of substituting sample students or attendance.

## Private local launch

Requires Docker Desktop or a Docker engine. The supported images use Node 24 and Python 3.12. Configuration and data stay out of Git.

On Windows, start Docker Desktop and double-click **Start-AAMS.cmd**. First launch asks for the private sign-in settings; subsequent launches reuse them and preserve QR/session keys. The website opens automatically. This uses the installed PowerShell policy; a policy that blocks local scripts must be resolved by the laptop owner. The equivalent PowerShell command is:

```powershell
.\deploy\showcase-windows.ps1 -SkipTelegram
```

Other hosts:

```bash
python deploy/configure_showcase.py --admin-email your.name@srmist.edu.in
docker compose up --build -d
```

Open http://localhost:8090 and sign in with the configured administrator account. The web and API host ports bind to localhost. Telegram credentials can be entered on the Communicate page and are stored in a private file on the database volume. They are never returned by the API or embedded in browser assets.

The shared access credential remains a server-side setting, `AAMS_ACCESS_PASSWORD`. Use the requested value privately; do not commit it. `API_ADMIN_PASSWORD` must be different. Configuration helpers generate separate random QR/session signing secrets.

After sign-in, use **Dashboard → Prototype setup → Initialize face model**. The panel separately reports the database, model, enrolled members and Telegram configuration. The first model download needs internet and several minutes; later starts reuse the saved cache. Initialization runs in a worker so the console remains responsive, and failed initialization can be retried from the panel. API health alone does not indicate that recognition is ready.

For Telegram, privately enter the current bot token in **Communicate**, leave Chat ID blank for personal pairing, enable delivery and save. Click **Connect my Telegram**, open the generated bot link and press **Start**, then return and click **Connect this chat** within five minutes. Click **Verify chat** and **Send test message**, and check the message actually arrives on your phone. Pairing preserves existing webhooks and never selects an arbitrary bot correspondent; bots already used by another polling application should use manual Chat ID entry or a dedicated bot. For a group, add the bot and enter the negative group ID or public group username. The bot username/link itself is not a chat ID. This bot sends AAMS notifications; typing `Attendance` in Telegram does not start a webcam or request a report. Use the website's **Send daily report now** button for a report.

Browser webcam capture needs HTTPS or localhost and camera permission. Unattended hardware capture is opt-in through `capture.enabled` in the backend configuration and requires the camera host; it is not needed for the laptop browser prototype.

## Development and checks

### Laptop webcam attendance

In **Members**, add a student, set payment status to **active**, and enroll clear face photos after obtaining consent. In **Live Monitor → Laptop Webcam Attendance**, click **Start webcam attendance** and allow camera access. Show one enrolled person at a time. The browser sends a short image burst to the signed-in backend, which checks identity and policy, records granted attendance/occupancy, and queues the Telegram entry notification. Configure and test the connected chat in **Communicate** before expecting delivery.

Blink verification is required by default for this mode; look at the camera and blink naturally. The explicit prototype checkbox skips that check and may accept a photograph. Webcam scanning needs HTTPS or localhost and a running backend; static Pages alone cannot perform recognition. Requests run sequentially with a ten-second gap. Empty frames do not create attendance or Telegram alerts. Recognized students already inside do not get another attendance record or entry notification until checked out; repeated denials are throttled for sixty seconds. Stop, navigation away, or hiding the page releases the camera and stops further captures. An entry request already accepted by the backend may finish after stopping.

Images used for a new decision follow the backend evidence retention settings. Camera access never starts automatically on page load. This is an attended prototype, not a validated anti-spoofing or production door-control system.

```bash
npm ci
pip install -r fablab-face-attendance/requirements.txt
npm run lint
npm run build
cd fablab-face-attendance
python -m pytest tests/ -q
```

For browser integration checks, from the repository root:

```bash
npx playwright install chromium
npm run test:e2e
```

The browser test starts disposable local servers and an isolated database. Neural inference and Telegram transport are controlled for CI; production source continues to use the real model and SDK. It covers setup, private-chat pairing, the webcam loop and attendance. Set `AAMS_TEST_PYTHON` if the backend packages live in a separate Python environment. Tests must run in the same network namespace as their local servers.

An opt-in real-model check uses the bundled public NASA astronaut image from scikit-image, the normal quality thresholds, isolated records/photos and a disabled Telegram transport. From `fablab-face-attendance`, with full requirements installed:

```bash
AAMS_REAL_VISION_TEST=1 python -m pytest tests/test_real_vision.py -q -s
```

It verifies actual image enrollment, recognition, attendance/occupancy, notification queuing, repeat-scan suppression, checkout/re-entry and expired-payment denial. A second test downloads Matplotlib's versioned public-domain Grace Hopper portrait, checks two identities and photo variants, rejects the unenrolled identity and denies a static burst when liveness is requested. Still-image identity checks explicitly bypass liveness. These are regression fixtures, not an accuracy benchmark. Physical webcam, live blink behavior and actual Telegram receipt must still be demonstrated on the laptop.

For troubleshooting, **Live Monitor → Photo & camera check → Check photo — no attendance** runs the real recognition pipeline without saving attendance, evidence or notifications. Results show why comparison stopped or the measured score versus threshold. See [DEMO_RUNBOOK.md](DEMO_RUNBOOK.md).

CI includes backend tests, frontend lint/build, browser flows, Windows repeat-launch checks, a disposable Docker startup/persistence/proxy check with real-model validation, and a complete hosted-container check. Deployment smoke tests are restricted to disposable GitHub Actions runners and never configure a real Telegram destination.

## Database and hosting

SQLite WAL and additive migrations are retained for the single-host showcase. The database, evidence/enrollment photos and model cache use persistent Docker volumes. Backups use SQLite's online backup API, including committed WAL data. Run one API process to keep the camera, scheduler and in-memory rate limits coherent.

Public hosting is paused while the local prototype is validated. The existing [deploy/HOSTING.md](deploy/HOSTING.md), `docker-compose.oracle.yml` and `Dockerfile.showcase` remain available for a later deployment with persistent storage and HTTPS.

GitHub Pages serves only static files. Secure sign-in and persistent features require a backend; a Pages-only build intentionally cannot sign in. The Pages workflow requires a manual dispatch, so publishing source changes does not automatically publish a site.

The student-management and continuous-webcam features are merged into `main` through PRs #8 and #11. All existing branches are preserved. See [SHOWCASE_READINESS.md](SHOWCASE_READINESS.md) for verified results and remaining laptop checks.
