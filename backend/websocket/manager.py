from typing import Dict, Set, Optional
from fastapi import WebSocket
import json
import asyncio
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class ConnectionManager:
    """
    Manages WebSocket connections for both CLI agents and dashboards
    """
    
    def __init__(self):
        # CLI agent connections: team_id -> set of websockets
        self.agent_connections: Dict[str, Set[WebSocket]] = {}
        # Dashboard connections: team_id -> set of websockets
        self.dashboard_connections: Dict[str, Set[WebSocket]] = {}
        # All connections for broadcasting
        self.active_connections: Set[WebSocket] = set()
    
    async def connect_agent(self, websocket: WebSocket, team_id: str):
        """Connect a CLI agent"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if team_id not in self.agent_connections:
            self.agent_connections[team_id] = set()
        self.agent_connections[team_id].add(websocket)
        
        logger.info(f"CLI agent connected for team {team_id}")
    
    async def connect_dashboard(self, websocket: WebSocket, team_id: str):
        """Connect a dashboard client"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        if team_id not in self.dashboard_connections:
            self.dashboard_connections[team_id] = set()
        self.dashboard_connections[team_id].add(websocket)
        
        logger.info(f"Dashboard connected for team {team_id}")
    
    def disconnect(self, websocket: WebSocket, team_id: str = None):
        """Disconnect a websocket"""
        self.active_connections.discard(websocket)
        
        # Remove from agent connections
        for connections in self.agent_connections.values():
            connections.discard(websocket)
        
        # Remove from dashboard connections
        for connections in self.dashboard_connections.values():
            connections.discard(websocket)
        
        logger.info(f"WebSocket disconnected for team {team_id}")
    
    async def send_to_team(self, team_id: str, message: dict, include_agents: bool = True, include_dashboards: bool = True):
        """Send a message to all connections for a specific team"""
        message_json = json.dumps(message)
        
        # Send to agents
        if include_agents and team_id in self.agent_connections:
            for websocket in self.agent_connections[team_id]:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending to agent: {e}")
                    self.disconnect(websocket, team_id)
        
        # Send to dashboards
        if include_dashboards and team_id in self.dashboard_connections:
            for websocket in self.dashboard_connections[team_id]:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending to dashboard: {e}")
                    self.disconnect(websocket, team_id)
    
    async def broadcast_log(self, team_id: str, log_entry: dict):
        """Broadcast a log entry to all dashboards for a team"""
        await self.send_to_team(
            team_id,
            {
                "type": "log",
                "data": log_entry,
                "timestamp": datetime.utcnow().isoformat()
            },
            include_agents=False,
            include_dashboards=True
        )
    
    async def broadcast_anomaly(self, team_id: str, anomaly: dict):
        """Broadcast an anomaly detection to all connected clients"""
        await self.send_to_team(
            team_id,
            {
                "type": "anomaly",
                "data": anomaly,
                "timestamp": datetime.utcnow().isoformat()
            },
            include_agents=True,
            include_dashboards=True
        )
    
    async def broadcast_incident(self, team_id: str, incident: dict):
        """Broadcast an incident creation to all dashboards"""
        await self.send_to_team(
            team_id,
            {
                "type": "incident",
                "data": incident,
                "timestamp": datetime.utcnow().isoformat()
            },
            include_agents=False,
            include_dashboards=True
        )
    
    async def send_heartbeat(self):
        """Send periodic heartbeats to all connections"""
        while True:
            await asyncio.sleep(30)
            heartbeat = {
                "type": "heartbeat",
                "timestamp": datetime.utcnow().isoformat()
            }
            for websocket in self.active_connections:
                try:
                    await websocket.send_text(json.dumps(heartbeat))
                except:
                    pass

# Global manager instance
manager = ConnectionManager()