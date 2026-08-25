#!/usr/bin/env python3
"""
Generate QR code for a user.
Run: python -m scripts.generate_qr RA2111003010123
"""

import sys
sys.path.insert(0, '..')

from app.qr_manager import QRManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.generate_qr <user_id>")
        sys.exit(1)
    
    user_id = sys.argv[1]
    qr_manager = QRManager()
    
    # Generate QR image
    qr_bytes = qr_manager.generate_qr_image(user_id)
    
    # Save to file
    output_path = f"images/enrolled/qr_{user_id}.png"
    with open(output_path, 'wb') as f:
        f.write(qr_bytes)
    
    print(f"[OK] QR code generated for {user_id}")
    print(f"  Saved to: {output_path}")

if __name__ == '__main__':
    main()

