# Security Policy & Hardening Notes

## Status

Prototype hardening applied Aug 2026. See CHANGELOG for the audit-driven fixes.
**Not yet certified for production or campus-wide rollout.**

## What is enforced today

| Control | Implementation |
|---|---|
| Admin authorization | `X-Admin-Token` header vs `API_ADMIN_PASSWORD`, constant-time compare (`hmac.compare_digest`) |
| CORS | Restricted allow-list via `ALLOWED_ORIGINS` (default: localhost dev origins) |
| Rate limiting | Per-IP fixed window, default 120 req/min (`RATE_LIMIT_PER_MIN`), `429 + Retry-After`; `/health` exempt |
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
In-memory, per-process. A multi-replica deployment needs a shared store
(Redis/slowapi) so limits can't be bypassed per-instance.

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
