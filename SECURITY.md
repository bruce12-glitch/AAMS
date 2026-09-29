# Security Policy & Hardening Notes

## Status

Prototype hardening applied Aug 2026. See CHANGELOG for the audit-driven fixes.
**Not yet certified for production or campus-wide rollout.**

## What is enforced today

| Control | Implementation |
|---|---|
| Console sign-in | SRMIST mail **+ password**; PBKDF2-SHA256 (200 k iters, random salt), constant-time compare, hashes stripped from every response |
| Admin authorization | `X-Admin-Token` header vs `API_ADMIN_PASSWORD`, constant-time compare (`hmac.compare_digest`) |
| Admin-guarded routes | QR pass generation (bearer credential), alert approve/acknowledge, member CRUD, enrollment, payment update, occupancy exit/scan, Telegram send |
| CORS | Restricted allow-list via `ALLOWED_ORIGINS` (default: localhost dev origins) |
| Rate limiting | Per-IP fixed window, default 120 req/min (`RATE_LIMIT_PER_MIN`), `429 + Retry-After`; `/health` exempt |
| Sign-in brute force | 10 attempts/min per mail ID (`LOGIN_RATE_LIMIT`) and 50/min per IP, `429 + Retry-After`, checked before the database |
| Upload validation | `user_id` allowlist (letters/digits/`.`/`-`/`_`, ≤64) so IDs can't escape `images/`, ≤10 photos per enrollment, ≤8 MB base64 and ≤40 MP per frame |
| Door pipeline | `POST /api/entry/process` and `/face-only` stay open for the lab host — put them behind the reverse proxy / LAN, they are the only unauthenticated writers |
| QR passes | HMAC-SHA256 signed payloads with expiry, verified server-side (§27.3) |
| Health probes | `/health` is side-effect free; model state isolated at `/model-status` |
| Data retention | Nightly purge: entry logs >90 d, alert images >30 d (§26.4) |

## Known limitations & required mitigations before pilots

### Transport security (TLS)
The API serves plain HTTP. **Terminate TLS at the reverse proxy** — the
compose file sketches an optional Caddy service:

```
# deploy/Caddyfile
lab.example.edu {
    reverse_proxy api:8000
}
```

Any standards-compliant proxy works (nginx + certbot equally fine).
Until TLS is on: admin tokens and face photos transit in cleartext —
do not expose the deployment beyond the lab LAN.

### Admin token storage (XSS surface)
The console stores the admin token in `localStorage` to attach it to
mutating requests. Any XSS in the console could exfiltrate it.
Mitigations in place/roadmap:
- Token is only used from the Enroll modal / member actions, never logged
- Roadmap: server-issued httpOnly session cookie + CSP headers

### Fail-open dev mode
With `API_ADMIN_PASSWORD` unset, admin endpoints are open **by design for
local development**, with a loud startup warning and per-request logs.
Never run this mode on a network others can reach.

### Rate limiter scope
In-memory, per-process — the sign-in limiter uses the same store. A
multi-replica deployment needs a shared store (`REDIS_URL` is already
supported) so limits can't be bypassed per-instance.

### Data at rest
SQLite and evidence photos are unencrypted local files (fine for one lab;
volume-backed in compose). For multi-site or sensitive rollouts, move to
Postgres + encrypted object storage with backups.

### Camera network
Place the entrance camera on an isolated VLAN; the host needs outbound
access only for Telegram API calls.

## Reporting

Contact the Fab Lab project team (see repository owner) for anything
security-related. Please do not open public issues for exploitable findings.
