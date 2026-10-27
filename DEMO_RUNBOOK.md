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
   **Enroll face**, obtain consent, and capture one clear front-facing face
   (more views help). Good lighting and no other person in the frame matter.
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

## Keep existing data safe

When updating a downloaded copy, keep your existing private
`fablab-face-attendance/.env` file; copy it locally into the same relative path
in the updated folder without sending it to anyone. The Compose project is
named `aams`, so it reuses the existing Docker volumes on the same Docker engine.
Do not delete volumes in Docker Desktop or use reset/clean commands. This update
does not need a database reset or sample data in your real member list.

Before the real presentation, rehearse once with the actual laptop, volunteer
and Telegram destination. Automated tests use isolated data and controlled
Telegram transport; they cannot prove physical-camera behavior or phone receipt.
