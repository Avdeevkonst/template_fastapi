from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import RefreshToken, check_authenticate
from src.crud import create_personal_model, create_user_model
from src.schemas import Credentials, RefreshTokenSchema, Register, UserView
from src.storage import get_async_session
from src.utils import UserRole

router = APIRouter(prefix="/register")


@router.post("/registration", status_code=status.HTTP_201_CREATED)
async def registration_user(
    db: Annotated[AsyncSession, Depends(get_async_session)], body: Register
):
    user = await create_user_model(db, body)
    personal = await create_personal_model(db, body, user["id"])
    await db.commit()
    schema = {**user, **personal}
    del schema["password"]
    return UserView(**schema)


@router.post("/login", status_code=status.HTTP_201_CREATED)
async def create_token(
    db: Annotated[AsyncSession, Depends(get_async_session)],
    credentials: Credentials,
):
    return await check_authenticate(db, credentials)


@router.post("/refresh-token", status_code=status.HTTP_201_CREATED)
async def refresh_token(token: RefreshTokenSchema):
    return RefreshToken(token=token.token, role=UserRole.noone).create_token()
