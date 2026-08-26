# Go-Live Checklist - every box must tick first

## Secrets & access
- [ ] API_ADMIN_PASSWORD set (long random value; dev-open mode OFF)
- [ ] QR_SECRET_KEY set (random >= 32 chars); rotating it invalidates old passes
- [ ] TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID set and a test alert received
- [ ] ALLOWED_ORIGINS lists only origins you control

## Transport
- [ ] TLS terminated at Caddy/nginx with real hostname (deploy/Caddyfile)
- [ ] HTTP -> HTTPS redirect verified; HSTS header present
- [ ] API not reachable on plain HTTP from outside the lab LAN

## Data & recovery
- [ ] database/ and images/ on persistent volumes or backed-up paths
- [ ] Manual backup taken: python -m scripts.backup_db
- [ ] Restore rehearsed once on a scratch DB

## AI sanity
- [ ] >= 10 users enrolled; each recognized in Snapshot Entry Test
- [ ] calibrate_threshold run; match_threshold updated from its output
- [ ] /api/dashboard/latency p95 < 3000 ms on entrance hardware
- [ ] One controlled proxy attempt detected + alert received end-to-end

## Process
- [ ] Signage posted at entrance (spec section 31.3 wording)
- [ ] Signed consent forms filed; consent_given=1 only after signature
- [ ] In-charge briefed on fallback: manual register + how to stop the service
