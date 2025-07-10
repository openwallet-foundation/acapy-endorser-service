"""Database session management module for handling asynchronous database operations.

This module provides a dependency function `get_db` that yields asynchronous database
sessions, ensuring proper error handling by rolling back the session if a database
exception occurs, and committing transactions otherwise.
"""

from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from api.db.session import async_session


async def get_db() -> AsyncSession:
    """Dependency function that yields db sessions."""
    async with async_session() as session:
        try:
            yield session
        except DBAPIError:
            await session.rollback()
            raise
        else:
            await session.commit()
