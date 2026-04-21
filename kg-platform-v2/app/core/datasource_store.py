"""Simple in‑memory / JSON file storage for data source definitions.

Each data source is represented as a dict with the following keys:
- id (uuid str)
- system_name (str)
- db_type ("mysql" or "sqlite")
- host (str) – hostname/IP or file path for sqlite
- port (int | None)
- username (str | None)
- password (str | None)
- database (str | None)
"""

import json
import os
import uuid
from typing import List, Dict, Any

_DATA_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "datasources.json")
)

# Load existing data sources at import time
if os.path.exists(_DATA_FILE):
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        _DATA_SOURCES: List[Dict[str, Any]] = json.load(f)
else:
    _DATA_SOURCES = []


def _persist() -> None:
    """Write the current list to the JSON file."""
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_DATA_SOURCES, f, ensure_ascii=False, indent=2)


def list_datasources() -> List[Dict[str, Any]]:
    return list(_DATA_SOURCES)


def get_datasource(ds_id: str) -> Dict[str, Any] | None:
    for ds in _DATA_SOURCES:
        if ds["id"] == ds_id:
            return ds
    return None


def create_datasource(data: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure status field exists with default "未知"
    data = {**data, "status": data.get("status", "未知")}
    ds = {
        "id": uuid.uuid4().hex,
        **data,
    }
    _DATA_SOURCES.append(ds)
    _persist()
    return ds


def update_datasource(ds_id: str, data: Dict[str, Any]) -> Dict[str, Any] | None:
    for i, ds in enumerate(_DATA_SOURCES):
        if ds["id"] == ds_id:
            _DATA_SOURCES[i] = {**ds, **data, "id": ds_id}
            _persist()
            return _DATA_SOURCES[i]
    return None


def delete_datasource(ds_id: str) -> bool:
    global _DATA_SOURCES
    original_len = len(_DATA_SOURCES)
    _DATA_SOURCES = [ds for ds in _DATA_SOURCES if ds["id"] != ds_id]
    if len(_DATA_SOURCES) != original_len:
        _persist()
        return True
    return False


def test_datasource(ds_id: str) -> str:
    """尝试连接数据源，返回状态: 正常 / 失败 / 未知"""
    ds = get_datasource(ds_id)
    if not ds:
        return "未知"
    db_type = ds.get("db_type")
    try:
        if db_type == "sqlite":
            # 对于 sqlite，检查文件是否存在并能打开
            path = ds.get("host")
            if path and os.path.exists(path):
                # 尝试打开 SQLite 数据库
                import sqlite3

                conn = sqlite3.connect(path)
                conn.close()
                return "正常"
            else:
                return "失败"
        elif db_type == "mysql":
            # 使用 pymysql 进行连接（若未安装则视为失败）
            try:
                import pymysql
            except Exception:
                return "失败"
            conn = pymysql.connect(
                host=ds.get("host"),
                port=ds.get("port") or 3306,
                user=ds.get("username"),
                password=ds.get("password"),
                database=ds.get("database"),
                connect_timeout=5,
                charset="utf8mb4",
            )
            conn.close()
            return "正常"
        else:
            return "未知"
    except Exception as e:
        # 任何异常视为连接失败
        return "失败"


def get_schema(ds_id: str) -> dict:
    """返回指定数据源的库结构信息，格式:
    {
        "database": <库名>,
        "tables": [
            {"name": <表名>, "columns": [{"name": <字段>, "type": <类型>, "comment": <备注>}...]}, ...
        ]
    }
    """
    ds = get_datasource(ds_id)
    if not ds:
        return {"database": None, "tables": []}
    db_type = ds.get("db_type")
    result = {"database": ds.get("database") or ds.get("system_name"), "tables": []}
    try:
        if db_type == "sqlite":
            import sqlite3

            conn = sqlite3.connect(ds.get("host"))
            cur = conn.cursor()
            # 获取表名
            cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cur.fetchall()]
            for t in tables:
                cur.execute(f"PRAGMA table_info('{t}')")
                cols = []
                for col in cur.fetchall():
                    # col format: cid, name, type, notnull, dflt_value, pk
                    cols.append({"name": col[1], "type": col[2], "comment": ""})
                result["tables"].append({"name": t, "columns": cols})
            conn.close()
        elif db_type == "mysql":
            try:
                import pymysql
            except Exception:
                return result
            conn = pymysql.connect(
                host=ds.get("host"),
                port=ds.get("port") or 3306,
                user=ds.get("username"),
                password=ds.get("password"),
                database=ds.get("database"),
                charset="utf8mb4",
            )
            cur = conn.cursor()
            # 获取表名
            cur.execute(
                "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=%s",
                (ds.get("database"),),
            )
            tables = [row[0] for row in cur.fetchall()]
            for t in tables:
                cur.execute(
                    "SELECT ORDINAL_POSITION, COLUMN_NAME, COLUMN_TYPE, COLUMN_COMMENT FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s ORDER BY ORDINAL_POSITION",
                    (ds.get("database"), t),
                )
                cols = []
                for col in cur.fetchall():
                    cols.append({"name": col[1], "type": col[2], "comment": col[3]})
                result["tables"].append({"name": t, "columns": cols})
            conn.close()
    except Exception as e:
        # 在查询过程中出现错误，返回已收集的部分或空结构
        pass
    return result
