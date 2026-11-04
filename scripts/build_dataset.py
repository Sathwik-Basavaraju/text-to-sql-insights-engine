"""Build the synthetic analytics SQLite database.

Data is SYNTHETIC, generated deterministically (seed 7) for this
project only — it is not employer data and not claimed to be a
public dataset download. Schema: customers, products, orders.
Run from the project root: python3 scripts/build_dataset.py
"""
import random
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB = ROOT / "data" / "analytics.db"

REGIONS = ["North", "South", "East", "West"]
SEGMENTS = ["Consumer", "Corporate", "Small Business"]
PRODUCTS = [
    ("Laptop Pro", "Electronics", 1299.00),
    ("Wireless Mouse", "Electronics", 29.99),
    ("Office Chair", "Furniture", 249.00),
    ("Standing Desk", "Furniture", 599.00),
    ("Winter Jacket", "Clothing", 149.00),
    ("Running Shoes", "Clothing", 119.00),
    ("Monitor 27in", "Electronics", 349.00),
    ("Bookshelf", "Furniture", 179.00),
    ("T-Shirt Pack", "Clothing", 39.99),
    ("Tablet", "Electronics", 499.00),
]


def main():
    rng = random.Random(7)
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    con = sqlite3.connect(str(DB))
    cur = con.cursor()
    cur.execute("CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, name TEXT, region TEXT, segment TEXT, signup_date TEXT)")
    cur.execute("CREATE TABLE products (product_id INTEGER PRIMARY KEY, name TEXT, category TEXT, price REAL)")
    cur.execute("CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER, product_id INTEGER, order_date TEXT, quantity INTEGER, amount REAL, FOREIGN KEY(customer_id) REFERENCES customers(customer_id), FOREIGN KEY(product_id) REFERENCES products(product_id))")
    customers = []
    for cid in range(1, 201):
        customers.append((cid, f"Customer {cid:03d}", rng.choice(REGIONS), rng.choice(SEGMENTS), f"20{22 + rng.randint(0, 1)}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"))
    cur.executemany("INSERT INTO customers VALUES (?,?,?,?,?)", customers)
    products = [(i + 1, n, c, p) for i, (n, c, p) in enumerate(PRODUCTS)]
    cur.executemany("INSERT INTO products VALUES (?,?,?,?)", products)
    orders = []
    oid = 1
    for _ in range(2000):
        cid = rng.randint(1, 200)
        pid, _, _, price = products[rng.randint(0, len(products) - 1)]
        qty = rng.randint(1, 3)
        year = rng.choice([2023, 2024])
        date = f"{year}-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}"
        orders.append((oid, cid, pid, date, qty, round(qty * price, 2)))
        oid += 1
    cur.executemany("INSERT INTO orders VALUES (?,?,?,?,?,?)", orders)
    con.commit()
    counts = {t: cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in ["customers", "products", "orders"]}
    total = cur.execute("SELECT SUM(amount) FROM orders").fetchone()[0]
    con.close()
    print(f"Wrote {DB}: {counts}, total revenue ${total:,.2f}")


if __name__ == "__main__":
    main()
