# FacePass FabLab AAMS — Spec Reconstruction & Development Analysis

**System:** Smart Anti-Proxy Facial Access and Attendance Management System  
**Site:** SRMIST Fab Lab  
**Version referenced in UI:** AAMS v1.0  
**Source of this analysis:** No PDF was present in the workspace. The document below is reconstructed from every `§` citation in the repo (backend modules, tests, `legacy/console-fragment.html`, READMEs) plus a line-by-line review of the current implementation.

If you attach the original PDF, this file should be re-checked against the source text rather than inferred comments.

---

## 1. What the spec is asking the product to do

AAMS is an **edge-deployed access-control + attendance** system for one physical entrance (CAM-01, Fab Lab Entrance).

A person either:

- **Mode B (§10) — Token + Face (default):** scans a signed QR / RFID token, then faces the camera. The claimed identity is 1:1 matched to the live face. If the live face matches a *different* enrolled user → **proxy**.
- **Mode A (§19 / §10 fallback) — Face-only:** no token. 1:N search of all enrolled embeddings. Used when someone walks up without a pass, or as fallback.

Every attempt is decided by a **9-row policy matrix (§11.2)**, logged for 90 days, and (when severity is medium/high) pushed to a Telegram in-charge group with a photo. Occupancy is tracked live with a 30-minute timeout. A daily report fires at 20:00.

This is **not** a generic attendance app. The research / acceptance bar is anti-proxy and anti-unpaid, not “mark present if a face is seen.”

---

## 2. Spec map (reconstructed table of contents)

| Section | Topic | What it mandates |
|---|---|---|
| **§9.3** | Capture quality | Face width ≥ 120 px; Laplacian blur ≥ 100; brightness 40–220; pose \|yaw\|≤25°, \|pitch\|≤20°, \|roll\|≤20°. Enrollment UI cites the same gates. |
| **§10** | Entry modes | Mode A = face-only; Mode B = token + face. Pipeline: Token/QR → SCRFD → quality → ArcFace 512-d → cosine ≥ 0.45 → blink EAR → payment → policy. |
| **§11.2** | Decision matrix | 9 rows (see §3). Output = `{decision, reason, alert_type, tag}`. |
| **§11.3** | Access state machine | `IDLE → TOKEN_DETECTED → FACE_DETECTED → FACE_RECOGNIZED → PAYMENT_CHECKED → LIVENESS_CHECKED → DECISION_MADE → ACCESS_GRANTED\|DENIED → ALERT_SENT → LOG_SAVED`. |
| **§12 / §13** | Liveness | Blink via Eye Aspect Ratio, 5 s challenge. EAR drop then rise = real; flat EAR = spoof. |
| **§14 / §14.5** | Occupancy | Statuses: `inside`, `exited`, `timeout_exited`. Timeout **30 min without detection**. Optional indoor scan every 120 s (`indoor_scan_enabled`). |
| **§15 / §15.2** | Telegram | Exact message templates for PROXY / UNPAID / UNKNOWN / SPOOF / TAILGATE / SYSTEM. Daily report format #7. Photo attached. |
| **§16** | Schema | 6 tables: `users`, `tokens`, `entry_logs`, `occupants`, `alerts`, `admin_actions`. |
| **§17 / §17.2–17.4** | Recognition + enrollment | SCRFD + ArcFace; cosine match; **5 poses captured, 3 embeddings stored** (mean + 2 best). |
| **§19** | Face-only | 1:N, best score ≥ 0.45 or UNKNOWN. |
| **§21** | Configuration | `config.yaml` + `.env` overrides for secrets. |
| **§26 / §26.2 / §26.4** | Privacy | Written biometric consent required. Deletion purges embeddings. Retention: logs **90 d**, alert images **30 d**, daily reports **1 y**. |
| **§27.3** | Signed QR | HMAC-SHA256 over `{user_id, issued_at, expires_at}`, 24 h TTL. |
| **§28** | Dashboard | Live monitor, KPIs, logs, alerts, users, reports, research/threshold page. |
| **§29 / §29.3** | Alert severity | High/medium → Telegram now. **Low (authorized grant, exit) → daily report only.** |
| **§30.5** | Payment updates | Live DB read. Changing payment does **not** require re-enrollment. |
| **§30.6** | Camera fault | CAM-01 offline → SYSTEM FAULT alert + **manual register mode**. |

