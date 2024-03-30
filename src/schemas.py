import datetime
import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from pydantic import BaseModel, Field, field_validator

from src.utils import UserRole


class Register(BaseModel):
    username: str
    password: str
    role: UserRole = UserRole.user

    phone: Annotated[str, Field(validate_default=True)]
    email: Annotated[str, Field(validate_default=True)]

    @field_validator("email")
    @classmethod
    def valid_email(cls, email: str) -> str:
        try:
            emailinfo = validate_email(email, check_deliverability=False)
            return emailinfo.normalized
        except EmailNotValidError as e:
            raise ValueError(
                f"Unexpected value {e!r}, expected format is 'mail@.x'"
            ) from e

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, phone: str) -> str:
        pattern = r"^(\+)[1-9][0-9\-\(\)\.]{9,15}$"
        if re.match(pattern, phone):
            return phone
        raise ValueError(
            f"Unexpected value {phone!r}, expected format is +79005001010"
        )


class UserView(BaseModel):
    id: int
    username: str
    created_at: datetime.datetime
    is_active: bool
    is_superuser: bool
    phone: str
    email: str


class Credentials(BaseModel):
    username: str
    password: str


class UserSchema(BaseModel):
    id: int
    username: str
    password: str
    role: UserRole
    created_at: datetime.datetime
    is_active: bool
    is_superuser: bool


class RefreshTokenSchema(BaseModel):
    token: str
