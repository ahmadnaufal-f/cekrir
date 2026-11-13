from typing import Any

from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


def build_pool(database_url: str) -> ConnectionPool:
    """Prisma manages DDL; Python only opens pooled PostgreSQL connections."""
    return ConnectionPool(
        database_url,
        min_size=1,
        max_size=10,
        timeout=10,
        open=False,
        kwargs={"autocommit": True, "row_factory": dict_row, "connect_timeout": 5},
        check=ConnectionPool.check_connection,
    )


DatabaseRow = dict[str, Any]
