# AAMS — FacePass Fab Lab

A React/Vite console and FastAPI service for the SRMIST Fab Lab. The showcase build includes student profiles, face enrollment, signed QR passes, entry checks, occupancy, security alerts and reporting. Telegram integration is implemented; live bot/group setup is deferred.

## Showcase features

- SRMIST-only sign-in. Members use a privately configured shared access credential; the configured administrator uses a different private administrator credential. The shared credential does not grant administrator privileges.
- Add and edit student ID, full name, SRMIST email, phone, department, year, section, member type, payment status/expiry and account status. Student creation does not require biometric enrollment.
- Enroll face photos or capture webcam photos after consent. The server validates images, runs InsightFace, saves embeddings, and issues a signed QR pass. Display/download/re-key passes; old passes are rejected after re-keying.
- Process signed QR + face or face-only snapshots. Expired payments are denied. Granted entries update occupancy and logs; administrators can check students out.
- Filter the latest 500 entry logs and export CSV. Export student records. View daily, weekly, security and occupancy reports. Times display in IST.
- Configure the Telegram group privately in **Communicate**, verify its identity, send a test or announcement, and inspect delivery history. Announcements, student additions/enrollments, granted entries and security alerts use a persistent queue. Failed deliveries remain queued and retry automatically. The daily summary runs at the configured IST time; default 20:00. Background camera notifications are queued for the next retry cycle.
- Clear loading/error states. Live pages retain the last real response on outages instead of substituting sample students or attendance.

## Private local launch

Requires Docker Desktop or a Docker engine. The supported images use Node 24 and Python 3.12. Configuration and data stay out of Git.

Windows PowerShell:

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

The first face request may download the configured `buffalo_l` models. Browser webcam capture needs HTTPS or localhost and camera permission. Unattended hardware capture is opt-in through `capture.enabled` in the backend configuration and requires the camera host; it is not needed for snapshot upload demonstrations.

## Development and checks

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

The browser test starts disposable local servers and an isolated database. Its neural inference boundary is controlled for CI; production source continues to use the real model. Set `AAMS_TEST_PYTHON` if the backend packages live in a separate Python environment. Tests must run in the same network namespace as their local servers.

CI includes backend tests, frontend lint/build, browser flows, a disposable Docker startup/persistence/proxy check, and a complete hosted-container check. Deployment smoke tests are restricted to disposable GitHub Actions runners and never configure a real Telegram group.

## Database and hosting

SQLite WAL and additive migrations are retained for the single-host showcase. The database, evidence/enrollment photos and model cache use persistent Docker volumes. Backups use SQLite's online backup API, including committed WAL data. Run one API process to keep the camera, scheduler and in-memory rate limits coherent.

For full website hosting, use [deploy/HOSTING.md](deploy/HOSTING.md), `docker-compose.oracle.yml` and `Dockerfile.showcase`. The selected path is Oracle Cloud Always Free: it serves the website and API together, keeps student records/photos/models/signing keys on one persistent volume, and uses Caddy for HTTPS. Production authentication is configured privately on the host. This option requires no local VS Code or terminal after initial hosting setup.

GitHub Pages serves only static files. Secure sign-in and persistent features require a backend; a Pages-only build intentionally cannot sign in. The Pages workflow requires a manual dispatch, so publishing source changes does not automatically publish a site.

PR #8 is merged into `main` with the tested feature build. Hosting publication is still pending a connected container-hosting account and private authentication settings. All existing branches are preserved. See [SHOWCASE_READINESS.md](SHOWCASE_READINESS.md) for verified results and remaining external setup.
