import pytest
from app import llm

SCHEMA = "Table customers: customer_id (INTEGER), customer_name (TEXT)"


def test_classifier_accepts_explicit_supported(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_gemini_text", lambda *args, **kwargs: "SUPPORTED")
    llm.check_question_support("List customers", SCHEMA)


def test_classifier_rejects_unsupported(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_gemini_text", lambda *args, **kwargs: "UNSUPPORTED")
    with pytest.raises(ValueError, match="outside the scope"):
        llm.check_question_support("Population of Mars?", SCHEMA)


def test_classifier_fails_closed_on_unexpected_output(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(llm, "_gemini_text", lambda *args, **kwargs: "Maybe, probably supported")
    with pytest.raises(ValueError, match="Could not verify"):
        llm.check_question_support("List customers", SCHEMA)


def test_demo_mode_supports_known_pattern(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "")
    sql, metadata = llm.generate_sql("What is the total order count?", SCHEMA)
    assert "COUNT(*)" in sql
    assert metadata["provider"] == "demo"


def test_demo_mode_rejects_unknown_question(monkeypatch):
    monkeypatch.setattr(llm, "GEMINI_API_KEY", "")
    with pytest.raises(ValueError, match="Demo mode supports"):
        llm.generate_sql("What is the population of Mars?", SCHEMA)
