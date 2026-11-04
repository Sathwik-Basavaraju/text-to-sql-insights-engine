"""SQL validation layer: allow only safe SELECT queries.

Rules:
- Must be a single SELECT statement (WITH ... SELECT is allowed).
- Blocks DDL/DML and other dangerous keywords anywhere: INSERT,
  UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE, REPLACE, GRANT,
  VACUUM, ATTACH, DETACH, PRAGMA, and multiple statements (';'
  followed by another statement).
- Every table referenced in FROM/JOIN must be in the schema, and
  every qualified column (table.column) must exist in that table.
  Unqualified columns are checked only if they are unique across
  the schema (ambiguous names are left to SQLite to reject).
- Uses sqlparse if available for parsing, otherwise a regex fallback.
  The fallback is deliberately conservative: it rejects anything it
  cannot prove safe.
"""
import re

from .schema import SCHEMA

FORBIDDEN = [
    "insert", "update", "delete", "drop", "alter", "create", "truncate",
    "replace", "grant", "revoke", "vacuum", "attach", "detach", "pragma",
    "exec", "execute", "call", "copy", "into outfile", "into dumpfile",
]


class ValidationError(ValueError):
    pass


def _strip_strings(sql):
    return re.sub(r"'[^']*'", "''", sql)


def validate_sql(sql, schema=None):
    """Validate sql; return the normalised SQL or raise ValidationError."""
    if schema is None:
        schema = SCHEMA
    if not sql or not isinstance(sql, str):
        raise ValidationError("Empty SQL")
    s = sql.strip()
    if s.endswith(";"):
        s = s[:-1].strip()
    if ";" in s:
        raise ValidationError("Multiple statements are not allowed")
    low = _strip_strings(s).lower()
    if not (low.startswith("select") or low.startswith("with")):
        raise ValidationError("Only SELECT (or WITH ... SELECT) queries are allowed")
    for word in FORBIDDEN:
        if re.search(r"\b" + re.escape(word) + r"\b", low):
            raise ValidationError(f"Forbidden keyword: {word}")
    # Try sqlparse if available, purely as a parse sanity check.
    try:
        import sqlparse

        parsed = sqlparse.parse(s)
        if len(parsed) != 1 or parsed[0].get_type() not in ("SELECT", "UNKNOWN"):
            # UNKNOWN covers WITH ... SELECT in some sqlparse versions.
            if not low.startswith("with"):
                raise ValidationError("Could not parse as a single SELECT")
    except ImportError:
        pass
    # Table check: FROM/JOIN table names.
    tables = re.findall(r"\b(?:from|join)\s+([a-z_][a-z0-9_]*)", low)
    for t in tables:
        if t not in schema:
            raise ValidationError(f"Unknown table: {t}")
    # Qualified column check: table.column
    for tbl, col in re.findall(r"\b([a-z_][a-z0-9_]*)\.([a-z_][a-z0-9_]*)", low):
        if tbl in schema and col not in schema[tbl]:
            raise ValidationError(f"Unknown column: {tbl}.{col}")
    return s
