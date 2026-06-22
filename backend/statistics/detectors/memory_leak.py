from collections import deque
from datetime import datetime, timedelta
import numpy as np
from typing import List, Dict, Any

class MemoryLeakDetector:
    """Detects memory leaks through consistent upward trend"""
    
    def __init__(self, window_minutes: int = 30, correlation_threshold: float = 0.7):
        self.window_minutes = window_minutes
        self.correlation_threshold = correlation_threshold
        
        self.data_points = deque(maxlen=window_minutes * 6)  # One per 10 seconds
    
    def add_point(self, timestamp: datetime, memory_usage: float):
        """Add a new memory measurement"""
        self.data_points.append((timestamp.timestamp(), memory_usage))
    
    def detect(self) -> Dict[str, Any]:
        """Detect if memory usage shows a consistent increasing trend"""
        if len(self.data_points) < 20:
            return {"detected": False, "slope": 0.0}
        
        x = np.array([p[0] for p in self.data_points])
        y = np.array([p[1] for p in self.data_points])
        
        # Normalize time to minutes
        x_norm = (x - x[0]) / 60.0
        
        # Linear regression
        n = len(x_norm)
        slope, intercept = np.polyfit(x_norm, y, 1)
        correlation = np.corrcoef(x_norm, y)[0, 1] if n > 1 else 0
        
        # Check for consistent upward trend (positive slope, high correlation)
        detected = slope > 0.01 and correlation > self.correlation_threshold
        
        # Calculate severity (0-100) based on slope and correlation
        severity = min(100, max(0, (correlation * 100)))
        
        # Calculate memory increase
        start_memory = y[0]
        end_memory = y[-1]
        total_increase = ((end_memory - start_memory) / max(start_memory, 0.001)) * 100
        
        return {
            "detected": detected,
            "slope": slope,
            "correlation": correlation,
            "severity_score": severity,
            "total_increase": total_increase,
            "description": f"Memory leak detected: {total_increase:.1f}% increase over {len(self.data_points)} samples (correlation: {correlation:.2f})"
        }