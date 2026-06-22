from collections import deque
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Any

class LatencyCreepDetector:
    """Detects gradual latency increases using linear regression"""
    
    def __init__(self, window_minutes: int = 10, slope_threshold: float = 0.1):
        self.window_minutes = window_minutes
        self.slope_threshold = slope_threshold
        
        # Store (timestamp, latency) pairs
        self.data_points = deque(maxlen=window_minutes * 60)  # Assuming one per second
    
    def add_point(self, timestamp: datetime, latency: float):
        """Add a new latency measurement"""
        self.data_points.append((timestamp.timestamp(), latency))
    
    def detect(self) -> Dict[str, Any]:
        """Detect if latency is trending upward"""
        if len(self.data_points) < 10:  # Need minimum data
            return {"detected": False, "slope": 0.0}
        
        # Extract x (time) and y (latency)
        x = np.array([p[0] for p in self.data_points])
        y = np.array([p[1] for p in self.data_points])
        
        # Normalize x to avoid numerical issues
        x_norm = (x - x[0]) / 60.0  # Convert seconds to minutes
        
        # Perform linear regression
        n = len(x_norm)
        slope, intercept = np.polyfit(x_norm, y, 1)
        
        # Calculate correlation
        correlation = np.corrcoef(x_norm, y)[0, 1] if n > 1 else 0
        
        # Detect if slope is positive and significant
        detected = slope > self.slope_threshold and correlation > 0.6
        
        # Calculate severity based on slope magnitude
        severity = min(100, max(0, (slope / (self.slope_threshold * 3)) * 100))
        
        # Predict next value
        last_time = x_norm[-1]
        next_time = last_time + 1  # One minute ahead
        predicted_next = slope * next_time + intercept
        current_value = slope * last_time + intercept
        percent_increase = ((predicted_next - current_value) / max(current_value, 0.001)) * 100
        
        return {
            "detected": detected,
            "slope": slope,
            "intercept": intercept,
            "correlation": correlation,
            "severity_score": severity,
            "percent_increase": percent_increase,
            "description": f"Latency creep detected: {percent_increase:.1f}% increase per minute (slope: {slope:.2f}ms/min)"
        }