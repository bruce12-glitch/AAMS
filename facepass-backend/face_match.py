"""
Phase 1: Face Detection and Matching Script
Implements §17.2 - Face Recognition Engine

This script opens the webcam, detects faces using InsightFace (SCRFD + ArcFace),
extracts the 512-d embedding, and compares it with a saved reference image.
"""

import cv2
import numpy as np
from insightface.app import FaceAnalysis
import os

# Initialize InsightFace with buffalo_l model (includes SCRFD detector + ArcFace recognizer)
# Using CPUExecutionProvider for compatibility (switch to 'CUDAExecutionProvider' if GPU available)
print("Initializing InsightFace model...")
face_app = FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
face_app.prepare(ctx_id=0, det_size=(640, 640))
print("✓ Model loaded successfully")


def extract_embedding_from_frame(frame):
    """
    Detect face in frame and extract 512-d embedding.
    
    Args:
        frame: OpenCV BGR image
        
    Returns:
        tuple: (embedding: np.ndarray or None, face_bbox: dict or None)
    """
    # Convert BGR to RGB for InsightFace
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    # Detect faces
    faces = face_app.get(rgb_frame)
    
    if len(faces) == 0:
        return None, None
    
    # Take the first detected face (largest one typically)
    face = faces[0]
    
    # Extract embedding (already normalized by InsightFace)
    embedding = face.embedding
    
    # Get bounding box
    bbox = {
        'x1': int(face.bbox[0]),
        'y1': int(face.bbox[1]),
        'x2': int(face.bbox[2]),
        'y2': int(face.bbox[3])
    }
    
    return embedding, bbox


def cosine_similarity(embedding_a, embedding_b):
    """
    Calculate cosine similarity between two embeddings.
    Implements §17.3 - Cosine Similarity Matching
    
    Args:
        embedding_a: 512-d numpy array
        embedding_b: 512-d numpy array
        
    Returns:
        float: Similarity score (0.0 to 1.0, higher = more similar)
    """
    # Normalize embeddings (should already be normalized, but ensure)
    norm_a = embedding_a / np.linalg.norm(embedding_a)
    norm_b = embedding_b / np.linalg.norm(embedding_b)
    
    # Cosine similarity = dot product of normalized vectors
    similarity = np.dot(norm_a, norm_b)
    
    return float(similarity)


def save_reference_image(image_path, name="reference_face"):
    """
    Capture and save a reference image for comparison.
    
    Args:
        image_path: Path to save the reference image
        name: Name to display in window
    """
    print(f"\n📸 Capturing reference image: {name}")
    print("Position your face in the center and press SPACE to capture")
    
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Cannot open webcam")
        return False
    
    saved = False
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Try to detect face
        embedding, bbox = extract_embedding_from_frame(frame)
        
        if embedding is not None and bbox is not None:
            # Draw bounding box (green when face detected)
            cv2.rectangle(frame, (bbox['x1'], bbox['y1']), 
                         (bbox['x2'], bbox['y2']), (0, 255, 0), 2)
            
            # Display status
            cv2.putText(frame, "Face Detected - Press SPACE to save", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        else:
            cv2.putText(frame, "No Face Detected", 
                       (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow(f"Reference Capture - {name}", frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord(' '):
            if embedding is not None:
                cv2.imwrite(image_path, frame)
                print(f"✓ Reference image saved to: {image_path}")
                saved = True
                break
            else:
                print("⚠ No face detected! Try again.")
        elif key == 27:  # ESC
            print("Capture cancelled")
            break
    
    cap.release()
    cv2.destroyAllWindows()
    return saved


def load_reference_embedding(image_path):
    """
    Load a reference image and extract its embedding.
    
    Args:
        image_path: Path to reference image
        
    Returns:
        np.ndarray: 512-d embedding or None if no face found
    """
    if not os.path.exists(image_path):
        print(f"❌ Reference image not found: {image_path}")
        return None
    
    frame = cv2.imread(image_path)
    embedding, _ = extract_embedding_from_frame(frame)
    
    if embedding is None:
        print("❌ No face detected in reference image!")
        return None
    
    print(f"✓ Reference embedding extracted from: {image_path}")
    return embedding


def main():
    """
    Main function: Run live face matching demo
    """
    print("\n" + "="*60)
    print("   FACEPASS FABLAB - Phase 1: Face Matching Demo")
    print("="*60)
    
    # Define paths
    reference_image_path = "reference_face.jpg"
    
    # Step 1: Check if reference image exists, if not capture one
    if not os.path.exists(reference_image_path):
        print("\n📋 No reference image found. Let's capture one now.")
        if not save_reference_image(reference_image_path, "Your Face"):
            print("❌ Failed to capture reference image. Exiting.")
            return
    else:
        print(f"\n✓ Found reference image: {reference_image_path}")
    
    # Step 2: Load reference embedding
    reference_embedding = load_reference_embedding(reference_image_path)
    if reference_embedding is None:
        print("❌ Could not extract embedding from reference image. Exiting.")
        return
    
    print("\n✅ Reference embedding loaded successfully!")
    print("\n🎯 Starting live matching demo...")
    print("   - Move your face in front of the camera")
    print("   - System will compare with reference image in real-time")
    print("   - Press ESC to exit\n")
    
    # Step 3: Live matching loop
    cap = cv2.VideoCapture(0)
    
    if not cap.isOpened():
        print("❌ Error: Cannot open webcam")
        return
    
    # Match threshold (§17.3 - typically 0.45 for ArcFace)
    MATCH_THRESHOLD = 0.45
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # Detect face and extract embedding
        current_embedding, bbox = extract_embedding_from_frame(frame)
        
        if current_embedding is not None and bbox is not None:
            # Calculate similarity with reference
            similarity = cosine_similarity(current_embedding, reference_embedding)
            
            # Determine match status
            is_match = similarity >= MATCH_THRESHOLD
            
            # Draw bounding box with color based on match
            color = (0, 255, 0) if is_match else (0, 0, 255)  # Green if match, Red if not
            cv2.rectangle(frame, (bbox['x1'], bbox['y1']), 
                         (bbox['x2'], bbox['y2']), color, 2)
            
            # Display similarity score
            score_text = f"Similarity: {similarity:.4f}"
            status_text = "MATCH ✓" if is_match else "NO MATCH ✗"
            
            cv2.putText(frame, score_text, (bbox['x1'], bbox['y1'] - 10), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            cv2.putText(frame, status_text, (bbox['x1'], bbox['y2'] + 25), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, color, 2)
            
            # Print to console periodically
            if similarity > 0.3:  # Only print when there's some similarity
                print(f"Score: {similarity:.4f} | {'MATCH' if is_match else 'NO MATCH'}")
        else:
            cv2.putText(frame, "No Face Detected", (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        
        cv2.imshow("Live Face Matching - Press ESC to Exit", frame)
        
        # Exit on ESC
        if cv2.waitKey(1) & 0xFF == 27:
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    print("\n" + "="*60)
    print("   Demo Complete!")
    print("="*60)
    print(f"\n📊 Summary:")
    print(f"   - Reference image: {reference_image_path}")
    print(f"   - Match threshold: {MATCH_THRESHOLD}")
    print(f"   - Embedding size: 512 dimensions")
    print(f"   - Model: InsightFace (SCRFD + ArcFace)")
    print("\n✨ Phase 1 Complete - AI brain is working!")


if __name__ == "__main__":
    main()