### 2.1 Research / acceptance targets (from console RQ cards)

| ID | Metric | Target | Prototype claim |
|---|---|---|---|
| RQ1 | Recognition accuracy | > 95% | 96.4% |
| RQ2 | Proxy detection rate | ≥ 95% | 100% |
| RQ3 | Unpaid silently accepted | **0** | 0 |
| RQ4 | Occupancy vs manual headcount | > 90% | 93% |
| RQ6 | Entry decision time | < 3 s | 1.9 s |
| RQ6 | Alert delivery | < 5 s | 2.4 s |

These are **product acceptance tests**, not dashboard decoration. Development work must be able to measure them.

### 2.2 Hardware / runtime assumed by the spec

- Edge node: Raspberry Pi 5, 24/7
- CAM-01: Logitech C920, **1280×720 @ 5 fps** (not 30 fps — CPU budget)
- 7″ door screen: grant / deny / fault copy
- Telegram Bot API → in-charge group
- Local SQLite `fablab.db`
- Models: InsightFace `buffalo_l` (SCRFD + ArcFace 512-d), ~500 MB first download

---

## 3. Decision matrix §11.2 — the core product

| Row | Token | Face | Payment | Liveness | Faces | Decision | Alert | Tag |
|---|---|---|---|---|---|---|---|---|
| 1 | Valid | Matches claimed | `active` | `real` | 1 | **GRANTED** | none (low / daily) | `authorized` |
| 2 | Valid | Matches claimed | `expired` / `unpaid` / `inactive` | `real` | 1 | DENIED | UNPAID | `unpaid` |
| 3 | Valid | Mismatch, other enrolled user | — | `real` | 1 | DENIED | PROXY | `proxy` |
| 4 | Valid | None | — | — | 0 | DENIED | NOFACE | `noface` |
| 5 | Invalid | Recognized enrolled | `active` | `real` | 1 | DENIED (manual verify) | UNKNOWN | `unknown` |
| 6 | Invalid | Recognized enrolled | expired / unpaid / inactive | `real` | 1 | DENIED | UNPAID | `unpaid` |
| 7 | Invalid / none | Unknown | — | `real` | 1 | DENIED | UNKNOWN | `unknown` |
| 8 | Any | Any | Any | **`spoof`** | any | DENIED | SPOOF | `spoof` |
| 9 | Valid | Matches + `active` | `active` | `real` | **>1** | **GRANTED** + flag | TAILGATE | `tailgate` |

**Priority implied by the code (and the prototype):** spoof > multi-face > match+pay > proxy > no-face > invalid-token variants > unknown.

### 3.1 Policy bugs to fix before treating the matrix as done

1. **`pending` payment is not treated as unpaid.** Row 2 only lists `expired|unpaid|inactive`. Demo user Karthik is `pending`. He currently falls through toward GRANT if face matches and liveness is real. That **violates RQ3**. Add `pending` (and any non-`active` status) to the unpaid set.
2. **Row 9 + unpaid:** if `face_count > 1` and result is MATCH but payment is not active, the engine returns DENIED + **TAILGATE only**. The unpaid signal is dropped. Combine: deny, `alert_type=UNPAID` (or dual alert), keep tailgate as secondary tag.
3. **Row 4 vs empty `face_result`:** no-face is only checked *after* MATCH/PROXY rows. Fine today, but if a caller sends `result=MATCH` with `face_count=0`, row 1 would grant. Guard: `face_count == 0` must be evaluated immediately after spoof.
4. **Row 5 “optional allow”** is implemented as always DENY. Spec comment says “optional allow or alert.” Product decision needed: deny + manual override (current) is safer; document it as the chosen variant.
5. **State machine exists but is unused** by `/api/entry/*`. The live UI is the only place that walks §11.3. Wire states into the entry pipeline so `/dashboard/live` can show them.

