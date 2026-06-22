from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Any
import json
import logging
from datetime import datetime

from .manager import manager
from ..database.crud import validate_api_key, save_log_entry, save_anomaly, create_incident
from ..database.init_db import get_db
from ..statistics.engine import StatisticsEngine
from ..statistics.models import AnomalyDetectionResult
import asyncio

logger = logging.getLogger(__name__)

# Global statistics engine
stats_engine = StatisticsEngine()

async def handle_agent_connection(websocket: WebSocket, token: str):
    """
    Handle WebSocket connection from CLI agent
    """
    # Validate API key
    async for db in get_db():
        team_id = await validate_api_key(db, token)
        if not team_id:
            await websocket.close(code=4001, reason="Invalid API key")
            return
        break
    
    # Accept connection
    await manager.connect_agent(websocket, team_id)
    
    try:
        while True:
            # Receive messages from agent
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "log":
                # Process log message
                await handle_log_message(team_id, message.get("data", {}))
            elif message.get("type") == "batch":
                # Process batch of logs
                for log in message.get("data", []):
                    await handle_log_message(team_id, log)
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, team_id)
        logger.info(f"Agent disconnected for team {team_id}")
    except Exception as e:
        logger.error(f"Error in agent handler: {e}")
        manager.disconnect(websocket, team_id)

async def handle_dashboard_connection(websocket: WebSocket, token: str):
    """
    Handle WebSocket connection from dashboard
    """
    # Validate JWT token (simplified - we'll implement proper JWT later)
    # For now, just accept
    # TODO: Implement proper JWT validation
    
    # For demo, use a hardcoded team
    team_id = "demo-team-id"  # This should come from JWT
    
    await manager.connect_dashboard(websocket, team_id)
    
    try:
        while True:
            # Dashboard clients might send ping messages or commands
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, team_id)
        logger.info(f"Dashboard disconnected for team {team_id}")
    except Exception as e:
        logger.error(f"Error in dashboard handler: {e}")
        manager.disconnect(websocket, team_id)

async def handle_log_message(team_id: str, log_data: Dict[str, Any]):
    """
    Process a log message: save to DB, run statistics, broadcast
    """
    try:
        # 1. Save log entry to database
        async for db in get_db():
            log_entry = await save_log_entry(db, team_id, log_data)
            break
        
        # 2. Run statistics engine
        anomalies = await stats_engine.process_log(team_id, log_data)
        
        # 3. Process detected anomalies
        for anomaly_result in anomalies:
            await handle_detected_anomaly(team_id, anomaly_result, log_entry.id)
        
        # 4. Broadcast log to dashboards
        await manager.broadcast_log(team_id, log_data)
        
    except Exception as e:
        logger.error(f"Error processing log: {e}")

async def handle_detected_anomaly(team_id: str, anomaly_result: AnomalyDetectionResult, log_entry_id: str):
    """
    Handle a detected anomaly: save to DB, create incident if needed, broadcast
    """
    try:
        # Save anomaly to database
        anomaly_data = {
            "team_id": team_id,
            "log_entry_id": log_entry_id,
            "anomaly_type": anomaly_result.anomaly_type.value,
            "severity_score": anomaly_result.severity_score,
            "description": anomaly_result.description,
            "context": anomaly_result.context
        }
        
        async for db in get_db():
            anomaly = await save_anomaly(db, anomaly_data)
            break
        
        # If severity is high, create an incident
        if anomaly_result.severity_score > 70:
            async for db in get_db():
                incident = await create_incident(
                    db,
                    team_id,
                    title=f"Critical: {anomaly_result.anomaly_type.value}",
                    severity="high",
                    description=anomaly_result.description,
                    anomalies=[anomaly.id]
                )
                # Broadcast incident
                await manager.broadcast_incident(team_id, {
                    "id": incident.id,
                    "title": incident.title,
                    "description": incident.description,
                    "severity": incident.severity,
                    "status": incident.status,
                    "started_at": incident.started_at.isoformat()
                })
                break
        
        # Broadcast anomaly
        await manager.broadcast_anomaly(team_id, {
            "id": anomaly.id,
            "type": anomaly_result.anomaly_type.value,
            "severity_score": anomaly_result.severity_score,
            "description": anomaly_result.description,
            "detected_at": datetime.utcnow().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error handling anomaly: {e}")