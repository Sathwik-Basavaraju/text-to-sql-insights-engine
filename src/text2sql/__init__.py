"""Evaluation-driven text-to-SQL insights engine (offline by default)."""
from .schema import SCHEMA, TABLE_DESCRIPTIONS, get_schema
from .validator import ValidationError, validate_sql
from .generator import generate_sql, generate_sql_v1, generate_sql_v2
from .llm_client import LLMClient
from .cache import QueryCache

__all__ = [
    "SCHEMA",
    "TABLE_DESCRIPTIONS",
    "get_schema",
    "ValidationError",
    "validate_sql",
    "generate_sql",
    "generate_sql_v1",
    "generate_sql_v2",
    "LLMClient",
    "QueryCache",
]