---

## 4. Data model §16 — what to persist and why

```
users          1 ─── * tokens
  │                    (token_value UNIQUE, type qr|rfid, issued/expires, active)
  ├── * entry_logs     (every attempt, 90 d)
  ├── * occupants      (session: inside | exited | timeout_exited)
  └── * admin_actions  (overrides, payment edits, deletions)

alerts         independent of users (unknown / spoof / system have no user_id today)
```

### `users` fields that matter for policy

| Column | Role |
|---|---|
| `user_id` | Register number, e.g. `RA2111003010123` |
| `payment_status` | `active` / `expired` / `pending` / `inactive` / `unpaid` — **live, no re-enroll** |
| `payment_expiry` | Displayed on door + UNPAID alert |
| `face_embedding{,_2,_3}` | Three 512-d vectors; match = **max** cosine |
| `consent_given` | Must be 1 to enroll / remain searchable |
| `active` | Soft disable without deleting biometrics |

### Schema / storage issues

- Embeddings are stored as **raw `float64` bytes**. InsightFace ArcFace outputs **float32**. Mixing dtypes in `np.frombuffer(..., dtype=np.float64)` will silently produce garbage vectors. **Standardize on float32 + explicit length 512.**
- `tokens.token_value` is a DB lookup string, but `QRManager` produces a **signed JSON payload**. Those two worlds are not joined: `generate_qr` does not INSERT into `tokens`; `verify_token_face` does not HMAC-verify the QR JSON. This is the largest Mode-B hole.
- `entry_logs.claimed_id` is sometimes written as the **raw token string**, not the user id (`routes_entry.py`). Reports and proxy joins then break.
- No `user_id` / `claimed_id` on `alerts` — cannot ack/approve against a person without parsing `message`.
- SQLite FKs are declared but **PRAGMA foreign_keys is never enabled**.
- No scheduled purge for §26.4 retention.

---

## 5. Runtime architecture (as designed)

```
                    ┌──────────── 7" door screen ────────────┐
Webcam 5 fps ──► CameraManager ──► FaceEngine (SCRFD+ArcFace)
                                      │
                                      ▼
                              LivenessChecker (EAR blink, 5s)
                                      │
QR / RFID ──► QRManager.verify ──► IdentityVerifier (1:1 or 1:N)
                                      │
                                      ▼
                              AccessDecision.evaluate  (§11.2)
                                      │
                    ┌─────────────────┼─────────────────┐
                    ▼                 ▼                 ▼
              entry_logs        OccupancyTracker   AlertService → Telegram
              (90 days)         inside/exit/30m    + photo evidence
                                      │
                              APScheduler
                              20:00 daily report
                              every 5 min timeout sweep
                              23:00 DB backup
```

Frontend (intended): React/Vite console (`src/`) replacing the rich static prototype in `legacy/console-fragment.html` / `index.html`.

