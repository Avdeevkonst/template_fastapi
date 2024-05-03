import datetime
import re
from typing import Annotated

from email_validator import EmailNotValidError, validate_email
from fastapi import HTTPException, status
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator,
)

from src.enums import UserRole


class UserView(BaseModel):
    id: int
    username: str
    creation_date: datetime.datetime
    modified_date: datetime.datetime | None
    is_active: bool
    is_superuser: bool
    phone: str
    email: str


class Me(BaseModel):
    pass


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


class CreateJwt(BaseModel):
    id: str
    role: str
    email: str
    is_superuser: bool


class RefreshTokenSchema(BaseModel):
    token: str


class ChangePassword(Credentials):
    new_password: str


class UpdateProfile(BaseModel):
    phone: Annotated[str | None, Field(validate_default=True)]
    email: Annotated[str | None, Field(validate_default=True)]

    @field_validator("email")
    @classmethod
    def valid_email(cls, email: str | None) -> str | None:
        if email is None:
            return email
        try:
            emailinfo = validate_email(email, check_deliverability=False)
            return emailinfo.normalized
        except EmailNotValidError as e:
            raise ValueError(
                f"Unexpected value {e!r}, expected format is 'mail@.x'"
            ) from e

    @field_validator("phone")
    @classmethod
    def valid_phone(cls, phone: str | None) -> str | None:
        if phone is None:
            return phone
        pattern = r"^(\+)[1-9][0-9\-\(\)\.]{9,15}$"
        if re.match(pattern, phone):
            return phone
        raise ValueError(
            f"Unexpected value {phone!r}, expected format is +79005001010"
        )


class Register(UpdateProfile):
    username: str
    password: str
    role: UserRole = UserRole.user


class MailSchema(BaseModel):
    recipients: list[str]
    body: str
    subject: str


class BaseMessage(BaseModel):
    text: str | None
    photo: str | None
    sender_id: int
    receiver_id: int

    @model_validator(mode="after")
    def check_passwords_match(self):
        text = self.text
        photo = self.photo
        if text is not None and photo is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="required any of photo or text",
            )
        return self


class IdField(BaseModel):
    id: int


class DeleteMessage(IdField):
    pass


class UpdateMessage(DeleteMessage):
    text: str


class CreateMessage(BaseMessage):
    pass


class WSMessageRequest(BaseModel):
    message: UpdateMessage | CreateMessage | DeleteMessage

    class Config:
        from_attributes = True


class ResponseMessage(IdField, BaseMessage):
    created_at: datetime.datetime


class AddContact(IdField):
    to_add: int
