from __future__ import annotations

from pydantic import EmailStr, Field

from app.models.enums import UserRole
from app.schemas.common import APIModel


class UserCreate(APIModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.MEMBER
    full_name: str | None = None


class UserOut(APIModel):
    id: int
    email: EmailStr
    role: UserRole
    full_name: str | None = None


class TokenOut(APIModel):
    access_token: str
    token_type: str = "bearer"
