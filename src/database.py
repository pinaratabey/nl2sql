"""Salt-okunur, authorizer ile kısıtlı ve süre/satır limitli SQLite yürütme."""
import math
import sqlite3
from pathlib import Path
from time import perf_counter


def connect_readonly(path: Path) -> sqlite3.Connection:
    path = path.resolve(strict=True)
    return sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)


class QueryError(RuntimeError):
    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type


def execute_query(sql: str, path: Path, timeout_seconds: float = 5, max_rows: int = 500) -> dict:
    from src.schema import ALLOWED_TABLES, inspect_schema
    from src.sql_security import ALLOWED_FUNCTIONS, validate_sql
    if not math.isfinite(timeout_seconds) or timeout_seconds <= 0 or not 1 <= max_rows <= 500:
        raise ValueError("Geçersiz sorgu sınırları.")
    started = perf_counter()
    validated = validate_sql(sql, inspect_schema(path))
    allowed = {t.lower() for t in ALLOWED_TABLES}
    timed_out = False
    def authorize(action, arg1, arg2, database, trigger):
        if action == sqlite3.SQLITE_SELECT:
            return sqlite3.SQLITE_OK
        if action == sqlite3.SQLITE_READ:
            return sqlite3.SQLITE_OK if (database == "main" or (database is None and arg2 == "")) and (arg1 or "").lower() in allowed else sqlite3.SQLITE_DENY
        if action == sqlite3.SQLITE_FUNCTION:
            return sqlite3.SQLITE_OK if (arg2 or "").lower() in ALLOWED_FUNCTIONS else sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_DENY
    connection = connect_readonly(path)
    deadline = perf_counter() + timeout_seconds
    def progress():
        nonlocal timed_out
        timed_out = perf_counter() >= deadline
        return int(timed_out)
    try:
        connection.enable_load_extension(False)
        connection.execute("PRAGMA query_only=ON")
        connection.execute("PRAGMA trusted_schema=OFF")
        connection.execute("PRAGMA busy_timeout=0")
        connection.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 1000000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 50000)
        connection.setlimit(sqlite3.SQLITE_LIMIT_EXPR_DEPTH, 100)
        connection.set_authorizer(authorize)
        connection.set_progress_handler(progress, 100)
        # Dış LIMIT, modelin LIMIT/OFFSET'ini değiştirmez. Bir fazla satır kesilmeyi gösterir.
        bounded = f'SELECT * FROM ({validated}) AS "__bounded_result" LIMIT {max_rows + 1}'
        cursor = connection.execute(bounded)
        rows = cursor.fetchmany(max_rows + 1)
        if perf_counter() >= deadline:
            raise QueryError("query_timeout", "Sorgu süre sınırını aştı.")
        return {"validated_sql": validated, "executed_sql": bounded,
                "columns": [c[0] for c in cursor.description], "rows": [list(r) for r in rows[:max_rows]],
                "row_count": min(len(rows), max_rows), "truncated": len(rows) > max_rows,
                "duration_ms": round((perf_counter()-started)*1000, 2)}
    except sqlite3.Error:
        kind = "query_timeout" if timed_out else "query_error"
        raise QueryError(kind, "Sorgu süre sınırını aştı." if timed_out else "Sorgu çalıştırılamadı veya erişim engellendi.") from None
    finally:
        connection.close()
