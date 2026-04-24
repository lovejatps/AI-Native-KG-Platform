"""Utility to initialise the placeholder SQLite business database used by NL2SQL.

The NL2SQL pipeline expects tables `class`, `grade` and `student` with the
following columns (original column names, not semantic names):

* class:   id INTEGER PRIMARY KEY, name TEXT, grade_id INTEGER
* grade:   id INTEGER PRIMARY KEY, name TEXT
* student: id INTEGER PRIMARY KEY, name TEXT, class_id INTEGER, gender TEXT, age INTEGER

This module creates the tables if they do not exist and inserts a minimal
sample dataset sufficient for demo queries such as:
    "1-B班有多少学生"
"1-B班的学生年龄平均值是多少"

The function is idempotent – running it multiple times will not duplicate
records because we use ``INSERT OR IGNORE`` based on the primary key.
"""

import sqlite3
from .settings_v2 import get_settings


def _get_conn() -> sqlite3.Connection:
    settings = get_settings()
    db_path = getattr(settings, "BUSINESS_DB_PATH", "business.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_business_db() -> None:
    """Create tables and seed a small dataset.

    This function is safe to call at application start‑up. It will create the
    required tables if they are missing and insert a handful of rows used by
    NL2SQL example queries.
    """
    conn = _get_conn()
    cur = conn.cursor()

    # Create tables
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS grade (
            id   INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS class (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            grade_id INTEGER NOT NULL,
            FOREIGN KEY (grade_id) REFERENCES grade(id)
        );
        CREATE TABLE IF NOT EXISTS student (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            gender   TEXT,
            age      INTEGER,
            FOREIGN KEY (class_id) REFERENCES class(id)
        );
        """
    )

    # Insert sample data – use INSERT OR IGNORE to avoid duplicates on repeated runs
    cur.executemany(
        "INSERT OR IGNORE INTO grade (id, name) VALUES (?, ?)",
        [
            (1, "一年级"),
            (2, "二年级"),
        ],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO class (id, name, grade_id) VALUES (?, ?, ?)",
        [
            (1, "1-B", 1),
            (2, "2-A", 2),
        ],
    )
    cur.executemany(
        "INSERT OR IGNORE INTO student (id, name, class_id, gender, age) VALUES (?, ?, ?, ?, ?)",
        [
            (1, "张三", 1, "M", 10),
            (2, "李四", 1, "F", 11),
            (3, "王五", 2, "M", 12),
        ],
    )

    conn.commit()
    conn.close()

if __name__ == "__main__":
    # Allow ad‑hoc execution: ``python -m app.core.init_business_db``
    init_business_db()
    print("Business SQLite DB initialised (or already ready).")
