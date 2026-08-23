"""
Identity Verification for FacePass FabLab.
Implements 1:1 and 1:N matching with cosine similarity.
Implements §10 Token+Face Mode and §19 Face-Only Mode.
"""

import numpy as np
from app.database import get_connection, list_from_rows
from app.face_engine import FaceEngine

class IdentityVerifier:
    """
    Identity verification logic for token+face and face-only modes.
    """
    
    def __init__(self):
        """
        Initialize the identity verifier with face engine and database access.
        """
        self.face_engine = FaceEngine()
        self.match_threshold = 0.45  # Configurable via config.yaml
    
    def get_user_embeddings(self, user_id: str) -> list:
        """
        Retrieve all stored embeddings for a user from the database.
        
        Args:
            user_id: The user's unique ID
            
        Returns:
            List of embedding arrays (up to 3) or empty list if not found
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT face_embedding, face_embedding_2, face_embedding_3 
            FROM users 
            WHERE user_id = ? AND active = 1
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row is None:
            return []
        
        embeddings = []
        for i in range(3):
            emb_data = row[i]
            if emb_data is not None:
                # Convert bytes back to numpy array
                embedding = np.frombuffer(emb_data, dtype=np.float64)
                embeddings.append(embedding)
        
        return embeddings
    
    def get_all_user_embeddings(self) -> dict:
        """
        Get embeddings for all active users.
        
        Returns:
            Dictionary of {user_id: [embedding1, embedding2, embedding3]}
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, face_embedding, face_embedding_2, face_embedding_3 
            FROM users 
            WHERE active = 1
        ''')
        
        rows = cursor.fetchall()
        conn.close()
        
        all_embeddings = {}
        for row in rows:
            user_id = row['user_id']
            embeddings = []
            
            for i in range(1, 4):  # Columns 1-3 are embeddings
                emb_data = row[i]
                if emb_data is not None:
                    embedding = np.frombuffer(emb_data, dtype=np.float64)
                    embeddings.append(embedding)
            
            if embeddings:
                all_embeddings[user_id] = embeddings
        
        return all_embeddings
    
    def verify_token_face(self, token_value: str, face_embedding: np.ndarray) -> dict:
        """
        Verify identity using token + face (Mode B - §10).
        
        Flow:
        1. Look up token in tokens table
        2. Get claimed user's stored embeddings (3 per user)
        3. Compare face_embedding against all 3 using cosine similarity
        4. Take the MAX similarity score
        5. If max_similarity >= threshold → MATCH
        6. If max_similarity < threshold → check if face matches ANY other user
           - If yes → PROXY (claimed ≠ detected)
           - If no → UNKNOWN
        
        Args:
            token_value: The token value from QR/RFID
            face_embedding: Normalized embedding from captured face
            
        Returns:
            Dictionary with:
            - match: bool
            - similarity: float (max similarity score)
            - claimed_user: dict or None
            - detected_user: str or None
            - result: "MATCH"|"PROXY"|"UNKNOWN"
        """
        conn = get_connection()
        cursor = conn.cursor()
        
        # Step 1: Look up token
        cursor.execute('''
            SELECT user_id, token_type, active, expires_at 
            FROM tokens 
            WHERE token_value = ? AND active = 1
        ''', (token_value,))
        
        token_row = cursor.fetchone()
        
        if token_row is None:
            conn.close()
            return {
                'match': False,
                'similarity': 0.0,
                'claimed_user': None,
                'detected_user': None,
                'result': 'INVALID_TOKEN'
            }
        
        claimed_user_id = token_row['user_id']
        
        # Get claimed user details
        cursor.execute('''
            SELECT user_id, name, payment_status, payment_expiry, active 
            FROM users 
            WHERE user_id = ?
        ''', (claimed_user_id,))
        
        claimed_user = cursor.fetchone()
        conn.close()
        
        if claimed_user is None:
            return {
                'match': False,
                'similarity': 0.0,
                'claimed_user': None,
                'detected_user': None,
                'result': 'USER_NOT_FOUND'
            }
        
        claimed_user_dict = dict(claimed_user)
        
        # Step 2: Get claimed user's embeddings
        user_embeddings = self.get_user_embeddings(claimed_user_id)
        
        if not user_embeddings:
            return {
                'match': False,
                'similarity': 0.0,
                'claimed_user': claimed_user_dict,
                'detected_user': None,
                'result': 'NO_EMBEDDINGS'
            }
        
        # Step 3: Compare against all 3 embeddings
        max_similarity = 0.0
        for user_emb in user_embeddings:
            similarity = self.face_engine.match_embeddings(face_embedding, user_emb)
            if similarity > max_similarity:
                max_similarity = similarity
        
        # Step 4: Check if match threshold met
        if max_similarity >= self.match_threshold:
            return {
                'match': True,
                'similarity': max_similarity,
                'claimed_user': claimed_user_dict,
                'detected_user': claimed_user_id,
                'result': 'MATCH'
            }
        
        # Step 5: Check if face matches ANY other user (proxy detection)
        all_embeddings = self.get_all_user_embeddings()
        best_match_id, best_score = self.face_engine.find_best_match(
            face_embedding, all_embeddings, threshold=self.match_threshold
        )
        
        if best_match_id and best_match_id != claimed_user_id:
            # PROXY: Face matches someone else
            return {
                'match': False,
                'similarity': max_similarity,
                'claimed_user': claimed_user_dict,
                'detected_user': best_match_id,
                'result': 'PROXY'
            }
        
        # UNKNOWN: Face doesn't match anyone
        return {
            'match': False,
            'similarity': max_similarity,
            'claimed_user': claimed_user_dict,
            'detected_user': None,
            'result': 'UNKNOWN'
        }
    
    def verify_face_only(self, face_embedding: np.ndarray) -> dict:
        """
        Verify identity using face only (Mode A - §19).
        
        Flow:
        1. Search ALL enrolled users
        2. Return best match above threshold or UNKNOWN
        
        Args:
            face_embedding: Normalized embedding from captured face
            
        Returns:
            Dictionary with:
            - match: bool
            - similarity: float
            - user: dict or None
            - result: "MATCH"|"UNKNOWN"
        """
        all_embeddings = self.get_all_user_embeddings()
        
        best_match_id, best_score = self.face_engine.find_best_match(
            face_embedding, all_embeddings, threshold=self.match_threshold
        )
        
        if best_match_id is None:
            return {
                'match': False,
                'similarity': best_score,
                'user': None,
                'result': 'UNKNOWN'
            }
        
        # Get user details
        conn = get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, name, payment_status, payment_expiry, user_type 
            FROM users 
            WHERE user_id = ?
        ''', (best_match_id,))
        
        user_row = cursor.fetchone()
        conn.close()
        
        if user_row is None:
            return {
                'match': False,
                'similarity': best_score,
                'user': None,
                'result': 'UNKNOWN'
            }
        
        return {
            'match': True,
            'similarity': best_score,
            'user': dict(user_row),
            'result': 'MATCH'
        }