API surface already sketched:

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/entry/process` | Mode B |
| POST | `/api/entry/face-only` | Mode A |
| POST | `/api/entry/simulate` | Demo scenarios (TC01–TC08) |
| CRUD | `/api/users` + `GET /{id}/qr` | Enrollment / payment / delete |
| GET | `/api/dashboard/stats\|activity\|live\|research` | Console |
| GET | `/api/reports/{daily,weekly,proxy,unpaid,occupancy}` | §15.2 |
| GET/POST | `/api/admin/exceptions`, `POST /payment-update` | §30.5 |
| — | occupants / alerts routers | Live list + ack/approve |

---

## 6. Enrollment §17 — required flow vs current code

**Specified flow**

1. Collect name, register no., phone, email, type, payment + expiry.
2. Operator ticks **written consent** (§26.2): purpose, data collected, storage, retention, deletion right.
3. Capture **5 poses**: front, slight left, slight right, glasses (if any), slight smile.
4. Run §9.3 quality on each; reject and recapture failures.
5. Extract 5 embeddings; store **3** (mean + 2 highest-quality).
6. Write `users` + images under `images/enrolled/{user_id}/`.
7. Issue signed QR (and persist token).

**Current state:** CLI prints the 5 poses then **stores one random 512-d vector**. Webcam path is stubbed. API `POST /api/users` creates a user **with zero embeddings**. QR image is generated but **not stored as a token row**.

Until this is real, **every recognition/proxy test is fiction**.

---

## 7. Gap matrix — spec vs repo (development backlog)

Priority: **P0** blocks a real door. **P1** blocks research claims / ops. **P2** polish.

### P0 — cannot run a real entry event

| Gap | Spec | Code today | Fix |
|---|---|---|---|
| Client-side embeddings | Server detects on the frame | `POST /entry/process` accepts `face_embedding: list` | Accept JPEG/PNG or multipart frame; run `FaceEngine.process_frame` server-side. Never trust client vectors. |
| Enrollment is fake | 5 poses → 3 embeddings | Random placeholder | Implement `enrollment/capture_images.py` + quality loop; persist 3 embeddings + face image. |
| QR not in the identity path | §27.3 HMAC payload is the token | `verify_token_face` looks up `tokens.token_value` only; expiry ignored | `process`: `QRManager.verify_token(json)` → `user_id`; still record a `tokens` row for audit / revoke. Check `expires_at` and `active`. |
| Granted entry does not mark inside | §14 | `/entry/process` only INSERTs `entry_logs` | On GRANTED call `OccupancyTracker.mark_inside`; on EXIT endpoint call `mark_exit`. |
| Alerts not fired | §15 | Formatters exist; process route never calls them | After decision, if `alert_type`, save image to `images/alerts/`, `save_alert_to_db`, `send_alert`. |
| Face-only not logged | §16.3 every attempt | `/entry/face-only` returns JSON only | Same log + occupancy + alert path as Mode B. |
| Liveness is non-functional | §12/13 EAR on 6-pt eyes | buffalo_l gives **5-point** kps; 6-pt EAR never runs; `calculate_avg_ear` returns 0.5; single-frame always `unknown` | Use InsightFace 106-pt (`buffalo_l` landmark_2d_106) **or** MediaPipe FaceMesh. Config load is also broken (`get_face_config()` returns only `face:`, not `liveness:`). |
| No camera-offline watchdog | §30.6 | `/dashboard/live` constructs a **new** `CameraManager()` per request (never `start()`), so always offline | Process-wide singleton; if no frame for 5 s → SYSTEM alert + `manual_register` flag. |

### P1 — correctness, security, research

| Gap | Why it matters | Fix |
|---|---|---|
| CORS `allow_origins=['*']`, admin unauthenticated | Anyone can flip payment or delete biometrics | Auth on `/api/admin/*` and mutating user routes; restrict CORS to the console origin. Secrets only in `.env`. |
| `IdentityVerifier` constructs a new `FaceEngine` (loads buffalo_l) every request | >3 s budget dies; Pi 5 will OOM/thrash | App-lifespan singleton for FaceEngine + Camera + AlertService + Occupancy. |
| Match threshold hardcoded `0.45` | §21 says config-driven | Read `face.match_threshold`. |
| Timeout uses `entry_time` not `last_seen_time` | Spec: “30 min **without detection**” | Timeout if `now - last_seen > 30m`. Enable indoor scan or treat each grant as last_seen. |
| `reports.generate_occupancy_report` uses `HOUR()` | SQLite has no `HOUR()` | `strftime('%H', entry_time)`. |
| No retention job | §26.4 | Nightly: delete logs >90 d, alert images >30 d, keep report text 1 y. |
| Tests instantiate `FaceEngine()` | CI will download 500 MB / fail offline | Split `cosine_similarity` into a pure function; mock InsightFace. |
| Door screen / relay | Prototype shows 7″ copy | Even a JSON `door` payload on the entry response is enough for a first kiosk. |
| Admin override on UNPAID | Prototype: approve → occupant + `admin_actions` | `POST /api/admin/override-entry`. |

### P2 — frontend & ops

| Gap | Fix |
|---|---|
| React `src/App.jsx` is a static 4-KPI scaffold | Port pages from `legacy/console-fragment.html`: Live, Logs, Alerts, Users, Reports. Wire to `/api/*`. Keep scenario buttons calling `/api/entry/simulate` until camera is live. |
| Live MJPEG / WebRTC | `/api/dashboard/live` should stream annotated frames, not spawn cameras. |
| Indoor scan disabled | Optional second camera; leave off until occupancy RQ4 is measured. |
| Backup path | Scheduler copies db; add rotate / keep 7 days. |

---

## 8. Recommended build sequence (development)

Do **not** start by polishing the React theme. The spec is an **entry pipeline**. Suggested order:

### Phase 0 — make the engine testable (1–2 days)

- Extract `cosine_similarity(a, b)` and `max_match(query, gallery, threshold)` with **no InsightFace import**.
- Fix embedding dtype (`float32`, len 512) in serialize/deserialize helpers.
- Expand `test_access_policy.py`: `pending` must deny; spoof beats grant; `face_count=0` never grants; tailgate+unpaid.
- Add `test_qr_manager.py` (tamper, expiry, happy path).
- Add `test_identity.py` with fixture embeddings (same / other / none).

### Phase 1 — real capture path (the P0)

1. Lifespan singletons: `FaceEngine`, `CameraManager`, `AlertService`.
2. `POST /api/entry/process` body: `{ token_json?, image_base64, face_count? }` — detect on server.
3. Enrollment webcam: 5 quality-gated frames → 3 embeddings + consent flag + QR row.
4. Connect QR verify → claimed user → 1:1 max-of-3 → 1:N proxy check.
5. On decision: log, occupancy, Telegram, door payload.

### Phase 2 — liveness that can fail a photo

- 106-point or FaceMesh EAR over `timeout_seconds * fps` frames (5 s × 5 fps = 25 frames).
- Challenge UX: door says “blink now”.
- Until this works, **do not claim spoof detection** (TC08 / RQ not measurable).

### Phase 3 — ops loop

- Camera watchdog + manual register form (name + reason → `admin_actions` + occupant).
- 20:00 report already scheduled — verify Markdown + photo-less send.
- Retention + backup rotation.
- Admin auth.

### Phase 4 — console

- Rebuild Live Monitor from the legacy prototype against real APIs.
- Scenario grid remains for demos (TC01 authorized, TC03 unpaid, TC04 unknown, TC05 proxy, TC06 noface, TC07 tailgate, TC08 spoof, §30.6 camera drill).
- Reports copy must match §15.2 templates (the prototype `reportDaily()` text is the contract).

### Phase 5 — measure RQs before any “done” claim

- RQ1/RQ2: labeled gallery + live set (same person, proxy pairs).
- RQ3: automated matrix test + a paid/expired fixture user.
- RQ4: 1-day headcount vs `occupants`.
- RQ6: timestamps from first frame to decision / Telegram `sent_at`.

---

## 9. Entry pipeline — implement exactly this order

The prototype `STEPS` array is the spec’s sequence. Keep it:

1. **Token / QR** — HMAC verify, not-expired, map to `claimed_id`. Face-only: skip and tag Mode A.
2. **Face capture** — SCRFD on the current frame; abort after 5 s with NOFACE.
3. **Quality** — §9.3; if fail, recapture (do not match a blurry face).
4. **Embedding** — ArcFace 512-d L2-normalized.
5. **Match** — Mode B: max cosine vs claimed user’s 3 vectors. If `< 0.45`, 1:N for PROXY vs UNKNOWN. Mode A: 1:N only.
6. **Liveness** — 5 s blink. Fail → SPOOF, stop.
7. **Payment** — read **live** `users.payment_status` (and expiry date).
8. **Decision** — §11.2 only. Then log, maybe alert, maybe occupy, update door.

Do not reorder payment before match (you would leak unpaid alerts on strangers). Do not skip liveness on 1:N.

---

## 10. Telegram contracts (§15.2) — keep byte-stable

Downstream operators will screenshot these. Backend formatters already approximate them; align to the prototype strings:

```
PROXY ALERT
Location: Fab Lab Entrance
Claimed ID: …
Detected Face: …
Confidence: 0.21
Time: …
Photo attached

UNPAID ENTRY ATTEMPT
Name: …
ID: …
Payment Expired: 12 Aug 2026
Time: …
Photo attached

UNKNOWN PERSON ALERT
Time: …
Photo attached

SPOOF ALERT
Possible photo/video used
Time: …
Photo attached

TAILGATING ALERT
Multiple faces detected during one entry event
Time: …
Photo attached

SYSTEM FAULT
Camera CAM-01 offline
Location: Fab Lab Entrance
Manual register mode active
Time: …
```

Daily report title in prototype: `FAB LAB DAILY REPORT` with counts + numbered active-user lines. `ReportGenerator.generate_daily` is close; `to_plain_text` is **not** that template — rewrite it.

Low priority (§29.3): authorized grant and normal EXIT must **not** hit Telegram.

---

## 11. Security & privacy checklist (ship blockers)

- [ ] Replace `CHANGE_THIS*` and default HMAC key.
- [ ] QR HMAC uses `hmac.compare_digest` (already).
- [ ] Tokens revocable (`tokens.active = 0`) and short-lived (24 h).
- [ ] Consent flag required; refuse 1:N on `consent_given = 0`.
- [ ] DELETE user purges all three embeddings, face image, tokens. Log `admin_actions`.
- [ ] No embeddings in JSON APIs (list_users already nulls them — keep it).
- [ ] Do not store raw frames except: enrollment refs, alert evidence (30 d).
- [ ] Admin password / session on mutating routes.
- [ ] HTTPS in production; CORS allowlist.
- [ ] Camera frames never leave the LAN except Telegram evidence.

---

## 12. What is already in good shape (do not rewrite)

- Policy function is isolated and unit-tested for the 9 happy rows — extend, don’t replace.
- Alert **formatters** and report **queries** are the right modules.
- Occupancy API (mark inside / exit / timeout / last_seen) matches §14 vocabulary.
- QR HMAC construction is correct; it just is not wired into entry.
- Config split (`config.yaml` + `.env`) matches §21.
- Legacy console is a high-fidelity **interaction spec** for the React port (pipeline, door copy, scenario IDs TC01–TC08, report text). Treat it as the UX source of truth.

---

## 13. Suggested module changes (minimal, concrete)

```
app/embeddings.py          NEW  serialize/deserialize float32[512], cosine, max-of-gallery
app/face_engine.py         KEEP detect/quality/embed; drop matching into embeddings.py
app/identity.py            USE  QRManager.verify + embeddings helpers; load threshold from config
app/liveness.py            REPLACE 5-pt hack with 106-pt / FaceMesh sequence
app/access_policy.py       FIX  pending, noface-first, tailgate+unpaid
api/routes_entry.py        REWRITE single process_attempt() used by both modes
app/main.py                lifespan: engine, camera, alerts, scheduler
enrollment/enroll_user.py  REAL capture; write 3 embeddings + token row
src/pages/*                PORT live / logs / alerts / users / reports from legacy HTML
scripts/purge_retention.py NEW  §26.4
```

---

## 14. If the original PDF differs

Re-open this analysis and check in order:

1. Decision-matrix row wording (especially row 5 allow-vs-deny and row 9 grant-vs-deny).
2. Timeout: from **entry** vs from **last detection**.
3. Number of stored embeddings (3 vs all 5).
4. Match threshold (0.45 is typical ArcFace cosine; confirm).
5. Whether Mode A is production or demo-only.
6. Retention periods and lawful basis text for the consent form.

---

*Generated for development use from repository evidence. Not a substitute for the signed specification PDF.*
