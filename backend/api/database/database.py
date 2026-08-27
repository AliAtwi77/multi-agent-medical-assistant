from sqlalchemy import create_engine
from backend.config.settings import SQLITE_DB_PATH
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from contextlib import contextmanager


engine= create_engine(
    f"sqlite:///{SQLITE_DB_PATH}",
    connect_args={"check_same_thread": False},
)

SessionLocal= sessionmaker(bind=engine, autocommit=False, autoflush=False)

class Base(DeclarativeBase):
    pass

def init_db():
    from backend.api.models import db_models
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db_session():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db():
    """FastAPI dependency."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()