from sqlalchemy import select, update
from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.exception import SchemaError
from src.models import Personal, User
from src.schemas import ChangePassword, Credentials, Register, UserSchema
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


async def get_user_model(db: AsyncSession, user_param: int | str):
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
        await db.rollback()
        handle_error(e)
    return user.__dict__


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
            .values(username=payload.username, password=payload.new_password)
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
