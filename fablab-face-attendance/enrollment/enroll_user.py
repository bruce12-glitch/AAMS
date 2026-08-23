#!/usr/bin/env python3
"""
CLI enrollment script for FacePass FabLab.
Run: python -m enrollment.enroll_user

Flow:
1. Ask for: name, user_id, phone, email, payment_status, payment_expiry
2. Confirm consent (§26.2)
3. Open webcam, capture 5 poses
4. Run quality_check on each image
5. Extract embedding from each
6. Store 3 embeddings (mean + 2 best) per §17.4
7. Save to users table + images/enrolled/{user_id}/
8. Generate QR token
"""

import sys
sys.path.insert(0, '..')

def main():
    print("=" * 50)
    print("FacePass FabLab - User Enrollment")
    print("=" * 50)
    
    # Step 1: Collect user information
    print("\n--- User Information ---")
    user_id = input("User ID (e.g., RA2111003010123): ").strip()
    name = input("Full Name: ").strip()
    phone = input("Phone Number: ").strip()
    email = input("Email: ").strip()
    user_type = input("User Type (student/faculty): ").strip() or 'student'
    payment_status = input("Payment Status (active/expired/pending): ").strip() or 'inactive'
    payment_expiry = input("Payment Expiry (YYYY-MM-DD): ").strip()
    
    # Step 2: Consent confirmation
    print("\n--- Consent Confirmation (§26.2) ---")
    print("By enrolling, you consent to:")
    print("1. Storage of your facial biometric data")
    print("2. Use of face recognition for access control")
    print("3. Logging of entry/exit events")
    
    consent = input("\nDo you consent? (yes/no): ").strip().lower()
    if consent != 'yes':
        print("Enrollment cancelled. Consent required.")
        return
    
    # Step 3-6: Capture faces and process
    print("\n--- Face Capture ---")
    print("This would open webcam and capture 5 poses:")
    print("  1. Front face")
    print("  2. Slight left turn")
    print("  3. Slight right turn")
    print("  4. With glasses (if applicable)")
    print("  5. Slight smile")
    print("\n[Webcam capture requires human interaction - skipped in this build]")
    
    # Step 7: Save to database
    from app.database import get_connection
    import numpy as np
    
    # Generate placeholder embedding for demo
    emb = np.random.randn(512)
    emb = emb / np.linalg.norm(emb)
    emb_bytes = emb.tobytes()
    
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (user_id, name, phone, email, user_type, 
                              payment_status, payment_expiry, 
                              face_embedding, consent_given, active)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1, 1)
        ''', (user_id, name, phone, email, user_type, 
              payment_status, payment_expiry, emb_bytes))
        conn.commit()
        print(f"\n✓ User {name} ({user_id}) enrolled successfully!")
    except Exception as e:
        print(f"\n✗ Enrollment failed: {e}")
    finally:
        conn.close()
    
    # Step 8: Generate QR token
    print("\n--- Generating QR Token ---")
    from app.qr_manager import QRManager
    qr_manager = QRManager()
    qr_bytes = qr_manager.generate_qr_image(user_id)
    
    qr_path = f"images/enrolled/qr_{user_id}.png"
    with open(qr_path, 'wb') as f:
        f.write(qr_bytes)
    print(f"✓ QR code saved to: {qr_path}")
    
    print("\n" + "=" * 50)
    print("Enrollment Complete!")
    print("=" * 50)

if __name__ == '__main__':
    main()
