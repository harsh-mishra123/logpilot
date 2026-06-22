from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum

class AnomalyType(str, Enum):
    ERROR_SPIKE = "error_spike"
    LATENCY_CREEP = "latency_creep"
    MEMORY_LEAK = "memory_leak"
    PATTERN_BREAK = "pattern_break"

@dataclass
class LogStats:
    """Container for statistics computed from logs"""
    team_id: str
    timestamp: datetime
    
    # Error stats
    error_count: int = 0
    total_count: int = 0
    error_rate: float = 0.0
    
    # Latency stats (if parsing response times)
    latencies: Optional[List[float]] = field(default=None)
    
    # Memory stats (if parsing memory usage)
    memory_values: Optional[List[float]] = field(default=None)
    
    # Pattern stats
    unique_messages: int = 0
    total_messages: int = 0
    entropy: float = 0.0

@dataclass
class AnomalyDetectionResult:
    anomaly_type: AnomalyType
    detected: bool
    severity_score: float  # 0-100
    description: str
    context: Dict[str, Any]
    log_entry_id: Optional[str] = None