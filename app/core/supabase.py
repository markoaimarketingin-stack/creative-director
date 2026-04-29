from contextlib import contextmanager

from psycopg2.pool import SimpleConnectionPool

from app.core.config import Settings


class DatabasePool:
    def __init__(self, settings: Settings) -> None:
        self._dsn = settings.supabase_url
        self._pool: SimpleConnectionPool | None = None
        if self._dsn and self._dsn.startswith("postgresql://"):
            self._pool = SimpleConnectionPool(
                minconn=settings.db_pool_min_size,
                maxconn=settings.db_pool_max_size,
                dsn=self._dsn,
            )

    @property
    def enabled(self) -> bool:
        return self._pool is not None

    @contextmanager
    def connection(self):
        if not self._pool:
            yield None
            return

        conn = self._pool.getconn()
        conn.autocommit = False
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            self._pool.putconn(conn)

    def close(self) -> None:
        if self._pool:
            self._pool.closeall()
            self._pool = None
