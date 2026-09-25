from collections.abc import Callable

import psycopg

DatabaseCheck = Callable[[], bool]


def postgres_check(database_url: str, timeout_seconds: int = 2) -> DatabaseCheck:
    def check() -> bool:
        try:
            with psycopg.connect(database_url, connect_timeout=timeout_seconds) as conn:
                conn.execute("SELECT 1")
            return True
        except psycopg.Error:
            return False

    return check
