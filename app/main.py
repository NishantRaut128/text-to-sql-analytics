from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from app.db import get_schema, run_read_query
from app.llm import generate_sql, back_translate
from app.guardrails import validate_sql, UnsafeQuery

app = FastAPI(title="Text-to-SQL Analytics Engine", version="1.1.0")


class AskRequest(BaseModel):
    question: str = Field(min_length=5, max_length=500)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/schema")
def schema():
    try:
        return {"schema": get_schema()}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Database unavailable: {exc}")


@app.post("/ask")
def ask(request: AskRequest):
    try:
        schema_text = get_schema()
        candidate, generation = generate_sql(request.question, schema_text)
        safe_sql = validate_sql(candidate)
        columns, rows = run_read_query(safe_sql)
        explanation = back_translate(safe_sql)
        return {
            "question": request.question,
            "sql": safe_sql,
            "explanation": explanation,
            "generation": generation,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
        }
    except UnsafeQuery as exc:
        raise HTTPException(status_code=400, detail=f"Blocked by SQL safety checks: {exc}")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Query could not be completed: {exc}")
