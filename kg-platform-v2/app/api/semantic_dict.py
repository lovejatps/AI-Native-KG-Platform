from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import json
import sqlite3

from app.core.db import get_connection
from app.api import schemas

router = APIRouter(prefix="/semantic", tags=["Semantic Dictionary"])

# ---------- Helper utilities ----------

def _get_conn() -> sqlite3.Connection:
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    return conn

def _parse_synonyms(text: str) -> List[str]:
    try:
        return json.loads(text)
    except Exception:
        return []

# ---------- Field Dictionary Endpoints ----------
@router.get("/fields", response_model=schemas.PagedFieldDictResponse)
async def list_fields(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    conn = _get_conn()
    cur = conn.cursor()
    base_sql = "SELECT * FROM field_dictionary"
    params = []
    if search:
        base_sql += " WHERE table_name LIKE ? OR column_name LIKE ? OR description LIKE ? OR synonyms LIKE ?"
        pattern = f"%{search}%"
        params.extend([pattern, pattern, pattern, pattern])
    count_sql = f"SELECT COUNT(*) FROM ({base_sql})"
    total = cur.execute(count_sql, params).fetchone()[0]
    sql = f"{base_sql} ORDER BY id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = cur.execute(sql, params).fetchall()
    items = []
    for r in rows:
        items.append(
            schemas.FieldDictOut(
                id=r["id"],
                library_name=r["library_name"],
                table_name=r["table_name"],
                column_name=r["column_name"],
                synonyms=_parse_synonyms(r["synonyms"]),
                description=r["description"],
            )
        )
    return schemas.PagedFieldDictResponse(total=total, items=items)

@router.post("/fields", response_model=schemas.FieldDictOut, status_code=201)
async def create_field(item: schemas.FieldDictCreate):
    conn = _get_conn()
    cur = conn.cursor()
    # Unique constraint: same table + same column
    cur.execute(
        "SELECT id FROM field_dictionary WHERE table_name=? AND column_name=?",
        (item.table_name, item.column_name),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="同一表中已存在该字段的字典记录")
    cur.execute(
        "INSERT INTO field_dictionary (library_name, table_name, column_name, synonyms, description) VALUES (?, ?, ?, ?, ?)",
        (
            item.library_name,
            item.table_name,
            item.column_name,
            json.dumps(item.synonyms),
            item.description,
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    return schemas.FieldDictOut(
        id=new_id,
        library_name=item.library_name,
        table_name=item.table_name,
        column_name=item.column_name,
        synonyms=item.synonyms,
        description=item.description,
    )

@router.put("/fields/{field_id}", response_model=schemas.FieldDictOut)
async def update_field(field_id: int, item: schemas.FieldDictUpdate):
    conn = _get_conn()
    cur = conn.cursor()
    # Check existence
    cur.execute("SELECT * FROM field_dictionary WHERE id=?", (field_id,))
    existing = cur.fetchone()
    if not existing:
        raise HTTPException(status_code=404, detail="字段字典记录未找到")
    # Unique constraint (exclude self)
    cur.execute(
        "SELECT id FROM field_dictionary WHERE table_name=? AND column_name=? AND id!=?",
        (item.table_name, item.column_name, field_id),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="同一表中已存在相同字段的字典记录")
    cur.execute(
        "UPDATE field_dictionary SET library_name=?, table_name=?, column_name=?, synonyms=?, description=? WHERE id=?",
        (
            item.library_name,
            item.table_name,
            item.column_name,
            json.dumps(item.synonyms),
            item.description,
            field_id,
        ),
    )
    conn.commit()
    return schemas.FieldDictOut(
        id=field_id,
        library_name=item.library_name,
        table_name=item.table_name,
        column_name=item.column_name,
        synonyms=item.synonyms,
        description=item.description,
    )

@router.delete("/fields/{field_id}", status_code=204)
async def delete_field(field_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM field_dictionary WHERE id=?", (field_id,))
    conn.commit()
    return

# ---------- Value Dictionary Endpoints ----------
@router.get("/values", response_model=schemas.PagedValueDictResponse)
async def list_values(
    limit: int = Query(10, ge=1),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
):
    conn = _get_conn()
    cur = conn.cursor()
    base_sql = "SELECT * FROM value_dictionary"
    params = []
    if search:
        base_sql += " WHERE table_name LIKE ? OR column_name LIKE ? OR display_value LIKE ? OR actual_value LIKE ? OR synonyms LIKE ?"
        pattern = f"%{search}%"
        params.extend([pattern] * 5)
    count_sql = f"SELECT COUNT(*) FROM ({base_sql})"
    total = cur.execute(count_sql, params).fetchone()[0]
    sql = f"{base_sql} ORDER BY id LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    rows = cur.execute(sql, params).fetchall()
    items = []
    for r in rows:
        items.append(
            schemas.ValueDictOut(
                id=r["id"],
                library_name=r["library_name"],
                table_name=r["table_name"],
                column_name=r["column_name"],
                display_value=r["display_value"],
                actual_value=r["actual_value"],
                synonyms=_parse_synonyms(r["synonyms"]),
            )
        )
    return schemas.PagedValueDictResponse(total=total, items=items)

@router.post("/values", response_model=schemas.ValueDictOut, status_code=201)
async def create_value(item: schemas.ValueDictCreate):
    conn = _get_conn()
    cur = conn.cursor()
    # Unique constraint: same table + column + actual_value
    cur.execute(
        "SELECT id FROM value_dictionary WHERE table_name=? AND column_name=? AND actual_value=?",
        (item.table_name, item.column_name, item.actual_value),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="同一字段已存在相同实际值的映射记录")
    cur.execute(
        "INSERT INTO value_dictionary (library_name, table_name, column_name, display_value, actual_value, synonyms) VALUES (?, ?, ?, ?, ?, ?)",
        (
            item.library_name,
            item.table_name,
            item.column_name,
            item.display_value,
            item.actual_value,
            json.dumps(item.synonyms),
        ),
    )
    conn.commit()
    new_id = cur.lastrowid
    return schemas.ValueDictOut(
        id=new_id,
        library_name=item.library_name,
        table_name=item.table_name,
        column_name=item.column_name,
        display_value=item.display_value,
        actual_value=item.actual_value,
        synonyms=item.synonyms,
    )

@router.put("/values/{value_id}", response_model=schemas.ValueDictOut)
async def update_value(value_id: int, item: schemas.ValueDictUpdate):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM value_dictionary WHERE id=?", (value_id,))
    if not cur.fetchone():
        raise HTTPException(status_code=404, detail="值映射字典记录未找到")
    # Unique constraint (exclude self)
    cur.execute(
        "SELECT id FROM value_dictionary WHERE table_name=? AND column_name=? AND actual_value=? AND id!=?",
        (item.table_name, item.column_name, item.actual_value, value_id),
    )
    if cur.fetchone():
        raise HTTPException(status_code=400, detail="同一字段已存在相同实际值的映射记录")
    cur.execute(
        "UPDATE value_dictionary SET library_name=?, table_name=?, column_name=?, display_value=?, actual_value=?, synonyms=? WHERE id=?",
        (
            item.library_name,
            item.table_name,
            item.column_name,
            item.display_value,
            item.actual_value,
            json.dumps(item.synonyms),
            value_id,
        ),
    )
    conn.commit()
    return schemas.ValueDictOut(
        id=value_id,
        library_name=item.library_name,
        table_name=item.table_name,
        column_name=item.column_name,
        display_value=item.display_value,
        actual_value=item.actual_value,
        synonyms=item.synonyms,
    )

@router.delete("/values/{value_id}", status_code=204)
async def delete_value(value_id: int):
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM value_dictionary WHERE id=?", (value_id,))
    conn.commit()
    return
