# Full website hosting

`Dockerfile.showcase` builds React and FastAPI into one container. Both are served on the platform's `PORT`, so login, uploads, QR passes and reports use the same HTTPS origin. The original two-service Compose stack remains available for local use.

## Railway setup

Use a GitHub-connected service for `bruce12-glitch/AAMS`, branch `main`:

| Setting | Value |
| --- | --- |
| Build | Dockerfile |
| Dockerfile path | `Dockerfile.showcase` (or variable `RAILWAY_DOCKERFILE_PATH=Dockerfile.showcase`) |
| Persistent volume mount | `/data` |
| Replicas | `1` |
| Health check | `/ready` |
| Start command | Image default, `python start_showcase.py` |
| Public domain | Generate HTTPS domain after the service is healthy |
| Auto-deploy | Disable until the release is verified; enable only if desired |

Create the volume before the first deployment. The launcher refuses to run a Railway service without its volume metadata. Do not use a build/pre-deploy command to initialize the volume; volumes are available at runtime. Use native service settings rather than the deprecated config-as-code format for a new service.

Configure these values privately in the provider's Variables screen:

| Variable | Requirement |
| --- | --- |
| `ADMIN_EMAIL` | Your exact `@srmist.edu.in` administrator address |
| `API_ADMIN_PASSWORD` | Private administrator credential, at least 12 characters |
| `AAMS_ACCESS_PASSWORD` | Private shared member credential, at least 12 characters; different from administrator credential |
| `RAILWAY_DOCKERFILE_PATH` | `Dockerfile.showcase`, if not selected in build settings |

Do not put credentials in Git, chat messages, build arguments or frontend variables. The server enforces the SRMIST domain for both sign-in and student records. A shared member password does not verify ownership of a mailbox.

The launcher enforces production mode and supplies stable random QR/session signing keys on the volume. Existing `QR_SECRET_KEY` / `SESSION_SECRET_KEY` overrides are supported for an intentional migration; keep them permanently consistent with the source instance. Changing or removing an override can invalidate sessions and existing passes. Do not configure a second replica: the scheduler, camera ownership and rate limiter are process-local, and SQLite is intended for a single-host showcase.

Telegram is deferred. No bot credentials or group setup are required to start or use the other features.

## Persistent state and recovery

The mounted data directory holds:

| Path | Contents |
| --- | --- |
| `database/` | SQLite database, WAL files, private notification settings and scheduled backups |
| `images/` | Enrollment and evidence photos |
| `models/` | InsightFace cache, downloaded on the first face request |
| `signing-keys.json` | Generated private QR/session keys (mode `0600`) |

Only the built `web-dist` folder is public. `/images`, `/database`, `/data` and signing keys are not static routes. Evidence photos remain private; QR downloads use authenticated API routes. Back up the entire volume, including signing keys, before moving hosts. Do not attach an empty volume over an existing installation without a planned migration.

The launcher accepts `AAMS_DATA_DIR` for another container host; default `/data`. `DATABASE_PATH` and `INSIGHTFACE_ROOT` must remain inside that directory. It refuses to overwrite an existing ordinary image directory containing photos.

For a different Docker host, mount a persistent directory at `/data`, supply the private variables above, and route HTTPS to `PORT` (default `8000`). No separate database service is necessary. The host must have enough memory/CPU for the actual model; use runtime metrics during real-image verification before selecting a production plan. Hardware capture requires a camera-attached host; browser snapshot upload works remotely.

## Release verification

CI builds the complete image and verifies HTML/assets, API readiness, SRMIST rejection, secure login, student creation, private-file protection, and student/photo/session persistence after destroying and recreating the container with its volume. It does not publish a domain or send Telegram messages.

After deploying, verify the HTTPS address, sign in as the configured administrator, add/edit a temporary student, enroll a consented image, download/re-key its QR, submit an entry snapshot, check occupancy/checkout, and inspect reports. Confirm persistence after a controlled redeploy; then remove the temporary record. The first face request downloads the model, so allow it to finish before showcasing. Webcam capture needs camera permission and HTTPS. Measure biometric and liveness performance with consented volunteers on the intended camera before operational use, and review pretrained-model licensing before commercial use.

Provider references: [Dockerfile selection](https://docs.railway.com/builds/dockerfiles), [persistent volumes](https://docs.railway.com/volumes), [config-as-code lifecycle](https://docs.railway.com/config-as-code/reference).
