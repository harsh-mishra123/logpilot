from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import asyncio
from collections import defaultdict

from .models import LogStats, AnomalyDetectionResult, AnomalyType
from .detectors.error_spike import ErrorSpikeDetector
from .detectors.latency_creep import LatencyCreepDetector
from .detectors.memory_leak import MemoryLeakDetector
from .detectors.pattern_break import PatternBreakDetector

class StatisticsEngine:
    """
    Main statistics engine that orchestrates all detectors
    and maintains state per team
    """
    
    def __init__(self):
        # Per-team state
        self.team_stats = defaultdict(lambda: {
            "error_spike": ErrorSpikeDetector(),
            "latency_creep": LatencyCreepDetector(),
            "memory_leak": MemoryLeakDetector(),
            "pattern_break": PatternBreakDetector(),
            "minute_counter": 0,
            "minute_errors": 0,
            "minute_total": 0,
            "minute_logs": [],
            "last_minute_reset": datetime.utcnow()
        })
    
    async def process_log(self, team_id: str, log_entry: Dict[str, Any]) -> List[AnomalyDetectionResult]:
        """
        Process a single log entry through all detectors
        Returns list of detected anomalies
        """
        anomalies = []
        state = self.team_stats[team_id]
        
        # Extract relevant data from log
        severity = log_entry.get('severity', 'INFO')
        message = log_entry.get('message', '')
        parsed_data = log_entry.get('parsed_data', {})
        
        # Update minute counters for error spike detection
        state["minute_total"] += 1
        if severity in ['ERROR', 'CRITICAL']:
            state["minute_errors"] += 1
        
        state["minute_logs"].append(message)
        
        # Update latency detector if response_time is present
        if 'response_time' in parsed_data:
            state["latency_creep"].add_point(
                datetime.fromisoformat(log_entry['timestamp']),
                parsed_data['response_time']
            )
        
        # Update memory detector if memory_usage is present
        if 'memory_usage' in parsed_data:
            state["memory_leak"].add_point(
                datetime.fromisoformat(log_entry['timestamp']),
                parsed_data['memory_usage']
            )
        
        # Update pattern break detector
        state["pattern_break"].add_message(message)
        
        # Check if we need to reset minute counters (every minute)
        now = datetime.utcnow()
        if (now - state["last_minute_reset"]).total_seconds() >= 60:
            # Run detectors on accumulated data
            anomalies.extend(self._run_minute_detection(team_id, state))
            
            # Reset minute counters
            state["minute_counter"] = 0
            state["minute_errors"] = 0
            state["minute_total"] = 0
            state["minute_logs"] = []
            state["last_minute_reset"] = now
        
        return anomalies
    
    def _run_minute_detection(self, team_id: str, state: Dict) -> List[AnomalyDetectionResult]:
        """Run all detectors on accumulated minute data"""
        anomalies = []
        
        # Error spike detection
        if state["minute_total"] > 0:
            error_result = state["error_spike"].detect(
                state["minute_errors"],
                state["minute_total"]
            )
            if error_result["detected"]:
                anomalies.append(AnomalyDetectionResult(
                    anomaly_type=AnomalyType.ERROR_SPIKE,
                    detected=True,
                    severity_score=error_result["severity_score"],
                    description=error_result["description"],
                    context=error_result
                ))
            
            # Update baseline for error spike detector
            state["error_spike"].update_baseline(
                state["minute_errors"],
                state["minute_total"]
            )
        
        # Latency creep detection (only if we have data)
        if len(state["latency_creep"].data_points) > 10:
            latency_result = state["latency_creep"].detect()
            if latency_result["detected"]:
                anomalies.append(AnomalyDetectionResult(
                    anomaly_type=AnomalyType.LATENCY_CREEP,
                    detected=True,
                    severity_score=latency_result["severity_score"],
                    description=latency_result["description"],
                    context=latency_result
                ))
        
        # Memory leak detection
        if len(state["memory_leak"].data_points) > 20:
            memory_result = state["memory_leak"].detect()
            if memory_result["detected"]:
                anomalies.append(AnomalyDetectionResult(
                    anomaly_type=AnomalyType.MEMORY_LEAK,
                    detected=True,
                    severity_score=memory_result["severity_score"],
                    description=memory_result["description"],
                    context=memory_result
                ))
        
        # Pattern break detection
        if len(state["pattern_break"].messages) > 10:
            pattern_result = state["pattern_break"].detect()
            if pattern_result["detected"]:
                anomalies.append(AnomalyDetectionResult(
                    anomaly_type=AnomalyType.PATTERN_BREAK,
                    detected=True,
                    severity_score=pattern_result["severity_score"],
                    description=pattern_result["description"],
                    context=pattern_result
                ))
        
        return anomalies