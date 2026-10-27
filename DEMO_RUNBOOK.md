# AAMS: five-minute local demonstration

No hosting account or paid database is needed. Use your laptop, Docker Desktop,
a consenting volunteer and a phone with Telegram. The website stays at
http://localhost:8090. Public deployment is not part of this rehearsal.

## Prepare before the audience arrives

1. Extract the project, start Docker Desktop and wait until the engine is
   running. Double-click **Start-AAMS.cmd**. Keep the window open until the
   website opens. The first Docker build and model download need internet;
   prepare these ahead of the presentation.
2. First launch only: enter your administrator **@srmist.edu.in** email and
   private administrator password, then the required shared member password.
   These two passwords must be different. Later launches reuse the saved
   configuration. Sign in as the administrator, not with the shared credential.
3. **Dashboard → Prototype setup → Initialize face model.** Wait for **Ready**.
   Database connectivity alone does not mean recognition is ready.
4. **Communicate:** enter the current bot token privately, enable Telegram
   delivery and automatic granted-entry messages, then **Save settings**.
   For personal chat: **Connect my Telegram → Open my bot in Telegram → Start**,
   then return and **Connect this chat** within five minutes. For a group: add
   the bot to the group and save the negative group ID or public group username.
5. **Verify chat → Send test message.** Confirm receipt on the intended phone
   or group. A “sent” response means Telegram accepted the message, not that
   someone has read it. “Queued” is not a successful delivery.
6. **Members → Add student:** use a unique student ID, full name, real SRMIST
   email and the required details. Set payment **active** with no past expiry.
   **Enroll face**, obtain consent, and capture 3 clear original photos with
   the same laptop webcam used for attendance. Do not use AI-enhanced portraits
   or sharpen a failed image to force it through the quality gate. Good lighting,
   proximity and no other person in the frame matter.
7. Dashboard must show at least one member with an enrolled face and current
   active payment. Close other applications using the camera. Keep the laptop
   powered, the browser tab visible and internet connected for Telegram.

## Present in this order

| Time | Action | Evidence to show |
| --- | --- | --- |
| 0:00 | Sign in and show Dashboard | Database, model and eligible member checks |
| 0:30 | Open Members | Student details, enrolled face and QR pass |
| 1:15 | Live Monitor → Start webcam attendance; allow camera | Volunteer’s name and real entry decision |
| 2:00 | Show Telegram and Entry Logs | Automatic named entry message with IST time and saved attendance |
| 2:30 | Keep the same person at the camera for the next scan | “Already recorded”; no new attendance or entry message |
| 3:00 | Stop webcam; Dashboard → Check out | Occupancy changes |
| 3:30 | Return to Live Monitor and start again | Valid re-entry and a new automatic entry message |
| 4:15 | Stop webcam; show Reports/CSV | Attendance and occupancy summary |

Blink verification is on by default for webcam attendance. Look into the camera
and blink naturally. If using **Prototype demo: skip blink check**, disclose
that liveness is bypassed and photos may be accepted; it is not an anti-spoofing
demonstration. Do not silently present scenario simulation buttons as real
recognition.

## Fast recovery without code

| What you see | What to do |
| --- | --- |
| Website does not open | Confirm Docker Desktop is running; open localhost:8090 manually. If startup failed, keep the error window and share a screenshot without passwords/tokens. |
| Model not ready | Dashboard → initialize/retry. Check internet and available storage; allow time for first download. |
| Camera denied/in use | Allow camera in the browser’s site controls and close Camera/Teams/Zoom; stop/start webcam attendance. |
| No face / low quality | Move closer, face the camera, improve lighting, keep only one person in frame. |
| Identity result INVALID_TOKEN | Use Face only for recognition testing. For Member + Face, select the actual member and regenerate their QR if expired/revoked. This is not a failed face comparison. |
| NO_EMBEDDINGS / EMPTY_GALLERY | A profile is not a face enrollment. Members → Enroll face, and wait for embeddings stored. |
| Matched but denied | Check account is active, payment is active/unexpired and blink is confirmed. |
| Already recorded | This is expected duplicate protection. Stop webcam, check out on Dashboard, then start again for re-entry. |
| Telegram queued | Communicate → check enabled destination, Verify chat, Send test. Check bot/group permissions and internet; failed sends retry automatically. |
| Telegram entry messages off | Enable **Automatically announce granted entries**, save and test again after checkout. |
| Optional Lab Camera says standby | Normal for this laptop setup; the browser webcam is separate. |

