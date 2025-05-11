import uuid
from datetime import datetime
from typing import Final

from sqlalchemy import DateTime, String
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column

DESCRIPTION_LENGTH: Final = 400
NAME_LENGTH: Final = 100
STRING_LENGTH: Final = 255


class Base(AsyncAttrs, DeclarativeBase):
    """
    Base class for all models.
    """

    ...


class TimestampMixin:
    """
    Mixin for timestamp fields.
    """

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.now)

    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)


class PrimaryKeyUUID:
    """
    Mixin for primary key UUID field.
    """

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)


class CommonData:
    """
    Mixin for name and description fields.
    """

    name: Mapped[str] = mapped_column(String(length=NAME_LENGTH), nullable=False, unique=True)
    description: Mapped[str] = mapped_column(String(length=DESCRIPTION_LENGTH), nullable=True)


class General(Base, PrimaryKeyUUID, TimestampMixin):
    """
    Abstract base class for all models.
    """

    __abstract__ = True

    @declared_attr  # pyright: ignore[reportArgumentType]
    @classmethod
    def __tablename__(cls):
        return cls.__name__.lower()
