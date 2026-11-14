# Text-to-SQL Analytics Engine with Safety Guardrails

A portfolio prototype that lets users ask questions about a synthetic sales database in natural language, inspect generated PostgreSQL, and explore bounded results in a Streamlit dashboard.

> **Project status:** functional local prototype. Gemini-generated SQL is not guaranteed to be semantically correct. The benchmark file is a review checklist, not a measured accuracy score. Run the automated tests and database-backed evaluation in your own environment before reporting results.

## Architecture

```text
Business question
      |
      v
Streamlit dashboard ---- HTTP POST ----> FastAPI /ask
                                           |
                                           v
                                 Fetch database schema
                                           |
                                           v
                               Gemini relevance classifier
                                           |
                                           v
                                  Gemini SQL generation
                                           |
                                           v
                               SQLGlot parse and guardrails
                                           |
                                           v
                             PostgreSQL read-only app role
                                           |
                                           v
                              Bounded rows + explanation
                                           |
                                           v
                         Streamlit table, chart and CSV export
```

## Features

- Schema-aware PostgreSQL SQL generation using the Gemini `generateContent` API.
- Schema-based relevance classification before SQL generation; unsupported or uncertain classifier output is rejected.
- SQLGlot parsing and structural guardrails: one statement, SELECT-family roots only, mutation/DDL command blocking, no `SELECT INTO`, no locking clauses, fixed non-negative integer `LIMIT`, and a configured maximum row count.
- Separate PostgreSQL administrative and application accounts. The application role is granted SELECT on the application tables and configured with read-only transactions by default.
- Statement timeout and an outer result row cap in the database execution layer.
- Plain-English SQL explanation. This is an aid for inspection, not proof of query correctness.
- Streamlit interface with SQL preview, result table, metric selection, Plotly visualization and CSV download.
- Small deterministic demo mode for a limited set of question patterns when no Gemini key is configured.
- Pytest unit tests for SQL guardrails, relevance-classifier decisions, demo fallback and API request validation.

## Data model

`seed.py` creates four related tables:

- `customers`: customer name, city and segment.
- `products`: product name, category and list price.
- `orders`: customer, order date and status.
- `order_items`: order, product, quantity and transaction unit price.

The seed script uses a fixed random seed and creates 60 customers, 8 products, 500 orders and their line items. It drops and recreates these tables; use it only on the demo database because rerunning it replaces the existing seeded data.

## Requirements

- Python 3.11+
- Docker Desktop / Docker Engine with Docker Compose
- Gemini API key for open-ended Text-to-SQL (optional; demo mode supports only predefined patterns)

## Local setup (Windows PowerShell)

1. Create a local environment file:

   ```powershell
   Copy-Item .env.example .env
   ```

2. Add your Gemini API key to `.env`. Never commit or share this file.
3. Start PostgreSQL:

   ```powershell
   docker compose up -d db
   ```

4. Create and activate a virtual environment, then install packages:

   ```powershell
   py -m venv .venv
   .venv\Scripts\Activate.ps1
   pip install -r requirements.txt
   ```

5. Seed the demo database:

   ```powershell
   python seed.py
   ```

   The seed script uses the admin connection derived from the local `DATABASE_URL` by default. If needed, set `SEED_DATABASE_URL` to an admin connection string in your local environment.

6. Start the API in one terminal:

   ```powershell
   uvicorn app.main:app --reload
   ```

7. Start Streamlit in a second terminal:

   ```powershell
   streamlit run streamlit_app.py
   ```

8. Open `http://localhost:8501`. FastAPI docs are at `http://localhost:8000/docs`.

### Docker Compose

`docker compose up --build` starts PostgreSQL, API and dashboard. The API uses the `analytics_user` role over Docker's internal network. Seed the database using the admin connection from a local Python environment after the database is healthy.

The SQL initialization script under `sql/readonly.sql` is executed only when PostgreSQL initializes a **new empty data volume**. If the volume already existed before the script was added or changed, Docker will not rerun it automatically. Do not run `docker compose down -v` unless you intentionally want to delete the local database volume and all its data. For an existing volume, apply the SQL grants manually as an administrator or recreate the demo volume only when safe.

## Example questions

- What was our monthly revenue?
- Show the top 10 products by revenue.
- Which customers generated the highest revenue?
- What is the total order count?
- Compare revenue by customer segment.
- Which product categories have the highest sales?

## Configuration

See `.env.example` for `GEMINI_API_KEY`, `GEMINI_MODEL`, `DATABASE_URL`, `MAX_ROWS` and `QUERY_TIMEOUT_SECONDS`. `.env` is intentionally excluded from version control. The values in Compose and `sql/readonly.sql` are demo credentials only; replace them with secrets for any shared deployment.

## Automated tests

Install requirements and run:

```powershell
pytest -q
```

The automated suite covers:

- Read-only SQL policy, destructive statements and multi-statement rejection.
- `SELECT INTO`, locking clauses, negative and excessive limits.
- Relevance-classifier supported, unsupported and unexpected responses (Gemini is mocked; no API call is made).
- Demo-mode supported and unsupported patterns.
- `/health` and Pydantic request validation for `/ask`.

`tests/benchmark_questions.json` is a 15-question evaluation checklist spanning aggregation, grouping, joins, ranking, time-series, filtering, segmentation, unsupported and ambiguous questions. It records intended tables and SQL concepts. It is **not** an automated gold-result benchmark yet: the expected SQL/results need human review against a fixed database snapshot before execution accuracy can be reported.

## Security design and limitations

- Generated SQL is untrusted. SQLGlot validates its parsed structure before execution; do not rely on prompt instructions alone.
- PostgreSQL uses a separate application account with SELECT grants, and the role is configured for read-only transactions by default. Verify grants on an existing database volume because initialization scripts run only on first initialization.
- The database execution layer applies a statement timeout and an outer row cap. Row limits do not by themselves prevent expensive query plans.
- The relevance classifier is an LLM heuristic. It can incorrectly accept or reject a question; fail-closed handling of unexpected classifier output reduces, but does not eliminate, that risk.
- A syntactically valid and safe query can still answer the wrong business question. Human-reviewed gold SQL and expected results are needed to measure semantic correctness.
- The demo uses synthetic data only. Do not expose this prototype to untrusted users without authentication, network restrictions, stronger query-cost controls, logging, secret management and a security review.

## Known limitations and future work

1. Build an executable gold-SQL benchmark with fixed expected results and report execution accuracy by category.
2. Add clarification handling for ambiguous terms such as “best customer” (revenue, order count or profit).
3. Add schema/table allowlists, query-cost controls and more adversarial prompt-injection tests.
4. Add API authentication, request rate limits and production secret management.
5. Improve visualization selection for multiple dimensions and non-time-series results.

## Interview walkthrough

A concise explanation:

> “I built a natural-language analytics application using FastAPI, Gemini, SQLGlot, PostgreSQL and Streamlit. The API retrieves the database schema, checks whether a question is relevant to that schema, asks Gemini to generate PostgreSQL, validates the generated statement, and executes it through a least-privilege database account. Results are returned as JSON and displayed as tables, interactive Plotly charts and downloadable CSV files. I tested SQL safety rules, API validation and the main dashboard workflow. One limitation is that safe, syntactically valid SQL is not automatically semantically correct, so a reviewed gold-query benchmark is a planned next step.”
