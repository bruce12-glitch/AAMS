# AAMS production showcase hosting

## Chosen platform and method

The complete AAMS website will run on **Oracle Cloud Always Free**, not on GitHub Pages, Render or Railway. One Oracle Ampere A1 VM (1 OCPU, 6 GB RAM) runs `docker-compose.oracle.yml`. The `app` container serves the React console and FastAPI API together; Caddy terminates HTTPS and forwards requests internally. SQLite, photos, model downloads and signing keys live in the persistent `aams-data` Docker volume.

This is a single-host showcase design: it is appropriate for the current single-digit audience. Keep one app replica because SQLite, scheduled reports, rate limits and camera ownership are single-process features. The website remains fully functional; it is not a static mockup.

Oracle lists 2 OCPUs and 12 GB RAM of Ampere A1 capacity as Always Free, so the selected 1 OCPU / 6 GB instance leaves headroom while remaining inside the free allocation. Oracle account creation normally requires a phone number and card verification. Do not create paid resources or exceed the Always Free allocation. The public name will be a free DuckDNS hostname, and Caddy provisions and renews TLS automatically.

## Repository assets

| File | Purpose |
| --- | --- |
| `Dockerfile.showcase` | Builds the complete console + API image. |
| `docker-compose.oracle.yml` | App, HTTPS reverse proxy and persistent volumes for the Oracle VM. |
| `deploy/Caddyfile.oracle` | HTTPS and same-origin proxy configuration. |
| `deploy/.env.oracle.example` | Private runtime-variable template; copy it only on the VM. |
| `.github/workflows/deploy-oracle.yml` | Manual GitHub deployment after the server is provisioned. |

No source push publishes a website. The GitHub workflow is manual, verifies its SSH connection before changing the host, fast-forwards only to `main`, rebuilds the two service stack, and probes `/ready` over HTTPS.

## First-time provisioning

The setup will be completed through the Oracle Cloud dashboard after the account is available:

1. Create **one** Always Free `VM.Standard.A1.Flex` instance in the account's home region with **1 OCPU / 6 GB RAM**, Ubuntu, a public IPv4 address, and a 50 GB boot volume. If the A1 shape reports temporary capacity exhaustion, wait or try another availability domain; do not choose a paid shape.
2. Allow inbound TCP **80** and **443** in the Oracle VCN security list. Restrict SSH (22) to the administrator's IP; do not expose the Docker app port 8000.
3. Create a unique free `*.duckdns.org` hostname pointing to the VM public IP. Open only the hostname through HTTPS; Caddy redirects HTTP automatically.
4. Install Docker and Git on the VM, clone `bruce12-glitch/AAMS` to `/srv/aams/AAMS`, copy `deploy/.env.oracle.example` to the ignored `deploy/.env.oracle`, and fill the private values there. The two `AAMS_HOSTNAME`/`ALLOWED_ORIGINS` values must use the exact same hostname.
5. Start the stack with `docker compose --env-file deploy/.env.oracle -f docker-compose.oracle.yml up --build -d`. The first biometric request downloads the InsightFace model to the persistent volume.
6. Store the VM host, its SSH host fingerprint and a dedicated deploy-key in GitHub's **`aams-oracle` environment secrets** as `ORACLE_HOST`, `ORACLE_KNOWN_HOSTS`, and `ORACLE_SSH_PRIVATE_KEY`. Run **Deploy AAMS showcase to Oracle** manually for subsequent updates.

Credentials are never placed in Git, build arguments, browser assets, GitHub Actions logs, or chat. Configure the administrator address with the exact `@srmist.edu.in` domain. The server continues to enforce the SRMIST email restriction and distinct administrator/member credentials. Telegram stays unconfigured for now.

## Persistent state and recovery

The `aams-data` volume holds:

| Path | Contents |
| --- | --- |
| `database/` | SQLite database, WAL files, private notification settings and backups |
| `images/` | Enrollment and evidence images |
| `models/` | InsightFace cache |
| `signing-keys.json` | Private QR/session keys (mode `0600`) |

Back up this volume before moving hosts. Do not attach an empty volume to an existing showcase, overwrite its signing keys, run multiple app replicas or put the database on ephemeral container storage.

## Release verification

After first deployment, verify: HTTPS padlock; rejected non-SRMIST login; administrator sign-in; add/edit a temporary student; enrollment with consented image; QR download/re-key; entry/occupancy/reports; persistence after a controlled container replacement. Remove the temporary student once verified. Browser webcam capture requires HTTPS and camera permission. Telegram is outside this verification scope.

References: [Oracle Always Free compute](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Oracle public IP setup](https://docs.oracle.com/en-us/iaas/Content/Network/Tasks/assign-public-ip-instance-launch.htm), [DuckDNS](https://www.duckdns.org/), [Caddy automatic HTTPS](https://caddyserver.com/docs/quick-starts/https).
