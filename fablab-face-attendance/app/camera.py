"""
Camera Manager for FacePass FabLab.
Handles webcam capture with configurable FPS and resolution.
"""

import threading
import time
from app.config import get_camera_config

class CameraManager:
    """
    Manages webcam capture with controlled FPS to save CPU.
    """
    
    def __init__(self, source=0, fps=None, resolution=None):
        """
        Initialize camera with configuration.
        
        Args:
            source: Camera device index (0 = default webcam)
            fps: Frames per second to capture (not 30fps to save CPU)
            resolution: Tuple of (width, height)
        """
        config = get_camera_config()
        
        self.source = config.get('source', source)
        self.fps = config.get('fps', fps or 5)
        self.resolution = tuple(config.get('resolution', resolution or [1280, 720]))
        
        self.camera = None
        self.frame = None
        self.lock = threading.Lock()
        self.running = False
        self.thread = None
        
        # Frame timing
        self.frame_interval = 1.0 / self.fps
        self.last_frame_time = 0
    
    def start(self):
        """Start camera capture in background thread."""
        if self.running:
            return

        try:
            import cv2
        except ImportError as exc:
            raise RuntimeError("opencv-python is required to start the camera") from exc
        
        self.camera = cv2.VideoCapture(self.source)
        
        if not self.camera.isOpened():
            raise RuntimeError(f"Failed to open camera {self.source}")
        
        # Set resolution
        self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, self.resolution[0])
        self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, self.resolution[1])
        
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
    
    def _capture_loop(self):
        """Background thread for capturing frames at controlled FPS."""
        while self.running:
            current_time = time.time()
            
            # Check if enough time has passed for next frame
            if current_time - self.last_frame_time >= self.frame_interval:
                ret, frame = self.camera.read()
                
                if ret:
                    with self.lock:
                        self.frame = frame.copy()
                    self.last_frame_time = current_time
            
            # Small sleep to prevent CPU spinning
            time.sleep(0.01)
    
    def stop(self):
        """Stop camera capture."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
        if self.camera:
            self.camera.release()
            self.camera = None
    
    def capture_frame(self):
        """
        Capture a single frame.
        
        Returns:
            numpy array (BGR image) or None if camera offline
        """
        if not self.is_online():
            return None
        
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
        return None
    
    def is_online(self) -> bool:
        """Check if camera is online and capturing."""
        return self.running and self.camera is not None and self.camera.isOpened()
    
    def get_status(self) -> dict:
        """
        Get camera status information.
        
        Returns:
            Dictionary with online status, FPS, and resolution
        """
        return {
            "online": self.is_online(),
            "fps": self.fps,
            "resolution": list(self.resolution),
            "source": self.source,
            "note": "singleton camera is started by the live API, not per request",
        }
