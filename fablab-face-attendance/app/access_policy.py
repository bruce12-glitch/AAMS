"""
Access Policy Decision Matrix for FacePass FabLab.
Implements §11.2 Decision Matrix with all 9 rows.
"""

from enum import Enum

class AccessDecision:
    """
    Decision matrix engine for access control.
    Implements all 9 rows from §11.2 specification.
    """
    
    def __init__(self, require_liveness: bool = False):
        """
        Initialize the decision matrix.

        Args:
            require_liveness: when True, a face match is only granted if
                liveness was positively confirmed ('real'). When False, a
                match with active payment is granted even when liveness is
                'unknown' (e.g. a single snapshot with no burst frames).
                See security.require_liveness in config.yaml.
        """
        self.require_liveness = require_liveness
    
    def evaluate_access(self, claimed_id: str, face_result: dict, 
                       payment_status: str, liveness_status: str, 
                       face_count: int) -> dict:
        """
        Evaluate access request using the full decision matrix from §11.2.
        
        Args:
            claimed_id: User ID from token (or None for face-only)
            face_result: Result from identity verification with keys:
                - result: "MATCH"|"PROXY"|"UNKNOWN"|"INVALID_TOKEN"
                - match: bool
                - similarity: float
                - detected_user: str or None
            payment_status: "active"|"expired"|"inactive"|"pending"|"unpaid"
            liveness_status: "real"|"spoof"|"unknown"
            face_count: Number of faces detected in frame
            
        Returns:
            Dictionary with:
            - decision: "GRANTED"|"DENIED"
            - reason: str (human-readable explanation)
            - alert_type: str|None (PROXY/UNPAID/UNKNOWN/SPOOF/TAILGATE/NOFACE)
            - tag: str (authorized/proxy/unpaid/unknown/spoof/tailgate/noface)
        """
        
        # Row 8: Any + spoof detected → DENY + SPOOF alert
        if liveness_status == "spoof":
            return {
                "decision": "DENIED",
                "reason": "Spoof attempt detected (photo/video attack)",
                "alert_type": "SPOOF",
                "tag": "spoof"
            }
        
        # Row 9: Multiple faces → GRANT (to verified) + TAILGATE alert
        if face_count > 1:
            # Still grant to the verified user but raise tailgate alert
            if face_result.get('result') == 'MATCH' and payment_status == 'active':
                return {
                    "decision": "GRANTED",
                    "reason": "Access granted but multiple faces detected (possible tailgating)",
                    "alert_type": "TAILGATE",
                    "tag": "tailgate"
                }
            elif face_result.get('result') == 'MATCH':
                return {
                    "decision": "DENIED",
                    "reason": "Multiple faces detected and payment issue",
                    "alert_type": "TAILGATE",
                    "tag": "tailgate"
                }
        
        # Row 1: Valid token + face matches + active payment + real → GRANT
        if (face_result.get('result') == 'MATCH' and 
            payment_status == 'active' and 
            liveness_status == 'real'):
            return {
                "decision": "GRANTED",
                "reason": "Authorized entry - valid token, verified face, active payment",
                "alert_type": None,
                "tag": "authorized"
            }
        
        # Row 2: Valid token + face matches + expired payment + real → DENY + UNPAID alert
        if (face_result.get('result') == 'MATCH' and 
            payment_status in ['expired', 'unpaid', 'inactive'] and 
            liveness_status == 'real'):
            return {
                "decision": "DENIED",
                "reason": f"Access denied - payment {payment_status}",
                "alert_type": "UNPAID",
                "tag": "unpaid"
            }
        
        # Row 2b: Match + active payment + liveness NOT confirmed.
        #
        # §11.2 has no row for this case, so it fell through to the default
        # fallback and was denied as "unknown" — even when the person was
        # recognised with high confidence. That is actively misleading: the
        # logs showed a 0.89 similarity match tagged 'unknown'.
        #
        # It also broke the normal flow, because the console defaults to
        # "skip liveness" for a single snapshot, so liveness is 'unknown' on
        # almost every request made through the UI.
        if (face_result.get('result') == 'MATCH' and
                payment_status == 'active' and
                liveness_status != 'real'):
            if self.require_liveness:
                return {
                    "decision": "DENIED",
                    "reason": "Liveness not verified - could not confirm a live person",
                    "alert_type": "SPOOF",
                    "tag": "spoof"
                }
            return {
                "decision": "GRANTED",
                "reason": ("Authorized entry - verified face, active payment "
                           "(liveness not verified; set security.require_liveness "
                           "to true to enforce)"),
                "alert_type": None,
                "tag": "authorized"
            }

        # Row 3: Valid token + face mismatch + real → DENY + PROXY alert
        if face_result.get('result') == 'PROXY':
            return {
                "decision": "DENIED",
                "reason": "Proxy attempt - token holder does not match presented face",
                "alert_type": "PROXY",
                "tag": "proxy"
            }
        
        # Row 4: Valid token + no face → DENY + NOFACE alert
        if face_count == 0:
            return {
                "decision": "DENIED",
                "reason": "No face detected",
                "alert_type": "NOFACE",
                "tag": "noface"
            }
        
        # Row 5: Invalid token + face recognized + active → Optional allow or alert
        if (face_result.get('result') == 'INVALID_TOKEN' and 
            face_result.get('detected_user') and 
            payment_status == 'active'):
            # Could allow with warning, or deny with alert
            return {
                "decision": "DENIED",
                "reason": "Invalid token but recognized face - manual verification required",
                "alert_type": "UNKNOWN",
                "tag": "unknown"
            }
        
        # Row 6: Invalid token + face recognized + expired → DENY + UNPAID alert
        if (face_result.get('result') == 'INVALID_TOKEN' and 
            face_result.get('detected_user') and 
            payment_status in ['expired', 'unpaid', 'inactive']):
            return {
                "decision": "DENIED",
                "reason": "Invalid token and payment issue",
                "alert_type": "UNPAID",
                "tag": "unpaid"
            }
        
        # Row 7: Invalid token + unknown face → DENY + UNKNOWN alert
        if face_result.get('result') in ['INVALID_TOKEN', 'UNKNOWN']:
            return {
                "decision": "DENIED",
                "reason": "Unknown person - no matching record found",
                "alert_type": "UNKNOWN",
                "tag": "unknown"
            }
        
        # Default fallback
        return {
            "decision": "DENIED",
            "reason": "Access denied - unable to verify identity",
            "alert_type": "UNKNOWN",
            "tag": "unknown"
        }


# State machine for tracking access flow
ACCESS_STATES = [
    "IDLE",
    "TOKEN_DETECTED",
    "FACE_DETECTED",
    "FACE_RECOGNIZED",
    "PAYMENT_CHECKED",
    "LIVENESS_CHECKED",
    "DECISION_MADE",
    "ACCESS_GRANTED",
    "ACCESS_DENIED",
    "ALERT_SENT",
    "LOG_SAVED"
]


class AccessStateMachine:
    """
    State machine for tracking the access control flow.
    """
    
    def __init__(self):
        """Initialize state machine in IDLE state."""
        self.current_state = "IDLE"
        self.history = []
    
    def transition(self, new_state: str) -> bool:
        """
        Transition to a new state.
        
        Args:
            new_state: The target state
            
        Returns:
            True if transition is valid, False otherwise
        """
        if new_state not in ACCESS_STATES:
            return False
        
        # Simple validation - could add more complex rules
        self.history.append((self.current_state, new_state))
        self.current_state = new_state
        return True
    
    def get_state(self) -> str:
        """Get current state."""
        return self.current_state
    
    def reset(self):
        """Reset to IDLE state."""
        self.current_state = "IDLE"
        self.history = []
