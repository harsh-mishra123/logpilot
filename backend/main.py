from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import asyncio
import logging

from .config import settings
from .database.init_db import init_db
from .websocket.handlers import handle_agent_connection, handle_dashboard_connection
from .websocket.manager import manager
from .api.routes import logs, incidents, teams, auth

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup/shutdown"""
    # Startup
    logger.info("Starting LogPilot Backend...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Start WebSocket heartbeat
    asyncio.create_task(manager.send_heartbeat())
    logger.info("WebSocket heartbeat started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down LogPilot Backend...")

# Create FastAPI app
app = FastAPI(
    title="LogPilot API",
    description="Real-time log anomaly detection with WebSocket-powered dashboard",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# WebSocket endpoints
@app.websocket("/ws/agent")
async def websocket_agent_endpoint(websocket: WebSocket):
    """WebSocket endpoint for CLI agents"""
    # Get token from query parameter
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    await handle_agent_connection(websocket, token)

@app.websocket("/ws/dashboard")
async def websocket_dashboard_endpoint(websocket: WebSocket):
    """WebSocket endpoint for dashboard clients"""
    # Get token from query parameter (JWT)
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return
    
    await handle_dashboard_connection(websocket, token)

# REST API routes
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(logs.router, prefix="/api/logs", tags=["logs"])
app.include_router(incidents.router, prefix="/api/incidents", tags=["incidents"])
app.include_router(teams.router, prefix="/api/teams", tags=["teams"])

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "logpilot-backend"}

# Root endpoint
@app.get("/")
async def root():
    return {
        "service": "LogPilot Backend",
        "version": "1.0.0",
        "docs": "/docs",
        "websocket_endpoints": {
            "agent": "ws://host/ws/agent?token=API_KEY",
            "dashboard": "ws://host/ws/dashboard?token=JWT_TOKEN"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )