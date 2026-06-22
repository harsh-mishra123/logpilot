from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import List

from ...database.init_db import get_db
from ...database.crud import create_team, get_team_by_id, create_api_key
from ...auth.middleware import get_current_user

router = APIRouter()

class TeamCreate(BaseModel):
    name: str

class TeamResponse(BaseModel):
    id: str
    name: str
    subscription_status: str
    seats_limit: int

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str  # This is the raw key - only shown once

@router.post("/")
async def create_new_team(
    team_data: TeamCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new team (owner only)"""
    # Only allow if user doesn't have a team yet
    if current_user.team_id:
        raise HTTPException(status_code=400, detail="User already belongs to a team")
    
    team = await create_team(db, team_data.name)
    return TeamResponse(
        id=team.id,
        name=team.name,
        subscription_status=team.subscription_status,
        seats_limit=team.seats_limit
    )

@router.post("/{team_id}/api-keys")
async def generate_api_key(
    team_id: str,
    name: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Generate a new API key for CLI agents"""
    if current_user.team_id != team_id or not current_user.is_owner:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    api_key, raw_key = await create_api_key(db, team_id, name)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=raw_key  # Only shown once!
    )