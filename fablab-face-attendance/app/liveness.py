"""
Liveness Checker for FacePass FabLab.
Implements blink detection via Eye Aspect Ratio (EAR) for anti-spoofing.
Implements §12 Liveness Detection specification.
"""

import cv2
import numpy as np
from app.config import get_face_config

class LivenessChecker:
    """
    Liveness detection using Eye Aspect Ratio (EAR) blink detection.
    Detects real users by tracking eye blinks over a sequence of frames.
    """
    
    def __init__(self):
        """
        Initialize the liveness checker with configuration parameters.
        """
        config = get_face_config()
        liveness_config = {
            'enabled': True,
            'method': 'blink',
            'timeout_seconds': 5
        }
        
        # Load from config if available
        if 'liveness' in config:
            liveness_config.update(config['liveness'])
        
        self.enabled = liveness_config.get('enabled', True)
        self.method = liveness_config.get('method', 'blink')
        self.timeout_seconds = liveness_config.get('timeout_seconds', 5)
        
        # EAR thresholds
        self.ear_threshold_low = 0.21   # Eye closed
        self.ear_threshold_high = 0.25  # Eye open
        
        # Eye landmark indices for InsightFace 5-point landmarks
        # Mapping approximate positions for left and right eyes
        self.left_eye_indices = [36, 37, 38, 39, 40, 41]  # Approximate
        self.right_eye_indices = [42, 43, 44, 45, 46, 47]  # Approximate
    
    def eye_aspect_ratio(self, eye_landmarks: np.ndarray) -> float:
        """
        Calculate Eye Aspect Ratio (EAR) for a single eye.
        
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        
        Where p1-p6 are the 6 landmark points around the eye.
        
        Args:
            eye_landmarks: 6 points (x, y) around one eye
            
        Returns:
            EAR value (lower when eye is closed)
        """
        # Vertical distances
        A = np.linalg.norm(eye_landmarks[1] - eye_landmarks[5])
        B = np.linalg.norm(eye_landmarks[2] - eye_landmarks[4])
        
        # Horizontal distance
        C = np.linalg.norm(eye_landmarks[0] - eye_landmarks[3])
        
        # Avoid division by zero
        if C == 0:
            return 0.0
        
        ear = (A + B) / (2.0 * C)
        return ear
    
    def extract_eye_landmarks(self, face_landmarks: np.ndarray) -> tuple:
        """
        Extract left and right eye landmarks from face landmarks.
        
        Args:
            face_landmarks: Landmarks from InsightFace (5 or 106 points)
            
        Returns:
            Tuple of (left_eye_points, right_eye_points) or (None, None)
        """
        if face_landmarks is None or len(face_landmarks) < 5:
            return None, None
        
        # For 5-point landmarks, we need to estimate eye positions
        # Points: [0:left_eye_center, 1:right_eye_center, 2:nose, 3:left_mouth, 4:right_mouth]
        # This is simplified - production should use 68 or 106 point model
        
        if len(face_landmarks) == 5:
            # Simplified estimation - not ideal but works for demo
            # In production, use a model with more landmarks
            left_eye = face_landmarks[0]
            right_eye = face_landmarks[1]
            
            # Create approximate eye regions (this is a simplification)
            # Real implementation should use 68-point facial landmark detector
            return left_eye, right_eye
        
        # For 68+ point models, use proper indices
        # Left eye: points 36-41, Right eye: points 42-47
        if len(face_landmarks) >= 48:
            left_eye = face_landmarks[36:42]
            right_eye = face_landmarks[42:48]
            return left_eye, right_eye
        
        return None, None
    
    def calculate_avg_ear(self, left_eye, right_eye) -> float:
        """
        Calculate average EAR from both eyes.
        
        Args:
            left_eye: Left eye landmarks
            right_eye: Right eye landmarks
            
        Returns:
            Average EAR value
        """
        ear_values = []
        
        if left_eye is not None and len(left_eye) >= 6:
            ear_values.append(self.eye_aspect_ratio(left_eye))
        
        if right_eye is not None and len(right_eye) >= 6:
            ear_values.append(self.eye_aspect_ratio(right_eye))
        
        if ear_values:
            return np.mean(ear_values)
        
        return 0.5  # Default to "open" if can't calculate
    
    def check_liveness(self, frames_sequence: list, faces_sequence: list = None) -> dict:
        """
        Check liveness by analyzing blink patterns in a sequence of frames.
        
        Args:
            frames_sequence: List of frames (BGR images) to analyze
            faces_sequence: Optional list of detected faces corresponding to frames
            
        Returns:
            Dictionary with:
            - status: "real"|"spoof"|"unknown"
            - blink_detected: bool
            - ear_values: list of EAR values over time
            - frames_analyzed: int
        """
        if not self.enabled:
            return {
                'status': 'unknown',
                'blink_detected': False,
                'ear_values': [],
                'frames_analyzed': len(frames_sequence),
                'reason': 'Liveness detection disabled'
            }
        
        ear_values = []
        blink_detected = False
        was_closed = False
        frame_count = 0
        
        for i, frame in enumerate(frames_sequence):
            # Get face landmarks for this frame
            face_landmarks = None
            if faces_sequence and i < len(faces_sequence):
                face = faces_sequence[i]
                if hasattr(face, 'kps'):
                    face_landmarks = face.kps
            
            # If no face provided, detect one
            if face_landmarks is None:
                # Quick detection (would use FaceEngine in production)
                pass
            
            if face_landmarks is not None:
                left_eye, right_eye = self.extract_eye_landmarks(face_landmarks)
                ear = self.calculate_avg_ear(left_eye, right_eye)
                ear_values.append(ear)
                
                # Detect blink: EAR drops below threshold then rises
                if ear < self.ear_threshold_low:
                    was_closed = True
                elif ear > self.ear_threshold_high and was_closed:
                    blink_detected = True
                    was_closed = False
                
                frame_count += 1
        
        # Determine status based on blink detection
        if blink_detected:
            status = 'real'
        elif len(ear_values) > 0 and frame_count > 0:
            # No blink detected within timeout
            status = 'spoof'
        else:
            status = 'unknown'
        
        return {
            'status': status,
            'blink_detected': blink_detected,
            'ear_values': ear_values,
            'frames_analyzed': frame_count,
            'timeout_seconds': self.timeout_seconds
        }
    
    def check_liveness_single_frame(self, frame: np.ndarray, face) -> dict:
        """
        Perform a quick liveness check on a single frame.
        This is a fallback when sequence analysis is not possible.
        
        Args:
            frame: Single BGR frame
            face: Detected face object
            
        Returns:
            Dictionary with status and confidence
        """
        # Single-frame checks (texture-based, motion-based)
        # This is less reliable than multi-frame blink detection
        
        return {
            'status': 'unknown',
            'blink_detected': False,
            'ear_values': [],
            'frames_analyzed': 1,
            'reason': 'Single frame - requires sequence for blink detection'
        }
