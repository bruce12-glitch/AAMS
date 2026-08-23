"""
Face Engine for FacePass FabLab.
Implements SCRFD detection + ArcFace embedding + quality checks.
Uses InsightFace library for face analysis.
"""

import cv2
import numpy as np
from insightface.app import FaceAnalysis
from app.config import get_face_config

class FaceEngine:
    """
    Face detection and recognition engine using InsightFace.
    Implements face detection, quality checking, and embedding extraction.
    """
    
    def __init__(self):
        """
        Initialize the InsightFace FaceAnalysis app.
        Uses buffalo_l model with SCRFD detector and ArcFace recognizer.
        """
        config = get_face_config()
        self.det_size = tuple(config.get('resolution', [640, 640]))
        
        # Initialize InsightFace with CPU provider (can be changed to CUDA)
        self.app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=self.det_size)
        
        # Load configuration thresholds
        self.min_face_size = config.get('min_face_size', 120)
        self.blur_threshold = config.get('blur_threshold', 100)
        self.brightness_min = config.get('brightness_min', 40)
        self.brightness_max = config.get('brightness_max', 220)
        self.max_yaw = config.get('max_yaw', 25)
        self.max_pitch = config.get('max_pitch', 20)
        self.max_roll = config.get('max_roll', 20)
    
    def detect_faces(self, frame: np.ndarray) -> list:
        """
        Detect all faces in a frame.
        
        Args:
            frame: BGR image from OpenCV
            
        Returns:
            List of face objects with bounding boxes, landmarks, and embeddings
        """
        # Convert BGR to RGB for InsightFace
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Detect faces
        faces = self.app.get(rgb_frame)
        
        return faces
    
    def quality_check(self, face, frame: np.ndarray) -> tuple:
        """
        Check if a detected face meets quality standards.
        Implements §17.3 Quality Checks.
        
        Args:
            face: Face object from InsightFace
            frame: Original BGR frame
            
        Returns:
            Tuple of (passed: bool, reasons: list)
        """
        reasons = []
        passed = True
        
        # Get face bounding box
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Calculate face width
        face_width = x2 - x1
        face_height = y2 - y1
        
        # Check 1: Face size (must be >= min_face_size pixels)
        if face_width < self.min_face_size:
            reasons.append(f"Face too small: {face_width}px < {self.min_face_size}px")
            passed = False
        
        # Check 2: Blur detection using Laplacian variance
        face_roi = frame[y1:y2, x1:x2]
        if face_roi.size > 0:
            gray_face = cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY)
            laplacian_var = cv2.Laplacian(gray_face, cv2.CV_64F).var()
            
            if laplacian_var < self.blur_threshold:
                reasons.append(f"Face too blurry: variance {laplacian_var:.1f} < {self.blur_threshold}")
                passed = False
        
        # Check 3: Brightness check
        if face_roi.size > 0:
            mean_brightness = np.mean(cv2.cvtColor(face_roi, cv2.COLOR_BGR2GRAY))
            
            if mean_brightness < self.brightness_min:
                reasons.append(f"Face too dark: {mean_brightness:.1f} < {self.brightness_min}")
                passed = False
            elif mean_brightness > self.brightness_max:
                reasons.append(f"Face too bright: {mean_brightness:.1f} > {self.brightness_max}")
                passed = False
        
        # Check 4: Pose estimation (yaw, pitch, roll)
        # InsightFace provides pose information in some models
        if hasattr(face, 'pose') and face.pose is not None:
            yaw, pitch, roll = face.pose
            
            if abs(yaw) > self.max_yaw:
                reasons.append(f"Yaw angle too high: {yaw:.1f}° > {self.max_yaw}°")
                passed = False
            if abs(pitch) > self.max_pitch:
                reasons.append(f"Pitch angle too high: {pitch:.1f}° > {self.max_pitch}°")
                passed = False
            if abs(roll) > self.max_roll:
                reasons.append(f"Roll angle too high: {roll:.1f}° > {self.max_roll}°")
                passed = False
        
        return passed, reasons
    
    def extract_embedding(self, face) -> np.ndarray:
        """
        Extract normalized 512-dimensional embedding from a face.
        Uses ArcFace recognition model.
        
        Args:
            face: Face object from InsightFace with embedding
            
        Returns:
            Normalized 512-d numpy array
        """
        embedding = face.embedding
        
        # Normalize the embedding vector
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm
        
        return embedding
    
    def match_embeddings(self, embedding_a: np.ndarray, embedding_b: np.ndarray) -> float:
        """
        Calculate cosine similarity between two embeddings.
        
        Args:
            embedding_a: First normalized embedding vector
            embedding_b: Second normalized embedding vector
            
        Returns:
            Cosine similarity score (0.0 to 1.0)
        """
        # Cosine similarity = dot product of normalized vectors
        similarity = np.dot(embedding_a, embedding_b)
        
        # Clip to valid range due to floating point precision
        similarity = np.clip(similarity, -1.0, 1.0)
        
        # Convert from cosine distance to similarity (higher is better)
        # InsightFace returns cosine similarity directly
        return float(similarity)
    
    def find_best_match(self, embedding: np.ndarray, all_embeddings: dict, threshold: float = 0.45) -> tuple:
        """
        Perform 1:N search to find the best matching user.
        
        Args:
            embedding: Query embedding vector
            all_embeddings: Dictionary of {user_id: [embedding1, embedding2, embedding3]}
            threshold: Minimum similarity threshold for a match
            
        Returns:
            Tuple of (best_user_id or None, best_score)
        """
        best_user_id = None
        best_score = 0.0
        
        for user_id, user_embeddings in all_embeddings.items():
            # Compare against all stored embeddings for this user
            for user_emb in user_embeddings:
                if user_emb is not None:
                    similarity = self.match_embeddings(embedding, user_emb)
                    
                    if similarity > best_score:
                        best_score = similarity
                        best_user_id = user_id
        
        # Return None if below threshold
        if best_score < threshold:
            return None, best_score
        
        return best_user_id, best_score
    
    def process_frame(self, frame: np.ndarray) -> dict:
        """
        Full processing pipeline: detect → quality check → embed.
        
        Args:
            frame: BGR image from camera
            
        Returns:
            Structured result with faces, quality info, and embeddings
        """
        faces = self.detect_faces(frame)
        
        results = []
        for face in faces:
            passed, reasons = self.quality_check(face, frame)
            embedding = self.extract_embedding(face)
            
            results.append({
                'face': face,
                'bbox': face.bbox.astype(int),
                'landmarks': face.kps,
                'quality_passed': passed,
                'quality_reasons': reasons,
                'embedding': embedding
            })
        
        return {
            'faces': results,
            'face_count': len(results),
            'timestamp': cv2.getTickCount() / cv2.getTickFrequency()
        }
