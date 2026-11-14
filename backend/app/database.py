from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Any

from .security import Principal
from .settings import settings

try:  # Docker installs psycopg from requirements; this fallback keeps static/API preview inspectable.
    from psycopg import Connection
    from psycopg.rows import dict_row
    from psycopg_pool import ConnectionPool
except ImportError:  # pragma: no cover - environment-specific fallback
    Connection = Any  # type: ignore[misc,assignment]
    dict_row = None
    ConnectionPool = None  # type: ignore[assignment,misc]


class DatabaseHub:
    def __init__(self) -> None:
        self._pools: dict[str, Any] = {}
        self._pool_errors: dict[str, str] = {}
        self._driver_error: str | None = None

    def open(self) -> None:
        if self._pools:
            return
        if ConnectionPool is None:
            self._driver_error = "psycopg is not installed; install backend/requirements.txt"
            return
        # Initialize each pool independently. One unavailable database must not
        # prevent the other four domains from reporting their own health status.
        for name, url in settings.database_urls.items():
            try:
                self._pools[name] = ConnectionPool(
                    conninfo=url,
                    min_size=0,
                    max_size=5,
                    timeout=4,
                    kwargs={"row_factory": dict_row, "autocommit": False},
                    open=True,
                )
            except Exception as exc:  # noqa: BLE001 - preserve partial service availability
                self._pool_errors[name] = type(exc).__name__

    def close(self) -> None:
        for pool in self._pools.values():
            pool.close()
        self._pools.clear()
        self._pool_errors.clear()

    def check(self) -> dict[str, str]:
        results: dict[str, str] = {}
        if ConnectionPool is None:
            return {name: "unavailable: database driver not installed" for name in settings.database_urls}
        for name, pool in self._pools.items():
            try:
                with pool.connection() as conn:
                    conn.execute("SELECT 1").fetchone()
                results[name] = "connected"
            except Exception as exc:  # noqa: BLE001 - health endpoint reports every database separately
                results[name] = f"unavailable: {type(exc).__name__}"
        for missing in set(settings.database_urls) - set(self._pools):
            if missing in self._pool_errors:
                results[missing] = f"unavailable: pool initialization failed ({self._pool_errors[missing]})"
            else:
                results[missing] = "not initialized"
        return results

    @contextmanager
    def user_connection(self, domain: str, principal: Principal) -> Iterator[Connection]:
        if ConnectionPool is None:
            raise RuntimeError("psycopg is not installed; install backend/requirements.txt")
        if domain not in self._pools:
            raise RuntimeError(f"Database pool for {domain} is not initialized")
        pool = self._pools[domain]
        with pool.connection() as conn:
            with conn.transaction():
                conn.execute("SELECT set_config('mishkat.user_id', %s, true)", (str(principal.user_id),))
                yield conn


db_hub = DatabaseHub()
