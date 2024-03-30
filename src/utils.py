import re
import secrets
from enum import Enum
from typing import Never

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.exc import SQLAlchemyError

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def generate_random_credential(length: int) -> str:
    return secrets.token_hex(length // 2)


def verify_password(plain_password: str, hashed_password: bytes | str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


def handle_error(error: SQLAlchemyError) -> Never:
    msg = convert_sqlachemy_exception(error)
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=msg,
    )


def convert_sqlachemy_exception(error: SQLAlchemyError):
    detail = repr(error).partition("DETAIL")[-1]
    pattern = r"[^a-zA-Zа-яА-Я@\s+=.]"
    cleaned_string = re.sub(pattern, "", detail)
    return cleaned_string.strip()


class UserRole(Enum):
    user = "user"
    administrator = "admin"
    noone = ""
