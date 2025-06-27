"""This module configures the async SQLAlchemy database engine and session for the API.

The module initializes the asynchronous database engine with settings drawn from
the application configuration and a sessionmaker for handling database sessions. It
supports database connection pooling and echoing of SQL statements for debugging.
"""

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from api.core.config import settings

engine = create_async_engine(
    settings.SQLALCHEMY_DATABASE_URI,
    echo=settings.DB_ECHO_LOG,
    echo_pool=settings.DB_ECHO_LOG,
    pool_size=20,
    future=True,
)
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False, future=True
)