Typing “Attendance” to the bot does not activate the camera. Start attendance on
the website. The browser stops capturing when hidden or when you navigate away;
an already accepted request may still finish. Avoid changing tabs until the
result has returned. Local recognition can work offline once models are cached;
Telegram requires internet.

## Check recognition before recording attendance

Live Monitor → **Photo & camera check** defaults to **Face only**. Upload an
original photo or capture from the webcam, then **Check photo — no attendance**.
The backend performs the same quality, embedding, identity and policy checks
but does not save evidence, attendance, occupancy or a Telegram notification.
Results show the detected face box, quality measurements, identity result and
cosine score versus threshold. A score is not an accuracy percentage. If the
token is invalid or enrollment is missing, comparison is explicitly “Not performed”.

Use **Member + Face** only to test a particular member's current pass and face.
The member selector identifies profiles without face enrollment. An arbitrary
number in the student-ID field will not create a valid enrollment or pass.

The still-photo option explicitly bypasses liveness. Uncheck it and choose
**Capture blink sequence** to capture 10 frames automatically; blink naturally,
then **Use sequence**. A static burst or inconclusive blink stays denied when
liveness is requested. Lack of a blink is not labelled proof of a spoof.
**Record entry** is a separate deliberate action and uses duplicate suppression.

Before claiming accuracy, test consenting volunteers with different enrollment
and probe captures. Record genuine accept/reject and different-person accept/reject
counts, with the same camera and lighting as the demo. Do not tune and evaluate
the threshold on the same captures. The bundled two-portrait regression is not
that evaluation and does not establish a false-accept rate.

## Keep existing data safe

### Account and payment controls

The top bar must say **ADMIN** to edit people. A shared member-password login
is deliberately read-only: sign out and use the configured administrator email
and its separate private password. Knowing an SRMIST address alone does not grant
administrator rights. On **Members**, **Account** controls Enabled/Disabled;
**Payment** separately controls active/pending/expired/inactive. Changes display
a saved confirmation or an error; refresh/reload to confirm persistence.

Disabling an account revokes its passes, closes any open visit and keeps its
face enrollment. Re-enabling does **not** revive revoked QR passes; issue a new
pass if required. Active payment can still be blocked by a past payment expiry.

### Current records and older examples

Entry Logs show names, decisions, reasons, IST timestamps and capture sources.
**Not compared** is not a similarity of zero, and missing historical comparison
information is shown as **Not recorded**. A denied attempt is not attendance.
No-face, low-quality and invalid-pass failures are not automatically security
incidents. The dashboard and Alerts show a factual review queue; **Mark reviewed**
does not authorize entry or prove misconduct.

The update does not guess whether old rows were genuine. Previously stored rows
without source information are kept under **Older / unverified records**;
explicit sample records are labelled **Demo data**. Select **All records** when
needed. Counts and a history notice make this separation visible. The original
records are not deleted or rewritten. Capture-source labels describe the request
path (the browser reports webcam use); they do not establish physical presence
or tamper-proof camera provenance. Dashboard attendance counts only granted,
current recorded events; reports exclude explicitly labelled sample entries.

Do not run the demo seeder on your presentation database. It now refuses production
or non-empty databases, creates no fake face embeddings or occupied visits, and
labels its isolated development examples so they cannot be sent to Telegram.

When updating a downloaded copy, keep your existing private
`fablab-face-attendance/.env` file; copy it locally into the same relative path
in the updated folder without sending it to anyone. The Compose project is
named `aams`, so it reuses the existing Docker volumes on the same Docker engine.
Do not delete volumes in Docker Desktop or use reset/clean commands. This update
does not need a database reset or sample data in your real member list.

Before the real presentation, rehearse once with the actual laptop, volunteer
and Telegram destination. Automated tests use isolated data and controlled
Telegram transport; they cannot prove physical-camera behavior or phone receipt.
