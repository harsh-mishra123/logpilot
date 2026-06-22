"""
Subscriptions route — Stripe removed.
Returns basic plan/subscription status for the current team.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from ...database.init_db import get_db
from ...database.crud import get_team_by_id
from ...auth.middleware import get_current_user

router = APIRouter()


class PlanResponse(BaseModel):
    team_id: str
    subscription_status: str
    seats_limit: int


@router.get("/plan")
async def get_plan(
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    """Return the current team's subscription / plan status."""
    team = await get_team_by_id(db, current_user.team_id)
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return PlanResponse(
        team_id=team.id,
        subscription_status=team.subscription_status,
        seats_limit=team.seats_limit,
    )