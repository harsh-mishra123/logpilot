from collections import deque, Counter
from datetime import datetime, timedelta
import math
from typing import List, Dict, Any

class PatternBreakDetector:
    """Detects unusual log patterns using message entropy"""
    
    def __init__(self, window_minutes: int = 5, entropy_threshold: float = 2.0):
        self.window_minutes = window_minutes
        self.entropy_threshold = entropy_threshold
        
        # Store message patterns for current window
        self.messages = deque(maxlen=10000)  # Max messages in window
        self.last_entropy = 0.0
    
    def add_message(self, message: str):
        """Add a log message to the pattern window"""
        # Normalize message (remove variable parts like IDs, timestamps)
        normalized = self._normalize_message(message)
        self.messages.append(normalized)
    
    def _normalize_message(self, message: str) -> str:
        """Normalize log message by replacing variable parts"""
        import re
        # Replace IDs, numbers, IPs, etc.
        normalized = re.sub(r'\b\d+\b', 'X', message)  # Numbers
        normalized = re.sub(r'\b[0-9a-f]{8,}\b', 'HASH', normalized)  # Hashes
        normalized = re.sub(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', 'IP', normalized)  # IPs
        return normalized
    
    def _calculate_entropy(self, messages: List[str]) -> float:
        """Calculate entropy of message patterns"""
        if not messages:
            return 0.0
        
        counter = Counter(messages)
        total = len(messages)
        
        entropy = 0.0
        for count in counter.values():
            probability = count / total
            entropy -= probability * math.log2(probability)
        
        return entropy
    
    def detect(self) -> Dict[str, Any]:
        """Detect pattern breaks using entropy changes"""
        if len(self.messages) < 10:
            return {"detected": False, "entropy": 0.0}
        
        current_entropy = self._calculate_entropy(list(self.messages))
        
        # Detect break if entropy is unusually high or low compared to baseline
        # For simplicity, we use a threshold
        detected = current_entropy > self.entropy_threshold or (
            self.last_entropy > 0 and abs(current_entropy - self.last_entropy) > 1.0
        )
        
        # Store entropy for next detection
        self.last_entropy = current_entropy
        
        # Calculate severity
        severity = min(100, (current_entropy / self.entropy_threshold) * 100)
        
        return {
            "detected": detected,
            "entropy": current_entropy,
            "severity_score": severity,
            "message_count": len(self.messages),
            "unique_patterns": len(Counter(self.messages)),
            "description": f"Pattern break detected: entropy {current_entropy:.2f} (threshold: {self.entropy_threshold:.2f})"
        }