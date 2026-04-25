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
        CREATE TABLE IF NOT EXISTS student (
            id       INTEGER PRIMARY KEY,
            name     TEXT NOT NULL,
            class_id INTEGER NOT NULL,
            gender   TEXT,
            age      INTEGER,
            FOREIGN KEY (class_id) REFERENCES class(id)
        );
        CREATE TABLE IF NOT EXISTS grade (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS class (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            grade_id INTEGER NOT NULL,
            FOREIGN KEY (grade_id) REFERENCES grade(id)
        );
        """
    )
    # ----------------------------------------------------------
    # 语义词典表（字段语义）
    # ----------------------------------------------------------
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS field_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            library_name VARCHAR(50),
            table_name VARCHAR(50) NOT NULL,
            column_name VARCHAR(50) NOT NULL,
            synonyms TEXT, -- JSON array
            description VARCHAR(255)
        );
        """
    )
    # ----------------------------------------------------------
    # 语义词典表（值映射）
    # ----------------------------------------------------------
    cur.executescript(
        """
        CREATE TABLE IF NOT EXISTS value_dictionary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            library_name VARCHAR(50),
            table_name VARCHAR(50) NOT NULL,
            column_name VARCHAR(50) NOT NULL,
            display_value VARCHAR(50) NOT NULL,
            actual_value VARCHAR(50) NOT NULL,
            synonyms TEXT -- JSON array
        );
        """
    );
    # ----------------------------------------------------------
    # 示例数据（仅供演示） - 若已存在则跳过插入
    # ----------------------------------------------------------
    # Check whether the dictionary tables already contain data.
    # If any rows exist, we assume the database has been seeded and skip further inserts.
    cur.execute("SELECT COUNT(*) FROM field_dictionary")
    if cur.fetchone()[0] > 0:
        # Seed data already present; skip remaining inserts.
        conn.commit()
        conn.close()
        return

    cur.executemany(
        "INSERT OR IGNORE INTO field_dictionary (library_name, table_name, column_name, synonyms, description) VALUES (?, ?, ?, ?, ?)",
        [
            ("SchoolA", "student", "gender", "[\"性别\",\"男女\",\"男生\",\"女生\"]", "学生性别字段"),
            ("SchoolA", "grade", "name", "[\"年级\",\"几年级\",\"高一\",\"高二\"]", "年级名称"),
            ("SchoolA", "class", "name", "[\"班级\",\"几班\",\"1班\",\"2班\"]", "班级名称")
        ]
    )
    cur.executemany(
        "INSERT OR IGNORE INTO value_dictionary (library_name, table_name, column_name, display_value, actual_value, synonyms) VALUES (?, ?, ?, ?, ?, ?)",
        [
            ("SchoolA", "student", "gender", "男", "M", "[\"男\",\"男生\",\"男性\",\"male\"]"),
            ("SchoolA", "student", "gender", "女", "F", "[\"女\",\"女生\",\"女性\",\"female\"]"),
            ("SchoolA", "grade", "name", "一年级", "一年级", "[\"一年级\",\"高一\",\"1年级\"]")
        ]
    );


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
