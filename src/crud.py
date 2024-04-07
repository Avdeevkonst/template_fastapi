from typing import Sequence

from sqlalchemy import delete, select, update
from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.exception import SchemaError
from src.models import Message, Personal, User
from src.schemas import (
    ChangePassword,
    CreateMessage,
    Credentials,
    DeleteMessage,
    Register,
    UpdateMessage,
    UpdateProfile,
    UserSchema,
)
from src.utils import (
    get_password_hash,
    handle_error,
)


async def create_user_model(db: AsyncSession, body: Register):
    password = get_password_hash(body.password)
    stmt = User(
        username=body.username,
        password=password,
        role=body.role,
    )
    db.add(stmt)
    try:
        await db.flush()
    except (SQLAlchemyError, IntegrityError) as e:
        await db.rollback()
        handle_error(e)
    return stmt.__dict__


async def get_user_model(db: AsyncSession, user_param: int | str) -> User:
    if isinstance(user_param, int):
        query = select(User).where(User.id == user_param)
    elif isinstance(user_param, str):
        query = select(User).where(User.username == user_param)
    try:
        found = await db.execute(query)
        user = found.scalar_one()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        handle_error(e)
    return user


async def create_personal_model(
    db: AsyncSession, body: Register, user_id: int
):
    stmt = Personal(
        phone=body.phone,
        email=body.email,
        id=user_id,
    )
    db.add(stmt)
    try:
        await db.flush()
    except (SQLAlchemyError, IntegrityError) as e:
        await db.rollback()
        handle_error(e)
    return stmt.__dict__


async def update_user_model(
    db: AsyncSession,
    payload: UserSchema | ChangePassword,
    user_id: int | None = None,
):
    if isinstance(payload, Credentials) and user_id:
        query = (
            update(User)
            .values(password=payload.new_password)
            .where(User.id == user_id)
        ).returning(User)
    elif isinstance(payload, UserSchema):
        query = (
            update(User)
            .values(payload.model_dump())
            .where(User.id == payload.id)
        ).returning(User)
    else:
        raise SchemaError(
            f"Unexpected schema type, use UserSchema or Credentials, instead {payload.__class__.__name__}"
        )
    try:
        response = await db.execute(query)
        user = response.scalar_one()
        await db.commit()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        await db.rollback()
        handle_error(e)
    return user.__dict__


async def get_personal_model(db: AsyncSession, user_id: int):
    query = select(Personal).where(Personal.id == user_id)
    try:
        found = await db.execute(query)
        user = found.scalar_one()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        await db.rollback()
        handle_error(e)
    return user.__dict__


async def update_profile_model(
    db: AsyncSession,
    payload: UpdateProfile,
    user_id: int,
):
    values = {}
    if payload.email and payload.phone:
        values = payload.model_dump()
    elif payload.email is None:
        values["phone"] = payload.phone
    elif payload.phone is None:
        values["email"] = payload.email
    query = (
        update(Personal).values(values).where(Personal.id == user_id)
    ).returning(Personal)
    try:
        response = await db.execute(query)
        await db.commit()
        profile = response.scalar_one()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        await db.rollback()
        handle_error(e)
    return profile.__dict__


async def create_message_model(
    db: AsyncSession, body: CreateMessage
) -> Message:
    stmt = Message(
        text=body.text or None,
        photo=body.photo or None,
        sender=body.sender_id,
        receiver=body.receiver_id,
    )
    db.add(stmt)
    try:
        await db.flush()
    except (SQLAlchemyError, IntegrityError) as e:
        await db.rollback()
        handle_error(e)
    return stmt


async def get_messages_model(
    db: AsyncSession, sender_id: int, receiver_id: int
) -> Sequence[Message]:
    query = (
        select(Message)
        .where(Message.sender == sender_id, Message.receiver == receiver_id)
        .order_by(Message.created_at.desc())
    )
    try:
        found = await db.execute(query)
        messages = found.scalars().fetchall()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        handle_error(e)
    return messages


async def delete_message_model(
    db: AsyncSession, message_id: DeleteMessage
) -> None:
    query = delete(Message).where(Message.id == message_id.id)
    try:
        await db.execute(query)
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        handle_error(e)


async def update_message_model(db: AsyncSession, new_message: UpdateMessage):
    query = (
        update(Message)
        .where(Message.id == new_message.id)
        .values(text=new_message.text)
    )
    try:
        response = await db.execute(query)
        await db.commit()
        message = response.scalar_one()
    except (
        NoResultFound,
        SQLAlchemyError,
        IntegrityError,
    ) as e:
        await db.rollback()
        handle_error(e)
    return message
