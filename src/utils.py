import re
import secrets
from typing import NoReturn

from fastapi import (
    HTTPException,
    status,
)
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_random_credential(length: int) -> str:
    return secrets.token_hex(length // 2)


def verify_password(plain_password: str, hashed_password: bytes | str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def handle_error(error: SQLAlchemyError) -> NoReturn:
    msg = convert_sqlachemy_exception(error)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=msg,
    )


def convert_sqlachemy_exception(error: SQLAlchemyError):
    if "DETAIL" in repr(error):
        detail = repr(error).partition("DETAIL")[-1]
    else:
        detail = repr(error)
    pattern = r"[^a-zA-Zа-яА-Я@\s+=.]"
    cleaned_string = re.sub(pattern, "", detail)
    return cleaned_string.strip()


def remove_private_data(
    payload: dict, *, to_another_user: bool = False
) -> None:
    if to_another_user:
        del payload["phone"]
        del payload["email"]
        del payload["role"]
        del payload["is_active"]
        del payload["is_superuser"]
        del payload["password"]
    else:
        del payload["password"]
