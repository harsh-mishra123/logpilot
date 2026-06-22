from statistics import mean, stdev
from collections import deque
from datetime import datetime, timedelta
import math
from typing import List, Dict, Any

class ErrorSpikeDetector:
    """Detects sudden spikes in error rates using z-score"""
    
    def __init__(self, window_seconds: int = 60, baseline_minutes: int = 60, z_threshold: float = 3.0):
        self.window_seconds = window_seconds
        self.baseline_minutes = baseline_minutes
        self.z_threshold = z_threshold
        
        # Sliding windows for baseline
        self.error_counts = deque(maxlen=baseline_minutes)  # One per minute
        self.total_counts = deque(maxlen=baseline_minutes)
    
    def update_baseline(self, errors: int, total: int):
        """Update baseline with a new minute of data"""
        self.error_counts.append(errors)
        self.total_counts.append(total)
    
    def detect(self, errors: int, total: int) -> Dict[str, Any]:
        """Detect if current error rate is an anomaly"""
        if len(self.error_counts) < 5:  # Need minimum baseline
            return {"detected": False, "z_score": 0.0}
        
        # Calculate error rates for baseline
        error_rates = [
            e / max(t, 1) * 100 
            for e, t in zip(self.error_counts, self.total_counts)
        ]
        
        # Current error rate
        current_rate = errors / max(total, 1) * 100
        
        # Calculate z-score
        baseline_mean = mean(error_rates)
        baseline_std = stdev(error_rates) if len(error_rates) > 1 else 1.0
        
        # Avoid division by zero
        if baseline_std < 0.001:
            z_score = 0.0
        else:
            z_score = (current_rate - baseline_mean) / baseline_std
        
        # Detect anomaly
        detected = z_score > self.z_threshold
        
        # Calculate severity (0-100)
        severity = min(100, max(0, (z_score / (self.z_threshold * 2)) * 100))
        
        return {
            "detected": detected,
            "z_score": z_score,
            "current_rate": current_rate,
            "baseline_mean": baseline_mean,
            "baseline_std": baseline_std,
            "severity_score": severity,
            "description": f"Error rate spike detected: {current_rate:.2f}% (z-score: {z_score:.2f})"
        }