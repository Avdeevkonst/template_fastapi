from sqlalchemy import CheckConstraint, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.enums import UserRole
from src.managers import manager
from src.mixins import TimestampMixin
from src.storage import Base


class User(Base, TimestampMixin):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    username: Mapped[str] = mapped_column(
        String(20), index=True, unique=True, nullable=False
    )
    password: Mapped[str] = mapped_column(String(1024), nullable=False)

    role: Mapped[Enum] = mapped_column(Enum(UserRole), nullable=False)

    is_active: Mapped[bool] = mapped_column(default=True)

    is_superuser: Mapped[bool] = mapped_column(default=False)

    def is_connected_ws(self):
        return bool(manager.active_connections.get(str(self.id), False))


class Personal(Base, TimestampMixin):
    __tablename__ = "personal"

    id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)

    phone: Mapped[str] = mapped_column(String(12), nullable=False, unique=True)

    email: Mapped[str] = mapped_column(String, nullable=False, unique=True)


class Message(Base, TimestampMixin):
    __tablename__ = "message"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    text: Mapped[str] = mapped_column(Text, nullable=False)

    photo: Mapped[str] = mapped_column(String, nullable=True)

    sender: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)

    chat_id: Mapped[int] = mapped_column(ForeignKey("chat.id"), index=True)

    receiver: Mapped[int] = mapped_column(
        ForeignKey("user.id"), nullable=False
    )

    __table_args__ = (CheckConstraint("NOT(photo IS NULL AND text IS NULL)"),)


class Chat(Base, TimestampMixin):
    __tablename__ = "chat"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)

    contact: Mapped[int] = mapped_column(ForeignKey("user.id"), index=True)
