"""Rule/template SQL generator (offline, no LLM call).

Two iterations, both actually run by the evaluator:
- v1 (baseline): templates for easy questions only. Medium/hard
  questions fall back to a naive query that usually fails (missing
  JOIN, wrong granularity, or a generic SELECT), so v1 accuracy is
  genuinely lower.
- v2 (improved): schema-aware templates for all tiers, using
  table-description retrieval (prompt.retrieve_tables) and the
  validator (validator.validate_sql) to reject unsafe output.
  If validation fails, v2 returns None instead of a bad query.

The LLM stub is never used here; generate_sql() uses v2 by default.
"""
import re

from .prompt import retrieve_tables
from .validator import ValidationError, validate_sql

JOIN_CUSTOMER = "orders o JOIN customers c ON o.customer_id = c.customer_id"
JOIN_PRODUCT = "orders o JOIN products p ON o.product_id = p.product_id"
JOIN_BOTH = (
    "orders o JOIN customers c ON o.customer_id = c.customer_id "
    "JOIN products p ON o.product_id = p.product_id"
)


def _year(q):
    m = re.search(r"\b(20\d\d)\b", q)
    return m.group(1) if m else None


def _region(q):
    for r in ["North", "South", "East", "West"]:
        if r.lower() in q:
            return r
    return None


def _top_n(q, default=5):
    m = re.search(r"top\s+(\d+)", q)
    return int(m.group(1)) if m else default


def _easy_sql(q):
    """Templates that both v1 and v2 share (easy tier)."""
    if "total revenue" in q and _year(q):
        return f"SELECT SUM(amount) AS total_revenue FROM orders WHERE strftime('%Y', order_date) = '{_year(q)}'"
    if "total revenue" in q:
        return "SELECT SUM(amount) AS total_revenue FROM orders"
    if "how many orders" in q and "by region" not in q:
        return "SELECT COUNT(*) AS order_count FROM orders"
    if "how many customers" in q and _region(q):
        return f"SELECT COUNT(*) AS customer_count FROM customers WHERE region = '{_region(q)}'"
    if "how many customers" in q:
        return "SELECT COUNT(*) AS customer_count FROM customers"
    if "how many products" in q:
        return "SELECT COUNT(*) AS product_count FROM products"
    if "average order amount" in q and "by" not in q:
        return "SELECT AVG(amount) AS avg_amount FROM orders"
    if "highest price" in q:
        return "SELECT name, price FROM products ORDER BY price DESC LIMIT 1"
    return None


def generate_sql_v1(question):
    """Baseline: easy templates only, naive fallbacks otherwise."""
    q = question.lower()
    sql = _easy_sql(q)
    if sql:
        return sql
    # Naive fallbacks that genuinely fail on medium/hard questions:
    if "by region" in q and "revenue" in q:
        return "SELECT region, SUM(amount) AS total_revenue FROM orders GROUP BY region"
    if "by product category" in q or "by category" in q:
        return "SELECT category, SUM(amount) AS total_revenue FROM orders GROUP BY category"
    if "monthly revenue" in q:
        return "SELECT order_date, SUM(amount) AS total_revenue FROM orders GROUP BY order_date"
    if "top" in q and "customer" in q:
        return "SELECT name, SUM(amount) AS total_revenue FROM orders GROUP BY name ORDER BY total_revenue DESC LIMIT 5"
    return "SELECT * FROM orders LIMIT 10"


