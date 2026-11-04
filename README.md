# Evaluation-Driven Text-to-SQL Insights Engine

Python, SQL, LLM API (optional/stubbed), pytest — public analytics
dataset created for this project (no employer data).

## What this is

An engine that turns business questions into SQLite queries, with
evaluation built in so changes can be checked against a gold set
instead of judged by eye:

- A small analytics database (customers, products, orders) in SQLite.
- A gold set of 24 business questions with gold SQL, across 3
  difficulty tiers (8 easy, 8 medium, 8 hard).
- A schema-aware prompt builder and keyword table-description retrieval.
- A SQL validation layer (SELECT only, blocks DDL/DML, checks tables
  and qualified columns against the schema; uses sqlparse if available,
  otherwise a conservative regex fallback).
- A rule/template SQL generator that runs **offline** — no API key,
  no external call.
- An **optional LLM provider stub, disabled by default**
  (`src/text2sql/llm_client.py`). It is never called by the evaluator
  and raises rather than inventing an API call or a cost if enabled
  without a real provider implementation.
- A question->SQL cache, query guardrails (validation + single
  statement only), and a pytest regression suite that fails if
  iteration-2 accuracy falls below 0.80 on the gold set.

## Results — actually computed by the evaluator in this repo

From `outputs/metrics.json`, produced by `scripts/evaluate.py`
(24 gold questions, SQLite database with 200 customers, 10 products,
2,000 orders, total revenue $1,339,159.40):

- **Iteration 1 (baseline generator, easy templates only): 37.5%
  accuracy (9/24)** — easy 100% (8/8), medium 12.5% (1/8), hard 0% (0/8).
- **Iteration 2 (improved generator, schema-aware templates +
  retrieval + validation): 100% accuracy (24/24)** — easy 100%,
  medium 100%, hard 100%.
- Median latency per query: iteration 1, 0.005 ms; iteration 2,
  2.005 ms; iteration-2 cached rerun, 0.004 ms (cache hit rate 1.0
  on the rerun, 24/24 hits).
- **Per-query cost: $0.** The offline generator makes no API call;
  the LLM stub is disabled, so no LLM cost is claimed or measured.
  If a real LLM provider is plugged in later, its cost must be
  measured from actual provider billing/logs, not estimated here.

### Honest limitation on the 100% figure

The 100% is **execution match on this 24-question gold set**, where
the improved templates were written to cover exactly these question
patterns. It is a regression guard for this gold set, not a claim
that the generator will answer unseen phrasings at 100%. The
regression test (`tests/test_text2sql.py::test_accuracy_threshold`)
fails if iteration-2 accuracy on this gold set drops below 0.80.

## How to run

```bash
pip install -r requirements.txt
python3 scripts/build_dataset.py   # creates data/analytics.db (84 KB)
python3 scripts/evaluate.py        # writes outputs/metrics.json + outputs/logs/runs.jsonl
python3 scripts/make_charts.py     # writes outputs/charts/accuracy_by_tier.png
python3 -m pytest tests/ -q        # 8 tests, including the accuracy gate
```

## Files

- `data/analytics.db` — synthetic SQLite database (seed 7).
- `data/gold_questions.json` — 24 questions with gold SQL, versioned.
- `src/text2sql/schema.py` — schema + table descriptions.
- `src/text2sql/prompt.py` — prompt builder + table retrieval.
- `src/text2sql/validator.py` — SELECT-only validation layer.
- `src/text2sql/generator.py` — v1 baseline + v2 improved generators.
- `src/text2sql/llm_client.py` — optional LLM stub, disabled by default.
- `src/text2sql/cache.py` — question->SQL cache.
- `scripts/build_dataset.py`, `scripts/evaluate.py`, `scripts/make_charts.py`.
- `tests/test_text2sql.py` — validator, gold execution, retrieval,
  generator, LLM-disabled, and accuracy-gate tests.
- `outputs/metrics.json`, `outputs/logs/runs.jsonl`,
  `outputs/charts/accuracy_by_tier.png`.

## Limitations

- The generator is rule/template-based, not a general LLM; unseen
  question phrasings outside the covered patterns will return no SQL
  or a wrong query (counted as incorrect by the evaluator).
- The database is synthetic and small (2,000 orders); it demonstrates
  the engine, not a production analytics warehouse.
