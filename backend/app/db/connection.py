"""
Database connection management.
Creates the SQLAlchemy engine and session factory.
Supports SQLite (default) and PostgreSQL via DATABASE_URL.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.core.config import settings
from app.db.models import Base
from app.core.fund_registry import ALL_FUNDS
from app.core.logger import get_logger

logger = get_logger(__name__)

# Create engine with appropriate settings
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
else:
    # PostgreSQL or other databases
    engine = create_engine(
        settings.DATABASE_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )

# Session factory
SessionFactory = sessionmaker(bind=engine)


@contextmanager
def get_session() -> Session:
    """
    Context manager that yields a SQLAlchemy session.
    Automatically commits on success, rolls back on error.

    Usage:
        with get_session() as session:
            session.add(...)
    """
    session = SessionFactory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """
    Create all tables and seed the Entity table with the 8 target funds.
    Safe to call multiple times — uses CREATE IF NOT EXISTS.
    """
    from app.db.models import Entity

    logger.info("Initializing database at: %s", settings.DATABASE_URL)
    Base.metadata.create_all(engine)
    logger.info("All tables created successfully.")

    # Seed entities
    with get_session() as session:
        existing = {e.fund_id for e in session.query(Entity.fund_id).all()}
        seeded = 0
        for fund in ALL_FUNDS:
            if fund.fund_id not in existing:
                session.add(Entity(
                    fund_id=fund.fund_id,
                    fund_name=fund.fund_name,
                    regulatory_type=fund.regulatory_type,
                    category=fund.category,
                ))
                seeded += 1

        if seeded:
            logger.info("Seeded %d new fund entities.", seeded)
        else:
            logger.info("All fund entities already exist.")
