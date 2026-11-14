"""Structural validation and row bounding for untrusted generated SQL."""
import sqlglot
from sqlglot import exp
from app.config import MAX_ROWS


class UnsafeQuery(ValueError):
    """Raised when a generated SQL statement violates read-only policy."""


FORBIDDEN_EXPRESSIONS = (
    exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter,
    exp.Command, exp.Copy, exp.Transaction, exp.Pragma, exp.Attach,
)
ALLOWED_ROOTS = (exp.Select, exp.Union, exp.Intersect, exp.Except)


def validate_sql(sql: str) -> str:
    """Allow one read-only SELECT statement and enforce the configured maximum LIMIT."""
    if not sql or not sql.strip():
        raise UnsafeQuery("SQL query is empty.")
    try:
        parsed = sqlglot.parse(sql, read="postgres")
    except sqlglot.errors.ParseError as exc:
        raise UnsafeQuery(f"SQL syntax could not be parsed: {exc}") from exc

    if len(parsed) != 1 or parsed[0] is None:
        raise UnsafeQuery("Only one SQL statement is allowed.")

    tree = parsed[0]
    if not isinstance(tree, ALLOWED_ROOTS):
        raise UnsafeQuery("Only read-only SELECT queries are permitted.")
    if any(tree.find(kind) is not None for kind in FORBIDDEN_EXPRESSIONS):
        raise UnsafeQuery("The query contains a blocked operation.")
    if tree.args.get("into") is not None or tree.args.get("locks"):
        raise UnsafeQuery("SELECT INTO and locking clauses are not permitted.")

    limit = tree.args.get("limit")
    if limit is None:
        tree = tree.limit(MAX_ROWS)
    else:
        try:
            requested = int(limit.expression.this)
        except (AttributeError, TypeError, ValueError):
            raise UnsafeQuery("LIMIT must be a fixed integer.")
        if requested < 0:
            raise UnsafeQuery("LIMIT cannot be negative.")
        if requested > MAX_ROWS:
            tree = tree.limit(MAX_ROWS)

    return tree.sql(dialect="postgres")
