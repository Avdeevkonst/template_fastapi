from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Annotated, Optional, Union

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.requests import HTTPConnection
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.crud import get_personal_model, get_user_model
from src.enums import UserRole
from src.models import User
from src.schemas import CreateJwt, Credentials
from src.storage import get_async_session
from src.utils import verify_password

access_token_expires = timedelta(minutes=30)

refresh_token_expires = timedelta(minutes=180)


@dataclass(slots=True, frozen=True)
class Token:
    token: str
    role: Union[UserRole, list[UserRole]]
    key: str = settings.SECRET_KEY
    algorithms: str = settings.ALGORITHMS

    def _decode(self) -> dict[str, str]:
        try:
            token = jwt.decode(
                self.token, key=self.key, algorithms=[self.algorithms]
            )
            return dict(token)
        except jwt.PyJWTError as exp_err:
            raise HTTPException(
                detail=exp_err.args,
                status_code=status.HTTP_401_UNAUTHORIZED,
            ) from exp_err

    def _has_access(self) -> bool:
        if isinstance(self.role, list):
            return self._decode().get("role", None) in [
                i.value for i in self.role
            ]
        else:
            return self._decode().get("role", None) == self.role.value

    def _not_access(self) -> bool:
        if isinstance(self.role, list):
            return self._decode().get("role", None) not in [
                i.value for i in self.role
            ]
        else:
            return self._decode().get("role", None) != self.role.value

    def check_permission(
        self,
        *,
        exclude: bool,
    ) -> None:
        if exclude:
            access_token = self._not_access()
        else:
            access_token = self._has_access()
        if not access_token:
            raise HTTPException(
                detail="Permission denied",
                status_code=status.HTTP_403_FORBIDDEN,
            )

    def user_id(self) -> int:
        user_id = self._decode().get("id", None)
        if user_id:
            return int(user_id)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must have key id",
        )

    def user_role(self) -> str:
        role = self._decode().get("role", None)
        if role:
            return role
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must have key role",
        )

    def user_email(self) -> str:
        email = self._decode().get("email", None)
        if email:
            return email
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Token must have key email",
        )


def _get_token_from_request(request: HTTPConnection) -> str:
    if not request.headers.get("Authorization", None):
        raise HTTPException(
            detail="Request must have a Authorization token",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    token = request.headers["Authorization"].split(" ")
    if token[0] != "Bearer":
        raise HTTPException(
            detail="Предоставлен не Bearer токен",
            status_code=status.HTTP_401_UNAUTHORIZED,
        )
    if len(token) == 2:
        return token[1]
    raise HTTPException(
        detail="Invalid basic header. Credentials string should not contain spaces.",
        status_code=status.HTTP_401_UNAUTHORIZED,
    )


async def get_user_from_request(
    request: HTTPConnection,
    db: Annotated[AsyncSession, Depends(get_async_session)],
) -> User:
    token = _get_token_from_request(request)
    token = Token(token, [UserRole.user, UserRole.administrator])
    token.check_permission(exclude=False)
    user_id = token.user_id()
    return await get_user_model(db, user_id)


def create_token(
    user: Optional[CreateJwt | None] = None,
    expires_delta: timedelta | None = None,
    user_id: Optional[str | None] = None,
    user_role: Optional[UserRole | None] = None,
    user_email: Optional[str | None] = None,
    is_superuser: Optional[bool] = False,
) -> str:
    if expires_delta:
        expire = datetime.now(UTC) + expires_delta
    else:
        expire = datetime.now(UTC) + timedelta(minutes=15)
    data = {}
    data["exp"] = expire

    if isinstance(user, CreateJwt):
        data["is_superuser"] = user.is_superuser
        data["id"] = user.id
        data["role"] = user.role
        data["email"] = user.email

    elif user_id and user_role:
        data["is_superuser"] = is_superuser
        data["id"] = user_id
        data["role"] = user_role.value
        data["email"] = user_email
    else:
        raise ValueError("Unexpected value, use Userschema or explicit values")
    return jwt.encode(data, settings.SECRET_KEY, algorithm=settings.ALGORITHMS)


async def check_credentials(
    db: AsyncSession, credentials: Credentials
) -> User:
    user = await get_user_model(db, credentials.username)
    if verify_password(credentials.password, user.password):
        return user
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Wrong password",
    )


async def check_authenticate(
    db: AsyncSession,
    credentials: Credentials,
):
    user = await check_credentials(db, credentials)
    email = await get_personal_model(db, user.id)

    payload = CreateJwt(
        id=str(user.id),
        role=str(user.role),
        is_superuser=user.is_superuser,
        email=email["email"],
    )
    access_token = create_token(payload, expires_delta=access_token_expires)

    refresh_token = create_token(payload, expires_delta=refresh_token_expires)
    return {
        "access": access_token,
        "refresh": refresh_token,
    }


@dataclass(frozen=True, slots=True)
class RefreshToken(Token):
    token: str
    role: UserRole | list[UserRole]

    def create_token(self):
        payload = self._decode()
        if (
            payload.get("id", None)
            and payload.get("role", None)
            and "is_superuser" in payload
        ):
            user_id = payload["id"]
            role = payload["role"]
            is_superuser = bool(payload["is_superuser"])
            access_token = create_token(
                user_id=user_id,
                user_role=UserRole[role],
                is_superuser=is_superuser,
                expires_delta=access_token_expires,
            )
            refresh_token = create_token(
                user_id=user_id,
                user_role=UserRole[role],
                is_superuser=is_superuser,
                expires_delta=refresh_token_expires,
            )
            return {
                "access": access_token,
                "refresh": refresh_token,
            }
        else:
            raise ValueError("Unexpected decryption result")
