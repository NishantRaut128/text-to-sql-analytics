"""Gemini-powered SQL generation with a deterministic local demo fallback."""
import re

import requests
import sqlglot
from app.config import GEMINI_API_KEY, GEMINI_MODEL

API_ROOT = "https://generativelanguage.googleapis.com/v1beta/models"

SYSTEM_RULES = """You are a careful analytics engineer. Generate exactly one PostgreSQL SELECT query.
Use only tables and columns in the supplied schema. Do not invent fields. Never generate
INSERT, UPDATE, DELETE, DDL, transaction commands, multiple statements, or SQL comments.
Prefer explicit JOIN conditions and clear aliases. Do not include markdown fences or explanations.
Return SQL only."""

CLASSIFIER_RULES = """You are a database question relevance checker.
Decide whether the supplied business question can reasonably be answered using the supplied schema.
Return exactly one token: SUPPORTED or UNSUPPORTED.
Return UNSUPPORTED if the question is unrelated to the database or requires data not represented
by its tables and columns. If uncertain, return UNSUPPORTED. Do not generate SQL or explanations."""


def _gemini_text(
    prompt: str,
    temperature: float = 0.0,
    system_rules: str = SYSTEM_RULES,
) -> str:
    """Call Gemini and return its first text part."""
    url = f"{API_ROOT}/{GEMINI_MODEL}:generateContent"
    response = requests.post(
        url,
        headers={"x-goog-api-key": GEMINI_API_KEY},
        json={
            "system_instruction": {"parts": [{"text": system_rules}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": 1200},
        },
        timeout=35,
    )
    response.raise_for_status()
    payload = response.json()
    try:
        return payload["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini returned no text. Please rephrase the question.") from exc


def _clean_sql(value: str) -> str:
    value = re.sub(r"^```(?:sql)?\s*|\s*```$", "", value.strip(), flags=re.IGNORECASE)
    return value.strip().rstrip(";")


def check_question_support(question: str, schema: str) -> None:
    """Fail closed unless Gemini explicitly classifies the question as supported."""
    prompt = f"Database schema:\n{schema}\n\nBusiness question:\n{question}\n"
    result = _gemini_text(prompt, temperature=0.0, system_rules=CLASSIFIER_RULES)
    decision = result.strip().upper().strip(". ")
    if decision == "UNSUPPORTED":
        raise ValueError(
            "This question is outside the scope of the available database. "
            "Please ask about customers, orders, products or sales."
        )
    if decision != "SUPPORTED":
        raise ValueError("Could not verify that this question is supported by the database. Please rephrase it.")


def _normalise(sql: str) -> str:
    return sqlglot.parse_one(sql, read="postgres").sql(dialect="postgres", pretty=False)


def generate_sql(question: str, schema: str) -> tuple[str, dict]:
    """Generate one SQL candidate; reject unsupported questions before SQL generation."""
    if not GEMINI_API_KEY:
        return demo_sql(question), {
            "provider": "demo",
            "agreement": "single deterministic pattern",
        }

    check_question_support(question, schema)
    prompt = (
        f"Database schema:\n{schema}\n\nBusiness question:\n{question}\n\n"
        "Generate one accurate PostgreSQL SELECT query. Check joins, grouping, filters and aggregations carefully."
    )
    sql = _clean_sql(_gemini_text(prompt, temperature=0.0))
    try:
        _normalise(sql)
    except Exception as exc:
        raise ValueError(f"Gemini generated SQL that could not be parsed: {exc}") from exc

    return sql, {
        "provider": "Gemini",
        "model": GEMINI_MODEL,
        "agreement": "Single SQL draft; PostgreSQL syntax check passed",
    }


def demo_sql(question: str) -> str:
    """Small deterministic examples for local setup without an API key."""
    q = question.lower()
    if "monthly" in q and "revenue" in q:
        return "SELECT DATE_TRUNC('month', o.order_date) AS month, SUM(oi.quantity * oi.unit_price) AS revenue FROM orders o JOIN order_items oi ON oi.order_id = o.order_id GROUP BY 1 ORDER BY 1"
    if "top" in q and "product" in q:
        return "SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS revenue FROM products p JOIN order_items oi ON oi.product_id = p.product_id GROUP BY p.product_name ORDER BY revenue DESC LIMIT 10"
    if "customer" in q and ("top" in q or "highest" in q):
        return "SELECT c.customer_name, SUM(oi.quantity * oi.unit_price) AS revenue FROM customers c JOIN orders o ON o.customer_id = c.customer_id JOIN order_items oi ON oi.order_id = o.order_id GROUP BY c.customer_name ORDER BY revenue DESC LIMIT 10"
    if "order" in q and "count" in q:
        return "SELECT COUNT(*) AS order_count FROM orders"
    raise ValueError("Demo mode supports monthly revenue, top products, top customers and order count. Add GEMINI_API_KEY for open-ended questions.")


def back_translate(sql: str) -> str:
    """Explain SQL in plain English; this explanation is not a correctness proof."""
    if not GEMINI_API_KEY:
        return "Demo mode: this query was generated from a predefined analytics pattern."
    prompt = (
        "Explain in one or two concise sentences what this PostgreSQL query calculates. "
        "Do not claim any result values and mention important grouping/filtering.\n\n" + sql
    )
    return _gemini_text(prompt, temperature=0.0)
