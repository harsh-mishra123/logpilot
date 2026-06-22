from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from typing import Optional, List
from pydantic import BaseModel

from ...database.init_db import get_db
from ...database.crud import get_recent_logs
from ...auth.middleware import get_current_user

router = APIRouter()

class LogResponse(BaseModel):
    id: str
    source: Optional[str]
    timestamp: datetime
    severity: str
    message: str
    parsed_data: Optional[dict]

@router.get("/")
async def get_logs(
    limit: int = Query(100, ge=1, le=1000),
    severity: Optional[str] = None,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get recent logs for the current user's team"""
    start_time = datetime.utcnow() - timedelta(hours=hours)
    
    logs = await get_recent_logs(
        db,
        current_user.team_id,
        limit=limit,
        severity=severity,
        start_time=start_time
    )
    
    return [
        LogResponse(
            id=log.id,
            source=log.source,
            timestamp=log.timestamp,
            severity=log.severity,
            message=log.message,
            parsed_data=log.parsed_data
        )
        for log in logs
    ]