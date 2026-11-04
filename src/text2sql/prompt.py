"""Schema-aware prompt builder and table-description retrieval.

Retrieval is keyword-based and deterministic: a table is included
if any of its description keywords appear in the question, or if
the question mentions revenue/orders (which always need orders).
This is the "retrieval" step whose addition is measured in the
evaluator's iteration 2.
"""
import re

from .schema import SCHEMA, TABLE_DESCRIPTIONS

KEYWORDS = {
    "customers": ["customer", "client", "region", "segment", "signup", "top customer"],
    "products": ["product", "category", "electronics", "furniture", "clothing", "price"],
    "orders": ["revenue", "order", "sale", "amount", "monthly", "total", "average", "count"],
}


def retrieve_tables(question):
    q = question.lower()
    chosen = []
    for table, words in KEYWORDS.items():
        if any(w in q for w in words):
            chosen.append(table)
    if "orders" not in chosen and any(w in q for w in ["revenue", "order", "sale"]):
        chosen.append("orders")
    if not chosen:
        chosen = ["orders"]
    # Preserve schema order.
    return [t for t in SCHEMA if t in chosen]


def build_prompt(question, tables=None):
    if tables is None:
        tables = retrieve_tables(question)
    lines = [
        "You are a text-to-SQL assistant. Write a single SQLite SELECT query.",
        "Use only the tables and columns below. Do not invent tables or columns.",
        "",
    ]
    for t in tables:
        lines.append(f"Table {t}: {TABLE_DESCRIPTIONS[t]}")
        lines.append(f"  Columns: {', '.join(SCHEMA[t])}")
    lines += ["", f"Question: {question}", "SQL:"]
    return "\n".join(lines)
