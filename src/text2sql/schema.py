"""Schema and table descriptions for the analytics SQLite database.

Tables:
- customers(customer_id, name, region, segment, signup_date)
- products(product_id, name, category, price)
- orders(order_id, customer_id, product_id, order_date, quantity, amount)
  amount = quantity * products.price at order time (stored, not computed).

Table descriptions are used for retrieval: the prompt builder only
includes tables whose description keywords match the question.
"""
import sqlite3
from pathlib import Path

SCHEMA = {
    "customers": ["customer_id", "name", "region", "segment", "signup_date"],
    "products": ["product_id", "name", "category", "price"],
    "orders": ["order_id", "customer_id", "product_id", "order_date", "quantity", "amount"],
}

TABLE_DESCRIPTIONS = {
    "customers": "Customers: one row per customer. Columns: customer_id, name, region (North/South/East/West), segment (Consumer/Corporate/Small Business), signup_date. Use for customer counts, regions, segments, and top customers by joining orders on customer_id.",
    "products": "Products: one row per product. Columns: product_id, name, category (Electronics/Furniture/Clothing), price. Use for product and category revenue by joining orders on product_id.",
    "orders": "Orders: one row per order line. Columns: order_id, customer_id, product_id, order_date (YYYY-MM-DD), quantity, amount (revenue for that line). Use for revenue, counts, monthly trends, and averages. Join customers on customer_id and products on product_id when names/regions/categories are needed.",
}


def get_schema(db_path=None):
    """Return (schema_dict, descriptions) from the live DB if present, else the constants."""
    if db_path is None:
        return SCHEMA, TABLE_DESCRIPTIONS
    path = Path(db_path)
    if not path.exists():
        return SCHEMA, TABLE_DESCRIPTIONS
    con = sqlite3.connect(str(path))
    try:
        schema = {}
        for (name,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
            cols = [r[1] for r in con.execute(f"PRAGMA table_info({name})")]
            schema[name] = cols
        return schema, TABLE_DESCRIPTIONS
    finally:
        con.close()
