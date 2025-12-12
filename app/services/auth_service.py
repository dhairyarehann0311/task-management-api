from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models.enums import UserRole
from app.models.user import User
from app.repositories.user_repo import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession):
        self.users = UserRepository(db)

    async def register(self, *, email: str, password: str, role: UserRole, full_name: str | None) -> User:
        existing = await self.users.get_by_email(email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        user = User(email=email, password_hash=hash_password(password), role=role, full_name=full_name)
        await self.users.create(user)
        return user

    async def authenticate(self, *, email: str, password: str) -> str:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        return create_access_token(subject=str(user.id), role=user.role.value)
