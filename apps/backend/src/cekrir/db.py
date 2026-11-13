from pathlib import Path

from sqlalchemy.engine import Engine, make_url
from sqlmodel import create_engine


def build_engine(database_url: str) -> Engine:
    url = make_url(database_url)
    if url.drivername == "sqlite":
        if url.database and url.database != ":memory:":
            Path(url.database).parent.mkdir(parents=True, exist_ok=True)
        return create_engine(database_url, connect_args={"check_same_thread": False})
    return create_engine(database_url, pool_pre_ping=True)
