import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
from text2sql.generator import generate_sql  # noqa: E402
from text2sql.prompt import build_prompt, retrieve_tables  # noqa: E402
from text2sql.validator import ValidationError, validate_sql  # noqa: E402
from text2sql.llm_client import LLMClient  # noqa: E402

DB = ROOT / "data" / "analytics.db"
GOLD = ROOT / "data" / "gold_questions.json"


def test_validator_blocks_dangerous_sql():
    for bad in [
        "DROP TABLE orders",
        "DELETE FROM orders",
        "INSERT INTO orders VALUES (1, 1, 1, '2024-01-01', 1, 10)",
        "SELECT * FROM orders; DROP TABLE customers",
        "UPDATE customers SET region = 'X'",
    ]:
        with pytest.raises(ValidationError):
            validate_sql(bad)


def test_validator_allows_select_and_unknown_table_fails():
    assert validate_sql("SELECT SUM(amount) FROM orders")
    with pytest.raises(ValidationError):
        validate_sql("SELECT * FROM nonexistent_table")


def test_gold_questions_all_execute():
    questions = json.loads(GOLD.read_text())
    assert len(questions) >= 20
    assert len({q["tier"] for q in questions}) >= 3
    con = sqlite3.connect(str(DB))
    try:
        for q in questions:
            rows = con.execute(q["gold_sql"]).fetchall()
            assert len(rows) > 0, f"Gold SQL returned no rows for {q['id']}"
    finally:
        con.close()


def test_retrieval_includes_relevant_tables():
    assert "customers" in retrieve_tables("How many customers are in the North region?")
    assert "products" in retrieve_tables("What is revenue by product category?")
    assert "orders" in retrieve_tables("What is total revenue?")


def test_generator_v2_produces_valid_sql_for_easy_questions():
    sql = generate_sql("What is the total revenue across all orders?", version=2)
    assert sql is not None
    validate_sql(sql)
    con = sqlite3.connect(str(DB))
    try:
        rows = con.execute(sql).fetchall()
        assert rows and rows[0][0] > 0
    finally:
        con.close()


def test_llm_client_disabled_by_default():
    client = LLMClient()
    assert client.generate("any prompt") is None


def test_accuracy_threshold():
    """Regression gate: iteration-2 accuracy must meet the threshold in metrics.json."""
    metrics_path = ROOT / "outputs" / "metrics.json"
    if not metrics_path.exists():
        pytest.skip("Run scripts/evaluate.py first to generate outputs/metrics.json")
    metrics = json.loads(metrics_path.read_text())
    threshold = metrics["accuracy_threshold_for_tests"]
    acc = metrics["iteration_2_improved_v2"]["accuracy"]
    assert acc >= threshold, f"Accuracy {acc} below threshold {threshold}"
    assert metrics["iteration_2_improved_v2"]["accuracy"] >= metrics["iteration_1_baseline_v1"]["accuracy"]


def test_prompt_includes_schema():
    prompt = build_prompt("What is total revenue?")
    assert "orders" in prompt and "amount" in prompt
