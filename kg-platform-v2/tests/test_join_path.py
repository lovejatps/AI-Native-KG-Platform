import pytest
from app.nl2sql.engine import build_join_path, generate_sql

# Minimal schema example matching our KG platform expectations
SCHEMA = {
    "entities": [
        {
            "name": "student",
            "properties": [
                {"name": "id", "source_column": "student.id"},
                {"name": "name", "source_column": "student.name"},
                {"name": "class_id", "source_column": "student.class_id"},
            ],
        },
        {
            "name": "class",
            "properties": [
                {"name": "id", "source_column": "class.id"},
                {"name": "grade_id", "source_column": "class.grade_id"},
                {"name": "name", "source_column": "class.name"},
            ],
        },
        {
            "name": "grade",
            "properties": [
                {"name": "id", "source_column": "grade.id"},
                {"name": "name", "source_column": "grade.name"},
            ],
        },
    ]
}

def test_build_join_path_student_grade():
    tables = ["student", "class", "grade"]
    join_descs = build_join_path(tables, SCHEMA)
    # Expect three join steps linking student->class and class->grade
    assert len(join_descs) == 2
    # Verify that join conditions contain foreign key references
    conds = [j["on"] for j in join_descs]
    assert any("student.class_id" in c and "class.id" in c for c in conds)
    assert any("class.grade_id" in c and "grade.id" in c for c in conds)

def test_generate_sql_simple_query():
    plan = {
        "tables": ["student", "class", "grade"],
        "select": ["student.name", "grade.name"],
        "where": [{"entity": "grade", "column": "name", "op": "=", "value": "三"}],
        "limit": None,
    }
    sql, _ = generate_sql(plan, SCHEMA)
    # Ensure generated SQL contains proper JOINs and ON conditions
    assert "JOIN" in sql.upper()
    assert "ON" in sql.upper()
    assert "student.class_id = class.id" in sql or "class.id = student.class_id" in sql
    assert "class.grade_id = grade.id" in sql or "grade.id = class.grade_id" in sql
    assert "WHERE" in sql.upper() and "grade.name = '三'" in sql
