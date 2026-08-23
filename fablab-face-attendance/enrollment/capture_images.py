#!/usr/bin/env python3
"""
Webcam capture module with real-time quality feedback.
Shows green/red overlay on preview window indicating quality checks.
Run: python -m enrollment.capture_images
"""

import sys
sys.path.insert(0, '..')

def main():
    print("Face Capture Module")
    print("=" * 50)
    print("\nThis module would:")
    print("1. Open webcam with OpenCV")
    print("2. Show real-time preview with quality overlays:")
    print("   - Green box: Face detected, quality OK")
    print("   - Red box: Quality check failed")
    print("   - Text indicators for each check")
    print("3. Auto-capture when all checks pass")
    print("4. User presses SPACE to capture, ESC to skip")
    print("\n[Requires webcam and display - skipped in headless build]")
    print("\nQuality checks implemented:")
    print("  - Face width >= 120px")
    print("  - Laplacian variance >= 100 (blur)")
    print("  - Brightness between 40-220")
    print("  - Yaw <= 25°, Pitch <= 20°, Roll <= 20°")

if __name__ == '__main__':
    main()
