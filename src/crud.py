from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
    NoResultFound,
    SQLAlchemyError,
)
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import Personal, User
from src.schemas import Register
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
