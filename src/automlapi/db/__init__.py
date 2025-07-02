import logging
from typing import Generator

from azure.identity import DefaultAzureCredential
from sqlalchemy import create_engine, text
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from ..config import settings

# Configure logging
logger = logging.getLogger(__name__)

# Database models base
Base = declarative_base()


class DatabaseManager:
    """Manages Azure SQL Database connections with Azure Default Credential"""

    def __init__(self):
        self.credential = DefaultAzureCredential()
        self._engine = None
        self._session_local = None

    def get_engine(self):
        """Get SQLAlchemy engine with Azure Default Credential authentication"""
        if self._engine is None:
            database_url = settings.database_url

            # Configure engine for Azure SQL Database
            connect_args = {
                "autocommit": False,
                "timeout": 30,
                "login_timeout": 30,
            }

            self._engine = create_engine(
                database_url,
                poolclass=QueuePool,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=3600,  # 1 hour for Azure SQL
                echo=False,
                connect_args=connect_args,
            )

            # Test connection
            try:
                with self._engine.connect() as conn:
                    conn.execute(text("SELECT 1 as test"))
                    logger.info(
                        f"Database connection established successfully to {settings.sql_server}"
                    )
            except Exception as e:
                logger.error(f"Database connection failed: {e}")
                logger.error(
                    f"Connection string (masked): mssql+pyodbc://@{settings.sql_server}:1433/{settings.sql_database}"
                )
                raise

        return self._engine

    def get_session_local(self):
        """Get SQLAlchemy session factory"""
        if self._session_local is None:
            self._session_local = sessionmaker(
                bind=self.get_engine(),
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_local


# Global database manager instance
db_manager = DatabaseManager()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for database sessions"""
    SessionLocal = db_manager.get_session_local()
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    try:
        engine = db_manager.get_engine()
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
