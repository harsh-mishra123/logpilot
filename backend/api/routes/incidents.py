from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from ...database.init_db import get_db
from ...database.crud import get_anomalies, resolve_incident, create_incident
from ...auth.middleware import get_current_user

router = APIRouter()

class IncidentCreate(BaseModel):
    title: str
    severity: str
    description: str = ""
    anomaly_ids: List[str] = []

class IncidentResponse(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    started_at: datetime
    resolved_at: Optional[datetime]

@router.get("/")
async def get_incidents(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all incidents for the current team"""
    # Implementation
    return {"incidents": []}

@router.post("/")
async def create_new_incident(
    incident: IncidentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new incident manually"""
    new_incident = await create_incident(
        db,
        current_user.team_id,
        incident.title,
        incident.severity,
        incident.description,
        incident.anomaly_ids
    )
    
    return IncidentResponse(
        id=new_incident.id,
        title=new_incident.title,
        severity=new_incident.severity,
        status=new_incident.status,
        started_at=new_incident.started_at,
        resolved_at=new_incident.resolved_at
    )

@router.post("/{incident_id}/resolve")
async def resolve_incident_endpoint(
    incident_id: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Resolve an incident"""
    incident = await resolve_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    return {"status": "resolved", "incident_id": incident_id}