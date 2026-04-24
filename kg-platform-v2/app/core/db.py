"""Simple database helper for NL2SQL execution.

We use SQLite as a placeholder for the real business DB. The path to the
SQLite file is configurable via ``SettingsV2.BUSINESS_DB_PATH``. In production
this module can be replaced with a proper DB client (PostgreSQL, MySQL, etc.).
"""

import sqlite3
from .settings_v2 import get_settings

def get_connection():
    """Return a SQLite connection to the configured business DB file.
    The connection uses ``row_factory`` to provide dict‑like rows.
    """
    settings = get_settings()
    db_path = getattr(settings, "BUSINESS_DB_PATH", "business.db")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn
