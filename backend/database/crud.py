from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func, and_
from sqlalchemy.sql import text
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import uuid
import hashlib
import secrets

from .models import User, Team, APIKey, LogEntry, Anomaly, Incident

# --- User CRUD ---
async def create_user(db: AsyncSession, email: str, hashed_password: str, full_name: str, team_id: str):
    user = User(
        email=email,
        hashed_password=hashed_password,
        full_name=full_name,
        team_id=team_id
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str):
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

# --- Team CRUD ---
async def create_team(db: AsyncSession, name: str):
    team = Team(name=name)
    db.add(team)
    await db.commit()
    await db.refresh(team)
    return team

async def get_team_by_id(db: AsyncSession, team_id: str):
    result = await db.execute(select(Team).where(Team.id == team_id))
    return result.scalar_one_or_none()

# --- API Key CRUD ---
async def create_api_key(db: AsyncSession, team_id: str, name: str):
    # Generate a secure API key
    raw_key = secrets.token_urlsafe(32)
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    
    api_key = APIKey(
        key=hashed_key,
        team_id=team_id,
        name=name
    )
    db.add(api_key)
    await db.commit()
    await db.refresh(api_key)
    return api_key, raw_key  # Return both the stored hash and raw key for display

async def validate_api_key(db: AsyncSession, raw_key: str):
    hashed_key = hashlib.sha256(raw_key.encode()).hexdigest()
    result = await db.execute(
        select(APIKey).where(
            and_(
                APIKey.key == hashed_key,
                APIKey.is_active == True
            )
        )
    )
    api_key = result.scalar_one_or_none()
    if api_key:
        # Update last_used_at
        api_key.last_used_at = datetime.utcnow()
        await db.commit()
        return api_key.team_id
    return None

# --- Log Entry CRUD ---
async def save_log_entry(db: AsyncSession, team_id: str, log_data: Dict[str, Any]):
    log_entry = LogEntry(
        team_id=team_id,
        source=log_data.get('source'),
        timestamp=datetime.fromisoformat(log_data.get('timestamp', datetime.utcnow().isoformat())),
        severity=log_data.get('severity', 'INFO'),
        message=log_data.get('message'),
        raw_log=log_data.get('raw_log'),
        parsed_data=log_data.get('parsed_data', {})
    )
    db.add(log_entry)
    await db.commit()
    await db.refresh(log_entry)
    return log_entry

async def get_recent_logs(
    db: AsyncSession, 
    team_id: str, 
    limit: int = 100,
    severity: Optional[str] = None,
    start_time: Optional[datetime] = None
):
    query = select(LogEntry).where(LogEntry.team_id == team_id)
    
    if severity:
        query = query.where(LogEntry.severity == severity)
    if start_time:
        query = query.where(LogEntry.timestamp >= start_time)
    
    query = query.order_by(desc(LogEntry.timestamp)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

# --- Anomaly CRUD ---
async def save_anomaly(db: AsyncSession, anomaly_data: Dict[str, Any]):
    anomaly = Anomaly(
        team_id=anomaly_data['team_id'],
        log_entry_id=anomaly_data.get('log_entry_id'),
        anomaly_type=anomaly_data['anomaly_type'],
        severity_score=anomaly_data.get('severity_score', 50.0),
        description=anomaly_data.get('description'),
        context=anomaly_data.get('context', {})
    )
    db.add(anomaly)
    await db.commit()
    await db.refresh(anomaly)
    return anomaly

async def get_anomalies(
    db: AsyncSession,
    team_id: str,
    limit: int = 50,
    resolved: Optional[bool] = None
):
    query = select(Anomaly).where(Anomaly.team_id == team_id)
    
    if resolved is not None:
        query = query.where(Anomaly.is_resolved == resolved)
    
    query = query.order_by(desc(Anomaly.detected_at)).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()

# --- Incident CRUD ---
async def create_incident(
    db: AsyncSession,
    team_id: str,
    title: str,
    severity: str,
    description: str = "",
    anomalies: List[str] = None
):
    incident = Incident(
        team_id=team_id,
        title=title,
        description=description,
        severity=severity,
        started_at=datetime.utcnow(),
        status="open"
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)
    
    # Link anomalies to incident
    if anomalies:
        for anomaly_id in anomalies:
            result = await db.execute(select(Anomaly).where(Anomaly.id == anomaly_id))
            anomaly = result.scalar_one_or_none()
            if anomaly:
                anomaly.incident_id = incident.id
                anomaly.is_resolved = True
        await db.commit()
    
    return incident

async def resolve_incident(db: AsyncSession, incident_id: str):
    result = await db.execute(select(Incident).where(Incident.id == incident_id))
    incident = result.scalar_one_or_none()
    if incident:
        incident.status = "resolved"
        incident.resolved_at = datetime.utcnow()
        
        # Resolve all linked anomalies
        for anomaly in incident.anomalies:
            anomaly.is_resolved = True
            anomaly.resolved_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(incident)
    return incident