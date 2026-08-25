#!/usr/bin/env python3
"""
Standalone webcam capture utility with live quality overlays (§9.3).

Shows a preview window with green/orange/red box depending on whether the
face passes size, blur, brightness and pose gates. SPACE captures a shot,
ESC quits. Saved shots land in images/enrolled/captures/.

Run:  python -m enrollment.capture_images
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def main():
    import cv2

    from app.face_engine import FaceEngine
    from app.utils import save_frame

    engine = FaceEngine()
    cam = cv2.VideoCapture(0)
    if not cam.isOpened():
        print("[ERROR] No webcam found.")
        return

    cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

    shots = 0
    print("SPACE=capture · ESC=quit")

    try:
        while True:
            ok, frame = cam.read()
            if not ok:
                break

            faces = engine.detect_faces(frame)
            status, color = "NO FACE", (0, 0, 255)
            passed = False

            if faces:
                face = max(faces, key=lambda f: f.bbox[2] * f.bbox[3])
                passed, reasons = engine.quality_check(face, frame)
                x1, y1, x2, y2 = face.bbox.astype(int)
                color = (0, 255, 0) if passed else (0, 165, 255)
                status = "OK — press SPACE" if passed else \
                    (reasons[0] if reasons else "checking…")
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)

            cv2.putText(frame, status, (20, 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2)
            cv2.imshow("FacePass Capture", frame)

            key = cv2.waitKey(30) & 0xFF
            if key == 27:
                break
            if key == 32 and passed:
                path = save_frame(frame, 'enrolled',
                                  prefix=f"capture_{shots + 1:02d}")
                shots += 1
                print(f"saved -> {path}")
    finally:
        cam.release()
        cv2.destroyAllWindows()
        print(f"Done. {shots} image(s) captured.")


if __name__ == '__main__':
    main()
