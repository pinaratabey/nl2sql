"""Güvenilir metadata yoluyla gerçek SQLite şemasını çıkarır; kullanıcı SQL'i almaz."""
from contextlib import closing
from pathlib import Path
from src.database import connect_readonly

ALLOWED_TABLES = frozenset({"Customers", "Products", "Orders", "OrderItems"})


def inspect_schema(path: Path) -> dict:
    result = {}
    with closing(connect_readonly(path)) as connection:
        existing = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        missing = ALLOWED_TABLES - existing
        if missing:
            raise ValueError(f"Eksik tablolar: {sorted(missing)}")
        for table in sorted(ALLOWED_TABLES):
            columns = connection.execute(f'PRAGMA table_info("{table}")').fetchall()
            foreign_keys = connection.execute(f'PRAGMA foreign_key_list("{table}")').fetchall()
            result[table] = {
                "columns": [{"name": c[1], "type": c[2], "not_null": bool(c[3]) or bool(c[5]), "primary_key": bool(c[5])} for c in columns],
                "foreign_keys": [{"column": fk[3], "target_table": fk[2], "target_column": fk[4]} for fk in foreign_keys],
                "row_count": connection.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0],
            }
    return result


def schema_context(path: Path) -> str:
    lines = []
    for table, info in inspect_schema(path).items():
        columns = ", ".join(c["name"] + " " + c["type"] + (" PK" if c["primary_key"] else "") for c in info["columns"])
        lines.append(f"{table}({columns})")
        for fk in info["foreign_keys"]:
            lines.append(f"FK: {table}.{fk['column']} -> {fk['target_table']}.{fk['target_column']}")
    return "\n".join(lines)
