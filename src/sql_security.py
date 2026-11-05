"""SQLite AST ve gerçek şema üzerinden SELECT doğrulaması."""
import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError, ErrorLevel
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope
from src.schema import ALLOWED_TABLES

# SQLite authorizer da bu listeyi uygular. Yan etkili/uzantı fonksiyonları kapalı.
ALLOWED_FUNCTIONS = frozenset({
    "sum", "avg", "count", "min", "max", "total", "round", "abs", "coalesce", "ifnull", "nullif",
    "strftime", "date", "datetime", "julianday", "unixepoch", "time", "substr", "substring",
    "lower", "upper", "length", "trim", "ltrim", "rtrim", "replace", "like", "glob", "printf",
    "row_number", "rank", "dense_rank", "lag", "lead", "first_value", "last_value", "nth_value",
})


class SQLSecurityError(ValueError):
    pass


def validate_sql(sql: str, schema: dict) -> str:
    if not isinstance(sql, str) or not sql.strip() or len(sql) > 50000:
        raise SQLSecurityError("SQL boş veya izin verilen uzunluğu aşıyor.")
    try:
        # Parser yorumları token olarak ayırır; string sabitlerine dokunulmaz.
        statements = [s for s in sqlglot.parse(sql, read="sqlite", error_level=ErrorLevel.RAISE) if s is not None]
        if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union, exp.Intersect, exp.Except)):
            raise SQLSecurityError("Yalnızca tek SELECT sorgusu kabul edilir.")
        tree = statements[0]
        forbidden = {"insert", "update", "delete", "drop", "alter", "create", "attach", "detach", "pragma", "command", "into", "transaction", "commit", "rollback", "copy", "merge", "grant", "revoke", "use", "set", "execute", "load_data"}
        for node in tree.walk():
            if node.key in forbidden:
                raise SQLSecurityError("Yan etkili SQL ifadesi yasak.")
            node.comments = None
            if isinstance(node, exp.Table):
                if node.db or node.catalog or not isinstance(node.this, exp.Identifier):
                    raise SQLSecurityError("Nitelikli tablo veya tablo fonksiyonu yasak.")
            if isinstance(node, exp.Anonymous) and node.name.lower() not in ALLOWED_FUNCTIONS:
                raise SQLSecurityError("İzin verilmeyen SQL fonksiyonu.")
            if isinstance(node, exp.With) and node.args.get("recursive"):
                raise SQLSecurityError("Recursive CTE bu PoC kapsamında kapalı.")
        allowed = {t.lower() for t in ALLOWED_TABLES}
        for scope in traverse_scope(tree):
            for source in scope.sources.values():
                if isinstance(source, exp.Table) and source.name.lower() not in allowed:
                    raise SQLSecurityError("İzin verilmeyen tablo erişimi.")
        typed_schema = {t: {c["name"]: c["type"] for c in info["columns"]} for t, info in schema.items() if t in ALLOWED_TABLES}
        qualify(tree.copy(), dialect="sqlite", schema=typed_schema, validate_qualify_columns=True)
        # Parser'ın ürettiği yorumdan arındırılmış SQL yürütülür; ham metin yürütülmez.
        return tree.sql(dialect="sqlite", comments=False)
    except SQLSecurityError:
        raise
    except (SqlglotError, ValueError, TypeError, RecursionError) as error:
        raise SQLSecurityError("SQL ayrıştırılamadı veya sütun/alias şemayla uyuşmuyor.") from None
