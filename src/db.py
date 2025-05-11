import typing as tp
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from types import TracebackType
from uuid import UUID

import sqlalchemy as sa
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.models import Base, PrimaryKeyUUID
from src.t_utils import handle_error

ModelType = tp.TypeVar("ModelType", bound=Base)


class NotCreatedSessionError(NotImplementedError):
    """Raised when trying to use a session that hasn't been created."""


class DatabaseConfig:
    """Database configuration and connection management."""

    def __init__(self, db_url_postgresql: str) -> None:
        """Initialize database configuration.

        Args:
            db_url_postgresql: PostgreSQL connection URL
        """
        self.db_url_postgresql = db_url_postgresql

    @property
    def engine(self):
        """Create and return SQLAlchemy async engine instance."""
        return create_async_engine(
            self.db_url_postgresql,
            echo=True,
            poolclass=NullPool,
        )

    @property
    def async_session_maker(self):
        """Create and return async session factory."""
        return async_sessionmaker(
            self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


class IUnitOfWorkBase(ABC):
    """Base interface for Unit of Work pattern implementation."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):  # noqa: ANN001
        await self.rollback()

    @abstractmethod
    async def commit(self) -> None:
        """Commit the current transaction."""
        raise NotImplementedError

    @abstractmethod
    async def close(self) -> None:
        """Close the current session."""
        raise NotImplementedError

    @abstractmethod
    async def rollback(self) -> None:
        """Rollback the current transaction."""
        raise NotImplementedError


class PgUnitOfWork(IUnitOfWorkBase):
    """PostgreSQL Unit of Work implementation."""

    def __init__(self, db_url_postgresql: str) -> None:
        """Initialize PostgreSQL Unit of Work."""
        self._session_factory = DatabaseConfig(db_url_postgresql).async_session_maker
        self._async_session: AsyncSession | None = None

    def activate(self) -> None:
        """Activate the session if not already active."""
        if not isinstance(self._async_session, AsyncSession):
            self._async_session = self._session_factory()

    async def __aenter__(self):
        """Enter the context manager and activate the session."""
        self.activate()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """Exit the context manager and handle any exceptions.

        Args:
            exc_type: Exception type if an exception was raised
            exc_val: Exception value if an exception was raised
            exc_tb: Exception traceback if an exception was raised
        """
        if exc_type is not None:
            await self.rollback()
        else:
            await self.commit()

        await self.close()
        if isinstance(exc_val, HTTPException):
            raise exc_val
        else:
            handle_error(exc_type, exc_val, exc_tb)

    async def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._async_session is None:
            raise NotCreatedSessionError

        await self._async_session.rollback()

    async def close(self) -> None:
        """Close the current session."""
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.close()

    async def commit(self) -> None:
        """Commit the current transaction."""
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.commit()

    async def flush(self) -> None:
        """Flush the current session."""
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.flush()

    async def refresh(self, instance: type[ModelType]) -> None:
        """Refresh the instance from the database.

        Args:
            instance: The instance to refresh
        """
        if self._async_session is None:
            raise NotCreatedSessionError
        await self._async_session.refresh(instance)

    async def execute(self, statement: sa.Executable, *args: tp.Any):
        """Execute a SQL statement.

        Args:
            statement: The SQL statement to execute
            *args: Additional arguments for the statement

        Returns:
            The result of the statement execution
        """
        if self._async_session is None:
            raise NotCreatedSessionError
        return await self._async_session.execute(statement, *args)

    def add(self, instance: object) -> None:
        """Add an instance to the session.

        Args:
            instance: The instance to add
        """
        if self._async_session is None:
            raise NotCreatedSessionError
        self._async_session.add(instance)


class Query(tp.Generic[ModelType]):
    """Generic query builder for database operations."""

    def __init__(self, model: type[ModelType]) -> None:
        """Initialize query builder.

        Args:
            model: The model class to build queries for
        """
        self.model = model
        self.conditions: list[sa.ColumnExpressionArgument] = []

    def insert(self, body: dict | BaseModel) -> sa.Insert:
        """Create an insert statement.

        Args:
            body: The data to insert

        Returns:
            An insert statement
        """
        if isinstance(body, BaseModel):
            body = body.model_dump()
        return sa.insert(self.model).values(**body).returning(self.model)

    def update(self, *condition: sa.ColumnExpressionArgument, body: dict | BaseModel) -> sa.Update:
        """Create an update statement.

        Args:
            *condition: The conditions for the update
            body: The data to update

        Returns:
            An update statement
        """
        if isinstance(body, BaseModel):
            body = body.model_dump()
        return sa.update(self.model).values(**body).where(*condition).returning(self.model)

    def delete(self, *condition: sa.ColumnExpressionArgument) -> sa.Delete:
        """Create a delete statement.

        Args:
            *condition: The conditions for the delete

        Returns:
            A delete statement
        """
        return sa.delete(self.model).where(*condition)

    def select(self, *condition: sa.ColumnExpressionArgument) -> sa.Select:
        """Create a select statement.

        Args:
            *condition: The conditions for the select

        Returns:
            A select statement
        """
        return sa.select(self.model).where(*condition)

    def make_conditions(self, conditions: BaseModel) -> None:
        """Make conditions for the query by pydantic model fields.

        If the field is not None and the model has the field,
        add the condition to the query.

        Args:
            conditions: The conditions to apply
        """
        # Clear existing conditions
        self.conditions = []
        for key, value in conditions.model_dump().items():
            if value is not None and hasattr(self.model, key):
                column = getattr(self.model, key, None)
                if column is None:
                    continue
                if isinstance(value, Enum):
                    self.conditions.append(tp.cast(sa.String, column) == value.value)
                else:
                    self.conditions.append(column == value)


class Crud(tp.Generic[ModelType], Query[ModelType]):
    def __init__(self, model: type[ModelType], uow: PgUnitOfWork):
        super().__init__(model=model)
        self.uow = uow

    async def create_entity(self, payload: dict | BaseModel) -> ModelType:
        """
        Create an entity.
        """
        if isinstance(payload, BaseModel):
            body = payload.model_dump()
        else:
            body = payload
        body["created_at"] = datetime.now(UTC)

        stmt = self.model(**body)

        self.uow.add(stmt)
        await self.uow.flush()

        return stmt

    async def update_entity(self, payload: dict | BaseModel, conditions: BaseModel) -> ModelType:
        """
        Update an entity.
        """
        if isinstance(payload, BaseModel):
            body = payload.model_dump()
        else:
            body = payload
        body["updated_at"] = datetime.now(UTC)
        self.make_conditions(conditions)

        query = self.update(*self.conditions, body=body)
        result_query = await self.uow.execute(query)
        await self.uow.flush()
        response = result_query.scalar_one()
        return tp.cast("ModelType", response)

    async def delete_entity(self, conditions: BaseModel) -> None:
        """
        Delete an entity.
        """
        self.make_conditions(conditions)
        query = self.delete(*self.conditions)
        await self.uow.execute(query)
        await self.uow.flush()


class CrudEntity(Crud[ModelType]):
    def __init__(self, model: type[ModelType], uow: PgUnitOfWork):
        self.uow = uow
        super().__init__(model=model, uow=uow)

    async def get_entity(self, r_id: UUID) -> ModelType:
        model = tp.cast("type[PrimaryKeyUUID]", self.model)
        conditions = model.id == r_id
        query = self.select(conditions)

        result_query = await self.uow.execute(query)
        response = result_query.scalar_one()
        return tp.cast("ModelType", response)

    async def get_entity_by_conditions(self, conditions: BaseModel) -> ModelType:
        """Get one row by conditions
        :param conditions:
        :return: self.model
        """
        self.make_conditions(conditions)
        query = self.select(*self.conditions)

        result_query = await self.uow.execute(query)
        response = result_query.scalar_one()
        return tp.cast("ModelType", response)

    async def one_or_none(self, conditions: BaseModel) -> ModelType | None:
        """Get one row by conditions if exists else return None
        :param conditions:
        :return: self.model
        """
        self.make_conditions(conditions)
        query = self.select(*self.conditions)

        result_query = await self.uow.execute(query)
        response = result_query.scalar_one_or_none()
        return tp.cast("ModelType | None", response)

    async def get_many(self, conditions: BaseModel) -> list[ModelType]:
        """Get all rows by conditions
        :param conditions:
        :return: list[self.model]
        """
        self.make_conditions(conditions)
        query = self.select(*self.conditions)

        result_query = await self.uow.execute(query)
        response = result_query.scalars().fetchall()
        return tp.cast("list[ModelType]", response)

    async def get_all(self) -> list[ModelType]:
        query = self.select()
        result_query = await self.uow.execute(query)
        response = result_query.scalars().fetchall()
        return tp.cast("list[ModelType]", response)

    async def get_by_query(self, query: sa.Executable) -> list[ModelType]:
        result_query = await self.uow.execute(query)
        response = result_query.scalars().fetchall()
        return tp.cast("list[ModelType]", response)
