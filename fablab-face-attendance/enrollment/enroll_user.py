#!/usr/bin/env python3
"""
CLI enrollment for FacePass FabLab (§17).

Full implementation:
  1. Prompts for user details + consent
  2. Opens the webcam with a live preview
  3. Guides through 5 poses, auto-capturing when quality gates pass
     (size / blur / brightness / pose — §9.3)
  4. Extracts ArcFace embeddings, stores best 3
  5. Saves profile photos + issues signed QR token

NOTE: running this requires a human in front of the webcam.
For headless environments use POST /api/users/enroll with photos instead.

Run:  python -m enrollment.enroll_user
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

POSES = [
    ("Front face — look straight at the camera", 2),
    ("Slight left turn", 1),
    ("Slight right turn", 1),
    ("With glasses (if you normally wear them)", 1),
    ("Slight smile", 1),
]


def prompt_details() -> dict | None:
    print("=" * 56)
    print("FacePass FabLab - User Enrollment")
    print("=" * 56)

    user_id = input("User ID (e.g., RA2111003010123): ").strip()
    if not user_id:
        print("User ID is required."); return None
    name = input("Full Name: ").strip()
    if not name:
        print("Name is required."); return None
    phone = input("Phone Number: ").strip()
    email = input("Email: ").strip()
    user_type = input("User Type [student]: ").strip() or 'student'
    payment_status = input("Payment Status active/expired/pending [inactive]: ").strip() or 'inactive'
    payment_expiry = input("Payment Expiry YYYY-MM-DD: ").strip()

    print("\nConsent (§26.2) — by enrolling you agree to:")
    print("  1. Storage of your facial biometric data (local DB only)")
    print("  2. Use solely for Fab Lab access control & attendance")
    print("  3. Logging of entry/exit events; deletion on request")
    if input("\nDo you consent? (yes/no): ").strip().lower() != 'yes':
        print("Enrollment cancelled — consent required.")
        return None

    return dict(user_id=user_id, name=name, phone=phone or None,
                email=email or None, user_type=user_type,
                payment_status=payment_status,
                payment_expiry=payment_expiry or None,
                consent_given=True)


def capture_poses(user_id: str):
    """Interactive webcam loop; returns list of (frame, embedding)."""
    import cv2

    from app.face_engine import FaceEngine
    from app.utils import save_frame

    engine = FaceEngine()
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        raise RuntimeError(
            "No webcam available. Use the API instead:\n"
            "  POST /api/users/enroll  with base64 photos"
        )

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    captured = []

    try:
        for label, needed in POSES:
            got_for_pose = 0
            print(f"\n[POSE] {label}  (need {needed} good shot(s))")

            while got_for_pose < needed:
                ok, frame = cam.read()
                if not ok:
                    raise RuntimeError("Camera frame read failed")

                faces = engine.detect_faces(frame)
                status, color = "NO FACE", (0, 0, 255)

                if faces:
                    face = max(faces, key=lambda f: f.bbox[2] * f.bbox[3])
                    passed, reasons = engine.quality_check(face, frame)
                    x1, y1, x2, y2 = face.bbox.astype(int)
                    color = (0, 255, 0) if passed else (0, 165, 255)
                    status = "QUALITY OK - hold still..." if passed \
                        else reasons[0] if reasons else "checking..."

                preview = frame.copy()
                if faces:
                    x1, y1, x2, y2 = max(faces, key=lambda f: f.bbox[2] * f.bbox[3]).bbox.astype(int)
                    cv2.rectangle(preview, (x1, y1), (x2, y2), color, 2)
                cv2.putText(preview, status, (20, 40),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
                cv2.putText(preview, f"{user_id}: {len(captured)} saved",
                            (20, 74), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                            (255, 255, 255), 1)
                cv2.imshow("FacePass Enrollment (ESC to abort)", preview)

                key = cv2.waitKey(30) & 0xFF
                if key == 27:
                    raise RuntimeError("Aborted by user")

                if faces and passed:
                    emb = engine.extract_embedding(
                        max(faces, key=lambda f: f.bbox[2] * f.bbox[3]))
                    captured.append((frame.copy(), emb))
                    got_for_pose += 1
                    save_frame(frame, 'enrolled', prefix=f"{user_id}_p{len(captured)}")
                    print(f"   captured {len(captured)} embeddings total")
    finally:
        cam.release()
        cv2.destroyAllWindows()

    return captured


def store_user(details: dict, captured: list) -> None:
    import numpy as np

    from app.database import get_connection
    from app.qr_manager import QRManager

    embs = [emb.astype(np.float64) for _, emb in captured[:3]]
    while len(embs) < 3:
        mean_emb = np.mean([e for e in embs], axis=0)
        norm = np.linalg.norm(mean_emb)
        embs.append(mean_emb / norm if norm > 0 else mean_emb)

    conn = get_connection()
    cur = conn.cursor()
    cur.execute('SELECT id FROM users WHERE user_id=?', (details['user_id'],))
    exists = cur.fetchone()

    cols = (details['name'], details['phone'], details['email'],
            details['user_type'], details['payment_status'],
            details['payment_expiry'],
            embs[0].tobytes(), embs[1].tobytes(), embs[2].tobytes())

    if exists:
        cur.execute('''UPDATE users SET name=?, phone=?, email=?, user_type=?,
            payment_status=?, payment_expiry=?, face_embedding=?,
            face_embedding_2=?, face_embedding_3=?, consent_given=1,
            active=1, updated_at=CURRENT_TIMESTAMP WHERE user_id=?''',
            (*cols, details['user_id']))
    else:
        cur.execute('''INSERT INTO users (user_id, name, phone, email,
            user_type, payment_status, payment_expiry, face_embedding,
            face_embedding_2, face_embedding_3, consent_given, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)''',
            (details['user_id'], *cols))

    # Issue fresh token (raw id form; signed QR also generated below)
    cur.execute('UPDATE tokens SET active=0 WHERE user_id=?', (details['user_id'],))
    cur.execute('''INSERT INTO tokens (token_value, user_id, token_type, active)
        VALUES (?, ?, 'qr', 1)''', (details['user_id'], details['user_id']))
    conn.commit()
    conn.close()

    qr = QRManager()
    png_path = Path('images') / 'enrolled' / f"{details['user_id']}_qr.png"
    png_path.parent.mkdir(parents=True, exist_ok=True)
    png_path.write_bytes(qr.generate_qr_image(details['user_id']))
    print(f"\nQR pass saved -> {png_path}")


def main():
    details = prompt_details()
    if not details:
        return

    print("\nStarting camera... look at the preview window.")
    try:
        captured = capture_poses(details['user_id'])
    except RuntimeError as exc:
        print(f"\n[ABORTED] {exc}")
        return

    store_user(details, captured)

    print("\n" + "=" * 56)
    print(f"ENROLLED {details['name']} ({details['user_id']})")
    print(f"  embeddings stored : 3")
    print(f"  payment status    : {details['payment_status']}")
    print("=" * 56)


if __name__ == '__main__':
    main()
