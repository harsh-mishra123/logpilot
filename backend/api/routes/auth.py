"""
Auth routes: register and login.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext

from ...database.init_db import get_db
from ...database.crud import get_user_by_email, create_user, create_team
from ...auth.middleware import create_access_token

router = APIRouter()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str = ""
    team_name: str = "My Team"


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new user and create their team."""
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Create team first
    team = await create_team(db, body.team_name)

    # Hash password and create user
    hashed_pw = pwd_context.hash(body.password)
    user = await create_user(db, body.email, hashed_pw, body.full_name, team.id)

    # Mark user as owner
    user.is_owner = True
    await db.commit()

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Login with email + password, return JWT."""
    user = await get_user_by_email(db, body.email)
    if not user or not pwd_context.verify(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token({"sub": user.id})
    return TokenResponse(access_token=token)
