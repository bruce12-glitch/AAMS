"""
Utility helpers for FacePass FabLab.
Image saving, timestamp formatting, and other common functions.
"""

import os
import cv2
from datetime import datetime
from pathlib import Path

# Base directory for images
BASE_DIR = Path(__file__).parent.parent
IMAGES_DIR = BASE_DIR / "images"

def ensure_image_dirs():
    """Ensure all image directories exist."""
    dirs = [
        IMAGES_DIR / "enrolled",
        IMAGES_DIR / "logs",
        IMAGES_DIR / "alerts"
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

def save_frame(frame, subdir: str, prefix: str = None) -> str:
    """
    Save a frame to disk with timestamp filename.
    
    Args:
        frame: BGR image array
        subdir: Subdirectory (enrolled/logs/alerts)
        prefix: Optional prefix for filename
        
    Returns:
        Relative path to saved image
    """
    ensure_image_dirs()
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    if prefix:
        filename = f"{prefix}_{timestamp}.jpg"
    else:
        filename = f"{timestamp}.jpg"
    
    save_path = IMAGES_DIR / subdir / filename
    
    cv2.imwrite(str(save_path), frame)
    
    # Return relative path
    return f"images/{subdir}/{filename}"

def format_timestamp(dt: datetime = None) -> str:
    """Format datetime as readable string."""
    if dt is None:
        dt = datetime.now()
    return dt.strftime('%d %b %Y, %I:%M %p')

def get_current_time_iso() -> str:
    """Get current time in ISO format."""
    return datetime.now().isoformat()

def calculate_duration(start_iso: str, end_iso: str = None) -> dict:
    """
    Calculate duration between two ISO timestamps.
    
    Returns:
        Dictionary with seconds, minutes, hours
    """
    start = datetime.fromisoformat(start_iso)
    end = datetime.fromisoformat(end_iso) if end_iso else datetime.now()
    
    delta = end - start
    total_seconds = int(delta.total_seconds())
    
    return {
        'seconds': total_seconds,
        'minutes': round(total_seconds / 60, 1),
        'hours': round(total_seconds / 3600, 2)
    }

def resize_frame(frame, max_width: int = 640, max_height: int = 480) -> tuple:
    """
    Resize frame while maintaining aspect ratio.
    
    Returns:
        Tuple of (resized_frame, scale_factor)
    """
    h, w = frame.shape[:2]
    
    scale = min(max_width / w, max_height / h)
    
    if scale < 1.0:
        new_w = int(w * scale)
        new_h = int(h * scale)
        resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
        return resized, scale
    
    return frame, 1.0

def draw_bbox(frame, bbox: list, color: tuple = (0, 255, 0), thickness: int = 2):
    """
    Draw bounding box on frame.
    
    Args:
        frame: BGR image
        bbox: [x1, y1, x2, y2]
        color: BGR color tuple
        thickness: Line thickness
    """
    x1, y1, x2, y2 = map(int, bbox)
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    return frame

def draw_text(frame, text: str, position: tuple, color: tuple = (0, 255, 0)):
    """Draw text on frame with background."""
    x, y = position
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.6
    thickness = 2
    
    # Get text size
    (text_w, text_h), baseline = cv2.getTextSize(text, font, font_scale, thickness)
    
    # Draw background rectangle
    cv2.rectangle(frame, (x, y - text_h - baseline), 
                  (x + text_w, y + baseline), color, -1)
    
    # Draw text
    cv2.putText(frame, text, (x, y), font, font_scale, (0, 0, 0), thickness)
    return frame
