# Test and evaluation notes

Run all automated tests from the repository root with `pytest -q`.

- `test_guardrails.py`: SQL safety policy and row-limit behaviour.
- `test_llm.py`: mocked relevance-classifier decisions and deterministic demo fallback.
- `test_api.py`: health route and Pydantic request validation.
- `benchmark_questions.json`: 15 candidate business questions for a future reviewed gold-SQL execution benchmark. This JSON file is a checklist, not a claim that all questions have been executed or scored.

Tests that call external Gemini or a live PostgreSQL database are intentionally not part of the default unit suite.