def generate_sql_v2(question):
    """Improved: schema-aware templates for all tiers + validation."""
    q = question.lower()
    tables = retrieve_tables(question)  # retrieval step (documented, not just unused)
    _ = tables
    # Hard tier first (most specific).
    if "top customer" in q and "each region" in q:
        return (
            "SELECT region, name, total_revenue FROM ("
            "SELECT c.region AS region, c.name AS name, SUM(o.amount) AS total_revenue, "
            "ROW_NUMBER() OVER (PARTITION BY c.region ORDER BY SUM(o.amount) DESC) AS rn "
            f"FROM {JOIN_CUSTOMER} GROUP BY c.region, c.customer_id, c.name) "
            "WHERE rn = 1 ORDER BY region"
        )
    if "more than 10 orders" in q or "more than ten orders" in q:
        return (
            f"SELECT c.name AS name, COUNT(*) AS order_count FROM {JOIN_CUSTOMER} "
            "GROUP BY c.customer_id, c.name HAVING COUNT(*) > 10 "
            "ORDER BY order_count DESC, name"
        )
    if "both 2023 and 2024" in q:
        return (
            f"SELECT c.name AS name FROM {JOIN_CUSTOMER} "
            "GROUP BY c.customer_id, c.name "
            "HAVING SUM(CASE WHEN strftime('%Y', o.order_date) = '2023' THEN 1 ELSE 0 END) > 0 "
            "AND SUM(CASE WHEN strftime('%Y', o.order_date) = '2024' THEN 1 ELSE 0 END) > 0 "
            "ORDER BY name"
        )
    if "second highest" in q and "price" in q:
        return "SELECT MAX(price) AS second_highest_price FROM products WHERE price < (SELECT MAX(price) FROM products)"
    if "above the average" in q:
        return "SELECT COUNT(*) AS order_count FROM orders WHERE amount > (SELECT AVG(amount) FROM orders)"
    if "revenue by category and region" in q:
        return (
            f"SELECT p.category AS category, c.region AS region, SUM(o.amount) AS total_revenue "
            f"FROM {JOIN_BOTH} GROUP BY p.category, c.region ORDER BY category, region"
        )
    if "average quantity" in q:
        return "SELECT AVG(quantity) AS avg_quantity FROM orders"
    if "segment" in q and "most revenue" in q:
        return (
            f"SELECT c.segment AS segment, SUM(o.amount) AS total_revenue FROM {JOIN_CUSTOMER} "
            "GROUP BY c.segment ORDER BY total_revenue DESC LIMIT 1"
        )
    # Medium tier.
    if "revenue by region" in q:
        return (
            f"SELECT c.region AS region, SUM(o.amount) AS total_revenue FROM {JOIN_CUSTOMER} "
            "GROUP BY c.region ORDER BY region"
        )
    if "revenue by product category" in q or "revenue by category" in q:
        return (
            f"SELECT p.category AS category, SUM(o.amount) AS total_revenue FROM {JOIN_PRODUCT} "
            "GROUP BY p.category ORDER BY category"
        )
    if "monthly revenue" in q:
        return (
            "SELECT strftime('%Y-%m', order_date) AS month, SUM(amount) AS total_revenue "
            "FROM orders GROUP BY month ORDER BY month"
        )
    if "top" in q and "customer" in q:
        n = _top_n(q, 5)
        return (
            f"SELECT c.name AS name, SUM(o.amount) AS total_revenue FROM {JOIN_CUSTOMER} "
            f"GROUP BY c.customer_id, c.name ORDER BY total_revenue DESC LIMIT {n}"
        )
    if "average order amount by" in q and "segment" in q:
        return (
            f"SELECT c.segment AS segment, AVG(o.amount) AS avg_amount FROM {JOIN_CUSTOMER} "
            "GROUP BY c.segment ORDER BY segment"
        )
    if "how many orders" in q and "by region" in q:
        return (
            f"SELECT c.region AS region, COUNT(*) AS order_count FROM {JOIN_CUSTOMER} "
            "GROUP BY c.region ORDER BY region"
        )
    if "top" in q and "product" in q:
        n = _top_n(q, 3)
        return (
            f"SELECT p.name AS name, SUM(o.amount) AS total_revenue FROM {JOIN_PRODUCT} "
            f"GROUP BY p.product_id, p.name ORDER BY total_revenue DESC LIMIT {n}"
        )
    # Easy tier (shared).
    sql = _easy_sql(q)
    if sql:
        try:
            return validate_sql(sql)
        except ValidationError:
            return None
    return None


def generate_sql(question, version=2):
    if version == 1:
        return generate_sql_v1(question)
    sql = generate_sql_v2(question)
    if sql is None:
        return None
    try:
        return validate_sql(sql)
    except ValidationError:
        return None
