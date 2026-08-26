# Fab Lab Biometric Access — Consent Form (Template)

> §26.2 of the AAMS specification. Print one per participant.
> Keep signed copies in a locked folder; record `consent_given = 1` only after signature.

---

## Study Title
Smart Anti-Proxy Facial Access and Attendance System (FacePass) — SRMIST Fab Lab Pilot

## Researcher / Team Contact
Name(s): ______________________  Phone: ______________  Email: ______________

## Purpose
This system automates Fab Lab entry verification using face recognition to
prevent proxy attendance and unpaid access, and to maintain an occupancy list.

## What we collect
- Name, register number, phone (optional), email (optional)
- Payment status and expiry (admin-entered)
- Face photographs taken at enrollment
- Mathematical face embeddings (512-number vectors) derived from those photos
- Entry/exit timestamps at the lab entrance

## How it is used
- Only to verify your identity at the Fab Lab entrance and log attendance
- Alerts on proxy/unpaid/unknown attempts are sent privately to the Lab In-charge

## What we will NEVER do
- Sell or share your data with anyone outside the project team and Fab Lab administration
- Use it for any purpose other than Fab Lab access control and attendance

## Storage & retention (§26.4)
- Data is stored in a local database on Fab Lab equipment, not on cloud servers
- Entry logs are deleted after **90 days**; alert photos after **30 days**
- Your enrollment data is deleted when you leave the Fab Lab or withdraw consent

## Your rights
- Ask for a copy of your data at any time (export feature available)
- Withdraw consent at any time → your profile, photos and embeddings are deleted
- Ask to use an alternative manual check-in if you prefer not to participate

## Voluntary participation
Participation is voluntary. Not participating will not affect your lab access
eligibility beyond standard payment requirements.

---

**Consent**

I have read this form. I agree to the enrollment and processing described above.

Name: ______________________  Register No.: ______________________

Signature: ______________________  Date: ____ / ____ / ________

Witness (project team): ______________________

> After signing: run enrollment (`Members → ＋ Enroll` or the webcam CLI),
> tick the consent checkbox, and file this sheet.
