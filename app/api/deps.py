import jwt, uuid

# fastapi
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

# SQLALCHEMY
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# app
from app.models.user import User
from app.core.security import decode_token
from app.core.db import get_db


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
        token: str = Depends(oauth2_scheme), 
        db: AsyncSession = Depends(get_db)
    ) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="인증 정보가 올바르지 않습니다.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_token(token)

        if payload.get("type") != "access":
            raise credentials_exception

        sub = payload.get("sub")
        if not sub:
            raise credentials_exception

        user_id = uuid.UUID(str(sub))

    except (jwt.PyJWTError, ValueError):
        raise credentials_exception

    result = await db.execute(select(User).where(User.id==user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise credentials_exception

    return user