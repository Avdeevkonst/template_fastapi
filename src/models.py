from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.storage import Base


class User(Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    username: Mapped[str] = mapped_column(
        String(20), index=True, unique=True, nullable=False
    )
    password: Mapped[str] = mapped_column(String(1024), nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    is_active: Mapped[bool] = mapped_column(default=True)
    is_superuser: Mapped[bool] = mapped_column(default=False)

    personal_data: Mapped["Personal"] = relationship(back_populates="user")


class Personal(Base):
    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(default=datetime.now(UTC))
    phone: Mapped[str] = mapped_column(String(12), nullable=False)
    email: Mapped[str] = mapped_column(String, nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"))

    parent: Mapped["User"] = relationship(
        back_populates="user", single_parent=True
    )

    __table_args__ = (UniqueConstraint("user_id"),)
