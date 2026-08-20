from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

# Local SQLite DB file for Step 2.8 persistence.
DEFAULT_DB_URL = f"sqlite:///{Path(__file__).resolve().parents[2] / 'characters.db'}"


def create_engine_for_url(db_url: str = DEFAULT_DB_URL) -> Engine:
    return create_engine(db_url, future=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False, class_=Session)
