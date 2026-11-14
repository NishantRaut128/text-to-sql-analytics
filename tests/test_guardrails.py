import pytest
from app.guardrails import validate_sql, UnsafeQuery


def test_select_is_allowed_and_limited():
    sql = validate_sql("SELECT customer_id FROM customers")
    assert "LIMIT 200" in sql


def test_select_with_join_is_allowed():
    sql = validate_sql(
        "SELECT c.customer_name, COUNT(o.order_id) AS orders "
        "FROM customers c LEFT JOIN orders o ON o.customer_id = c.customer_id "
        "GROUP BY c.customer_name"
    )
    assert "JOIN" in sql
    assert "LIMIT 200" in sql


@pytest.mark.parametrize("query", [
    "DELETE FROM customers",
    "UPDATE customers SET city = 'X'",
    "INSERT INTO customers(customer_name) VALUES ('x')",
    "DROP TABLE customers",
    "ALTER TABLE customers ADD COLUMN bad TEXT",
])
def test_mutating_statements_are_blocked(query):
    with pytest.raises(UnsafeQuery):
        validate_sql(query)


def test_multiple_statements_are_blocked():
    with pytest.raises(UnsafeQuery):
        validate_sql("SELECT 1; DROP TABLE customers")


def test_large_limit_is_capped():
    sql = validate_sql("SELECT * FROM customers LIMIT 99999")
    assert "LIMIT 200" in sql


def test_non_integer_limit_is_blocked():
    with pytest.raises(UnsafeQuery):
        validate_sql("SELECT * FROM customers LIMIT (SELECT 1)")


def test_empty_sql_is_blocked():
    with pytest.raises(UnsafeQuery):
        validate_sql("  ")


def test_select_into_is_blocked():
    with pytest.raises(UnsafeQuery, match="SELECT INTO"):
        validate_sql("SELECT customer_name INTO copied_customers FROM customers")


def test_select_for_update_is_blocked():
    with pytest.raises(UnsafeQuery, match="locking"):
        validate_sql("SELECT * FROM customers FOR UPDATE")


def test_negative_limit_is_blocked():
    with pytest.raises(UnsafeQuery, match="negative"):
        validate_sql("SELECT * FROM customers LIMIT -1")


def test_union_is_allowed_and_limited():
    sql = validate_sql("SELECT customer_name FROM customers UNION SELECT product_name FROM products")
    assert "UNION" in sql
    assert "LIMIT 200" in sql


def test_nested_mutation_is_blocked():
    with pytest.raises(UnsafeQuery):
        validate_sql("WITH changed AS (DELETE FROM customers RETURNING *) SELECT * FROM changed")
