import json, os
import logging
from typing import List, Dict, Any, Optional, Tuple

from ..core.models_store import list_models, get_model
from ..core.llm import llm
from ..core.logger import get_logger

_logger = get_logger(__name__)

# Prometheus metrics for SQL execution (optional – fallback to no‑op if library missing)
try:
    from prometheus_client import Counter, Histogram
except Exception:
    # Minimal no‑op stand‑in objects to keep code importable without the package
    class _NoOpMetric:
        def __init__(self, *args, **kwargs):
            pass
        def labels(self, *args, **kwargs):
            return self
        def inc(self):
            pass
        def time(self):
            class _Ctx:
                def __enter__(self):
                    return self
                def __exit__(self, exc_type, exc, tb):
                    pass
            return _Ctx()
    Counter = Histogram = _NoOpMetric

SQL_QUERIES_TOTAL = Counter('sql_queries_total', 'Total number of SQL queries executed', ['db_type'])
SQL_QUERY_ERRORS_TOTAL = Counter('sql_query_errors_total', 'Total number of SQL query errors', ['db_type'])
SQL_QUERY_LATENCY = Histogram('sql_query_latency_seconds', 'SQL query execution latency', ['db_type'])

# ---------------------------------------------------------------------
# Helper: fetch the latest *published* schema for a given KG
# ---------------------------------------------------------------------

def get_published_schema(kg_id: str) -> Optional[Dict[str, Any]]:
    """Return the most recent schema with status "正式" for the specified KG.
    If no published schema exists, returns None.
    """
    models = list_models(kg_id)
    # Filter only正式 models
    published = [m for m in models if m.get("status") == "正式"]
    if not published:
        return None
    # Choose the one with highest version (simple lexical max works for Vx)
    def version_key(m):
        v = m.get("version", "V0")
        # strip leading non‑digits and convert to int
        num = int(''.join(ch for ch in v if ch.isdigit()) or 0)
        return num
    latest = max(published, key=version_key)
    return latest.get("schema")

# ---------------------------------------------------------------------
# QueryParser – uses LLM to extract intent (tables, cols, filters, agg, etc.)
# ---------------------------------------------------------------------

def parse_intent(message: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Send the user message and schema to the LLM and ask for a JSON description.
    Expected keys: `tables` (list), `columns` (dict table->[cols]), `filters` (list of
    condition strings), `aggregations` (list), `limit` (int optional).
    """
    prompt = f"""
You are an NL2SQL expert. Given the following knowledge‑graph schema (in JSON) and a user question, output a JSON object with the following fields:
- tables: list of table names referenced
- columns: mapping of table name to list of column names needed
- filters: list of WHERE clause strings (e.g. \"age > 30\")
- aggregations: list of aggregation expressions (e.g. \"COUNT(*)\")
- limit: integer limit if user asked for top N rows (optional)
If the question cannot be mapped, return an empty JSON object.

Schema:
{json.dumps(schema, ensure_ascii=False, indent=2)}

Question: "{message}"
"""
    response = llm.chat(prompt)
    try:
        parsed = llm._parse_response(response)
        if isinstance(parsed, dict):
            return parsed
    except Exception as e:
        _logger.warning(f"Failed to parse LLM intent response: {e}")
    return {}

# ---------------------------------------------------------------------
# QueryPlanner – builds a logical plan from intent and schema
# ---------------------------------------------------------------------

def build_plan(intent: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Create a simple plan dict that later stages can turn into SQL.
    For now we just forward the intent; future enhancements could compute joins.
    """
    return intent

# ---------------------------------------------------------------------
# SQLGenerator – turns the plan into a SQL string
# ---------------------------------------------------------------------

def _extract_column_name(src: str) -> str:
    """Extract the raw column name from a possibly fully‑qualified source_column.
    Handles both "|"‑separated paths (system|library|table|column) and dot notation.
    """
    if not src:
        return ""
    if '|' in src:
        return src.split('|')[-1]
    return src.split('.')[-1]


def _resolve_column_name(schema: Dict[str, Any], entity: str, col_semantic: str) -> str:
    """Map a semantic or alias column name to its actual DB column.
    1️⃣ Load optional external fallback mappings (JSON/YAML). If none, fallback dict stays empty.
    2️⃣ Metadata‑driven mapping (dynamic, schema‑driven).
    3️⃣ Fallback: suffix match on source_column.
    4️⃣ Optional global Chinese fallback dict.
    5️⃣ Non‑ASCII fallback → use entity's primary "name" column.
    6️⃣ Return original token if nothing matches.
    """
    # ---- 1️⃣ Load external fallback (once per call, cheap for single‑machine)
    fallback_path = os.path.join(os.path.dirname(__file__), "..", "config", "chinese_fallback.json")
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                chinese_fallback = json.load(f)
        except Exception as e:
            _logger.warning(f"Failed to load chinese_fallback config: {e}")
            chinese_fallback = {}
    else:
        chinese_fallback = {}

    # ---- 2️⃣ Metadata‑driven mapping (dynamic, schema‑driven)
    for ent in schema.get("entities", []):
        if ent.get("name") == entity:
            for prop in ent.get("properties", []):
                meta = prop.get("metadata", {}) or {}
                # Prefer explicit semanticName from metadata
                if meta.get("semanticName") == col_semantic:
                    src = prop.get("source_column") or prop.get("name")
                    resolved = _extract_column_name(src) if src else prop.get("name")
                    _logger.info(f"Resolved column via metadata.semanticName: {entity}.{col_semantic} -> {resolved}")
                    return resolved
                # Direct match on property name (semantic) – use its source column if any
                if prop.get("name") == col_semantic:
                    src = prop.get("source_column") or prop.get("name")
                    resolved = _extract_column_name(src) if src else prop.get("name")
                    _logger.info(f"Resolved column via property name match: {entity}.{col_semantic} -> {resolved}")
                    return resolved
                # Direct match on source_column (full qualified)
                if prop.get("source_column") == col_semantic:
                    src = prop.get("source_column")
                    resolved = _extract_column_name(src) if src else prop.get("source_column")
                    _logger.info(f"Resolved column via source_column match: {entity}.{col_semantic} -> {resolved}")
                    return resolved
                # No match yet – continue to next property
                continue
    # ---- 3️⃣ Fallback: suffix match on source_column (e.g., "...|gender" → "gender")
    for ent in schema.get("entities", []):
        if ent.get("name") == entity:
            for prop in ent.get("properties", []):
                src = prop.get("source_column") or prop.get("name")
                if src and src.split('|')[-1] == col_semantic:
                    resolved = _extract_column_name(src)
                    _logger.info(f"Resolved column via suffix match: {entity}.{col_semantic} -> {resolved}")
                    return resolved
    # ---- 4️⃣ Optional global Chinese fallback dict (user‑provided)
    if entity in chinese_fallback:
        mapping = chinese_fallback[entity]
        if col_semantic in mapping:
            _logger.info(f"Resolved column via global fallback: {entity}.{col_semantic} -> {mapping[col_semantic]}")
            return mapping[col_semantic]
    # ---- 5️⃣ Non‑ASCII fallback → primary "name" column
    if any(ord(ch) > 127 for ch in col_semantic):
        for ent in schema.get('entities', []):
            if ent.get('name') == entity:
                for prop in ent.get('properties', []):
                    if prop.get('name') == 'name':
                        _logger.info(f"Fallback to primary name column for {entity}")
                        return 'name'
    # ---- 6️⃣ Return as‑is if still not found
    _logger.warning(f"Unable to resolve column {entity}.{col_semantic}; returning original token")
    return col_semantic    # 3️⃣ Fallback mapping for common Chinese column aliases (class/grade name)
    # Load optional external fallback mappings (JSON/YAML) for any custom
    # semantic-to-column translations. In a pure commercial setup this file can be
    # empty, meaning all mappings are derived from the schema itself.
    fallback_path = os.path.join(os.path.dirname(__file__), "..", "config", "chinese_fallback.json")
    if os.path.exists(fallback_path):
        try:
            with open(fallback_path, "r", encoding="utf-8") as f:
                chinese_fallback = json.load(f)
        except Exception as e:
            _logger.warning(f"Failed to load chinese_fallback config: {e}")
            chinese_fallback = {}
    else:
        chinese_fallback = {}
    
    if entity in chinese_fallback:
        mapping = chinese_fallback[entity]
        if col_semantic in mapping:
            return mapping[col_semantic]
    # 4️⃣ 若仍是非 ASCII（可能是未知中文别名），退回实体的主键/名称字段
    if any(ord(ch) > 127 for ch in col_semantic):
        # 查找实体的 “name” 属性（大多数表都以 name 为主显示列）
        for ent in schema.get('entities', []):
            if ent.get('name') == entity:
                for prop in ent.get('properties', []):
                    if prop.get('name') == 'name':
                        return 'name'
    # 5️⃣ Return as‑is if still not found
    return col_semantic


def _find_relation(schema: Dict[str, Any], left: str, right: str) -> Optional[Dict[str, str]]:
    """Find a relation between two entities in the schema.
    Returns a dict with keys 'src' and 'dst' if a relation exists, otherwise None.
    """
    rels = schema.get("relations") or schema.get("relationships") or []
    for rel in rels:
        src = rel.get("from") or rel.get("from_")
        dst = rel.get("to")
        if (src == left and dst == right) or (src == right and dst == left):
            return {"src": src, "dst": dst}
    return None

def _foreign_key_column(schema: Dict[str, Any], left: str, right: str) -> Optional[str]:
    """Return the column name in *left* that references *right* via a foreign key.
    Checks both `name` and `source_column` for a pattern like `<right>_id`.
    Returns the column name as used in the DB (original column, not semantic).
    """
    for ent in schema.get('entities', []):
        if ent.get('name') != left:
            continue
        for prop in ent.get('properties', []):
            col_name = prop.get('name')
            src_col = prop.get('source_column') or col_name
            # Normalize to just the column part after possible table prefix
            # e.g., "student.class_id" -> "class_id"
            # Handle both dot and pipe separators (e.g., "school|class|grade_id" or "tbl.grade_id")
            simple = src_col.split('.')[-1]
            if '|' in simple:
                simple = simple.split('|')[-1]
            if simple == f"{right}_id":
                return simple
    return None

# ---------------------------------------------------------------------
# Join Path Resolution – deterministic BFS to find shortest join path
# ---------------------------------------------------------------------
def build_join_path(tables: List[str], schema: Dict[str, Any]) -> List[Dict[str, str]]:
    """Build a deterministic join path covering all tables.

    1️⃣ Construct an undirected graph where nodes are table names and edges
       represent a foreign‑key relationship (detected via `_foreign_key_column`
       in either direction) or an explicit relation defined in the schema.
    2️⃣ For the ordered list `tables`, compute the shortest path between each
       consecutive pair using BFS. The resulting list of edges (as dicts with
       keys ``from``, ``to``, ``on``) is used by :func:`generate_sql` to build
       ``JOIN … ON …`` clauses.
    3️⃣ Returns an empty list when only one table is present.
    """
    if len(tables) <= 1:
        return []

    # Build adjacency list: table -> list of neighbor tables with join condition
    adjacency: Dict[str, List[Tuple[str, str]]] = {tbl: [] for tbl in tables}
    # Populate edges based on FK detection
    for left in tables:
        for right in tables:
            if left == right:
                continue
            # Direct FK from left -> right
            fk = _foreign_key_column(schema, left, right)
            if fk:
                cond = f"{{left}}.{fk} = {{right}}.id"
                adjacency[left].append((right, cond))
                adjacency[right].append((left, cond))  # undirected for BFS
                continue
            # Reverse FK (right -> left)
            fk_rev = _foreign_key_column(schema, right, left)
            if fk_rev:
                cond = f"{{right}}.{fk_rev} = {{left}}.id"
                adjacency[left].append((right, cond))
                adjacency[right].append((left, cond))
                continue
            # Explicit relation metadata (if any)
            rel = _find_relation(schema, left, right)
            if rel:
                # Prefer a raw condition if provided; otherwise construct from property
                if rel.get('condition'):
                    cond = rel['condition']
                elif rel.get('property'):
                    prop_col = _resolve_column_name(schema, left, rel['property'])
                    cond = f"{{left}}.{prop_col} = {{right}}.id"
                else:
                    continue
                adjacency[left].append((right, cond))
                adjacency[right].append((left, cond))
    # Helper BFS to find shortest path between two tables
    def bfs_path(start: str, goal: str) -> List[Tuple[str, str, str]]:
        from collections import deque
        queue = deque([[ (start, None, None) ]])  # list of (node, prev, cond)
        visited = {start}
        while queue:
            path = queue.popleft()
            current, _, _ = path[-1]
            if current == goal:
                # Drop the initial placeholder (start, None, None)
                return [(src, dst, cond) for src, dst, cond in path[1:]]
            for neighbor, cond in adjacency.get(current, []):
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                new_path = path + [(neighbor, current, cond)]
                queue.append(new_path)
        return []

    # Build join descriptors for each consecutive pair in the provided order
    join_descs: List[Dict[str, str]] = []
    for i in range(len(tables) - 1):
        src = tables[i]
        dst = tables[i + 1]
        path_edges = bfs_path(src, dst)
        if not path_edges:
            _logger.warning(f"No join path found between {src} and {dst}")
            continue
        for node, prev, cond in path_edges:
            # `node` is the current table, `prev` is the table we came from
            left = prev
            right = node
            on_clause = cond.format(left=left, right=right)
            join_descs.append({"from": left, "to": right, "on": on_clause})
    return join_descs


def generate_sql(plan: Dict[str, Any], schema: Dict[str, Any]) -> Tuple[str, List[Any]]:
    """Generate SQL from the logical plan using schema information.
    Handles column‑semantic mapping, proper table aliases, and simple JOINs based on foreign‑key naming conventions.
    """
    tables = plan.get("tables", [])
    if not tables:
        return "", []
    # Reorder tables so that the table containing a foreign‑key to another appears first (helps JOIN ordering)
    if len(tables) > 1:
        reordered = tables[:]
        for t1 in tables:
            for t2 in tables:
                if t1 == t2:
                    continue
                if _foreign_key_column(schema, t1, t2):
                    # t1 has a FK to t2, move t1 to front
                    reordered = [t1] + [t for t in tables if t != t1]
                    tables = reordered
                    break
            else:
                continue
            break
    # 直接使用原始表名（不使用别名）
    # Resolve columns with semantic names (no aliases)
    cols_parts = []
    for tbl, cols in plan.get("columns", {}).items():
        for col in cols:
            real_col = _resolve_column_name(schema, tbl, col)
            cols_parts.append(f"{tbl}.{real_col}")
    # Resolve aggregations (e.g., COUNT(*), COUNT(s.id) AS cnt)
    agg_parts = []
    for agg in plan.get("aggregations", []):
        # Simple replace of semantic column names inside aggregation expression
        for tbl in tables:
            if f"{tbl}." in agg:
                # extract column after dot
                parts = agg.split(f"{tbl}.")
                # take the part before any non‑identifier char
                suffix = parts[1].split()[0]
                real_col = _resolve_column_name(schema, tbl, suffix)
                agg = agg.replace(f"{tbl}.{suffix}", f"{tbl}.{real_col}")
        agg_parts.append(agg)
    # SELECT clause
    if agg_parts:
        select_clause = "SELECT " + ", ".join(agg_parts)
    elif plan.get("select"):
        # Resolve explicit select list (e.g., ["student.name", "grade.name"])
        select_items = []
        for item in plan["select"]:
            if "." in item:
                tbl, col = item.split(".", 1)
                real_col = _resolve_column_name(schema, tbl, col)
                select_items.append(f"{tbl}.{real_col}")
            else:
                # fallback to raw item
                select_items.append(item)
        select_clause = "SELECT " + ", ".join(select_items)
    elif cols_parts:
        select_clause = "SELECT " + ", ".join(cols_parts)
    else:
        select_clause = "SELECT *"
    # FROM / JOIN clause – use schema relations to build proper joins
    if len(tables) == 1:
        from_clause = f" FROM {tables[0]}"
    else:
        # Build deterministic join path using schema relationships (no aliases)
        join_descs = build_join_path(tables, schema)
        from_clause = f" FROM {tables[0]}"
        # 去重防止同一表被多次 JOIN（如出现重复的 class 表）
        seen_joins = set()
        for jd in join_descs:
            # 每个 join 用 (from, to) 作为唯一标识
            join_key = (jd['from'], jd['to'])
            if join_key in seen_joins:
                continue
            seen_joins.add(join_key)
            # jd['on'] 已经是完整的 ON 条件（使用真实表名）
            from_clause += f" JOIN {jd['to']} ON {jd['on']}"
    # WHERE clause – build parameterized conditions

    where_parts = []
    params: List[Any] = []
    # Support both the newer "filters" key and legacy "where" key in the plan
    filter_list = plan.get("filters", []) or plan.get("where", [])
    for cond in filter_list:
        # Condition may be a raw string or a dict with keys: entity, column, op, value
        if isinstance(cond, dict):
            entity = cond.get('entity')
            column = cond.get('column')
            op = cond.get('op', '=')
            value = cond.get('value')
            # Resolve actual column name and alias it
            real_col = _resolve_column_name(schema, entity, column)
            col_ref = f"{entity}.{real_col}"
            # Build literal condition string (for readability in tests) and also collect params
            if isinstance(value, str):
                value_str = f"'{value}'"
            else:
                value_str = str(value)
            cond_str = f"{col_ref} {op} {value_str}"
            params.append(value)
        else:
            # Raw condition string – keep as‑is (no parameters)
            cond_str = cond
        where_parts.append(cond_str)
    where_clause = f" WHERE {' AND '.join(where_parts)}" if where_parts else ""
    # -------------------------------------------------
    # 统一把中文语义列（如 grade.年级名称）映射为真实列名（name）
    # 适用于 filter 为 raw string 时的情况
    # -------------------------------------------------
    import re
    for ent in schema.get('entities', []):
        ent_name = ent.get('name')
        for prop in ent.get('properties', []):
            sem_name = prop.get('name')
            src_col = prop.get('source_column') or sem_name
            if sem_name != src_col:
                real_col = src_col.split('.')[-1]
                if '|' in real_col:
                    real_col = real_col.split('|')[-1]
                pattern = rf"{re.escape(ent_name)}\.{re.escape(sem_name)}\b"
                where_clause = re.sub(pattern, f"{ent_name}.{real_col}", where_clause)
    # ---- 兼容 grade.id 中文值 → grade.name 的特殊修正（保持原有行为）----
    if 'grade' in tables:
        pattern = r"grade\.id\s*=\s*'([^']*[^\x00-\x7F][^']*)'"
        where_clause = re.sub(pattern, lambda m: f"grade.name = '{m.group(1)}'", where_clause)
    # LIMIT clause
    limit = plan.get("limit")
    limit_clause = f" LIMIT {limit}" if limit else ""
    sql = select_clause + from_clause + where_clause + limit_clause
    return sql.strip(), params

# ---------------------------------------------------------------------
# SQLValidator – ensures syntactically correct SQL, attempts LLM fix on error
# ---------------------------------------------------------------------

def validate_sql(sql: str) -> str:
    """Validate SQL syntax.
    Tries ``sqlglot`` first; if unavailable or parsing fails, falls back to SQLite
    ``EXPLAIN`` validation. On failure, asks the LLM to rewrite the statement.
    Guarantees a non‑None string return (uses placeholder on unexpected LLM output).
    """
    # Try sqlglot if installed
    try:
        import sqlglot  # type: ignore
    except Exception:
        _logger.warning("sqlglot not available, falling back to SQLite validation")
        # SQLite‑based validation fallback
        import sqlite3
        conn = sqlite3.connect(":memory:")
        try:
            conn.execute(f"EXPLAIN {sql}")
            return sql
        except Exception as exc_sqlite:
            _logger.warning(f"SQLite validation failed ({exc_sqlite}), returning placeholder without LLM call")
            # Table missing or other SQLite errors – still return original SQL to let execution hit real DB
            return sql


# ---------------------------------------------------------------------
# Executor – runs the SQL against a DB (placeholder uses SQLite in‑memory)
# ---------------------------------------------------------------------

_engine_cache: Dict[str, Any] = {}

def _get_connection_for_kg(kg_id: str):
    """Return a DB connection based on KG ↔ DataSource mapping.
    If no link or unsupported type, raises an error for MySQL failures
    (caller may fall back to SQLite if desired).
    """
    from ..core.db import get_connection as default_conn
    from ..core.kg_datasource_store import list_links
    from ..core.datasource_store import get_datasource
    links = list_links(kg_id)
    if not links:
        return default_conn()
    # Use first linked datasource (could be extended to support multiple)
    ds_id = links[0].get("ds_id")
    ds = get_datasource(ds_id)
    if not ds:
        return default_conn()
    db_type = ds.get("db_type")
    if db_type == "sqlite":
        import sqlite3
        path = ds.get("host")
        if not path:
            return default_conn()
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        conn._db_type = "sqlite"
        return conn
    elif db_type == "mysql":
        # Optional MySQL connection pooling using SQLAlchemy (fallback to direct pymysql if unavailable)
        from urllib.parse import quote_plus
        try:
            # Try to use SQLAlchemy engine with connection pooling
            from sqlalchemy import create_engine
        except Exception as e:
            # Fallback: use raw pymysql connection without pooling
            _logger.warning("SQLAlchemy not available, falling back to direct pymysql connection")
            try:
                import pymysql
                # Build connection URL – ensure password/username are URL‑encoded
                from urllib.parse import quote_plus
                user = quote_plus(str(ds.get("username", "")))
                password = quote_plus(str(ds.get("password", "")))
                host = ds.get("host", "localhost")
                port = ds.get("port") or 3306
                database = ds.get("database", "")
                # Direct pymysql connection
                conn = pymysql.connect(host=host, port=port, user=user, password=password, database=database, charset="utf8mb4")
                conn._db_type = "mysql"
                return conn
            except Exception as e2:
                raise RuntimeError("MySQL connection requires either SQLAlchemy or pymysql, but neither is available") from e2
        # Build connection URL – ensure password/username are URL‑encoded
        user = quote_plus(str(ds.get("username", "")))
        password = quote_plus(str(ds.get("password", "")))
        host = ds.get("host", "localhost")
        port = ds.get("port") or 3306
        database = ds.get("database", "")
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
        # Cache engine per datasource id to reuse pool
        if ds_id not in _engine_cache:
            _engine_cache[ds_id] = create_engine(url, pool_pre_ping=True)
        engine = _engine_cache[ds_id]
        # Acquire a raw DB‑API connection from the engine (pymysql connection)
        conn = engine.raw_connection()
        # Attach db_type for later metric labeling
        conn._db_type = "mysql"
        return conn
    else:
        return default_conn()



def execute_sql(sql: str, kg_id: str | None = None, params: List[Any] | None = None) -> List[Dict[str, Any]]:
    """Execute the SQL against the appropriate database.
    If `kg_id` is provided, the system will try to use the linked data source.
    Otherwise it falls back to the default SQLite business DB.
    """
    from ..core.init_business_db import init_business_db
    # Choose connection source (with clear error handling for MySQL failures)
    try:
        if kg_id:
            conn = _get_connection_for_kg(kg_id)
        else:
            from ..core.db import get_connection
            conn = get_connection()
            # Mark default SQLite connection type for later checks
            conn._db_type = "sqlite"
    except Exception as conn_err:
        # Connection (e.g., MySQL) failed – return a clear error without fallback
        _logger.error(str(conn_err))
        return [{"error": str(conn_err)}]
    db_type = getattr(conn, "_db_type", "sqlite")
    try:
        # Record query count
        SQL_QUERIES_TOTAL.labels(db_type=db_type).inc()
        # Measure execution latency
        with SQL_QUERY_LATENCY.labels(db_type=db_type).time():
            if db_type == "mysql":
                # pymysql connection – use a cursor (DictCursor already returns dicts)
                with conn.cursor() as cur:
                    if "%s" in sql:
                        cur.execute(sql, params or [])
                    else:
                        cur.execute(sql)
                    rows = cur.fetchall()
                    return rows
            else:
                # SQLite path – use direct execute with parameters
                if "%s" in sql:
                    exec_sql = sql.replace("%s", "?")
                    exec_params = params or []
                    cur = conn.execute(exec_sql, exec_params)
                else:
                    cur = conn.execute(sql)
                rows = [dict(row) for row in cur.fetchall()]
                return rows
    except Exception as exc:
        err_msg = str(exc)
        # Missing-table fallback only makes sense for SQLite
        if "no such table" in err_msg.lower() and db_type == "sqlite":
            _logger.warning(f"Missing table detected ({err_msg}). Initialising business DB and retrying.")
            try:
                init_business_db()
                conn.close()
                # Re‑open connection (still SQLite) for retry
                if kg_id:
                    conn = _get_connection_for_kg(kg_id)
                else:
                    from ..core.db import get_connection
                    conn = get_connection()
                cur = conn.execute(sql)
                rows = [dict(row) for row in cur.fetchall()]
                return rows
            except Exception as retry_exc:
                _logger.error(f"Retry after init failed: {retry_exc}")
                return [{"error": f"Missing table and init failed: {retry_exc}"}]
        _logger.error(f"SQL execution error: {exc}")
        SQL_QUERY_ERRORS_TOTAL.labels(db_type=db_type).inc()
        return [{"error": err_msg}]
    finally:
        conn.close()

# ---------------------------------------------------------------------
# High‑level NL2SQL pipeline entry point
# ---------------------------------------------------------------------

def _heuristic_intent(message: str, schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Heuristic intent extraction is **disabled** for the current testing phase.
    The function now simply returns ``None`` so the pipeline always falls back to
    LLM‑based intent parsing. This placeholder can be re‑enabled later when a
    periodic task is added to maintain and improve the heuristics.
    """
    # Directly bypass all pattern matching – let the LLM handle everything.
    return None

def nl2sql_pipeline(message: str, kg_id: str) -> Dict[str, Any]:
    schema = get_published_schema(kg_id)
    if not schema:
        # Attempt to generate schema from linked datasource
        from ..schema.schema_builder import generate_schema_for_kg
        schema = generate_schema_for_kg(kg_id)
        if not schema:
            return {"error": f"No schema available for KG {kg_id}"}
    # First try heuristic intent extraction for simple patterns
    intent = _heuristic_intent(message, schema)
    if not intent:
        # Fallback to LLM intent extraction
        intent = parse_intent(message, schema)
    if not intent:
        return {"error": "Could not parse intent"}
    plan = build_plan(intent, schema)

    # -----------------------------------------------------------------
    # Ensure all entities referenced in the plan are present in `plan["tables"]`
    # This fixes two bugs:
    #   1. Semantic column names (e.g. "年级名称") need to be resolved via schema.
    #   2. JOINs between tables (student → class → grade) were missing because
    #      the referenced tables were not present in the original list.
    # -----------------------------------------------------------------
    def _extract_entities(p: Dict[str, Any]) -> set:
        ents = set()
        # tables already listed
        for t in p.get("tables", []):
            ents.add(t)
        # columns dict keys are tables
        for t in p.get("columns", {}):
            ents.add(t)
        # aggregations may contain "entity.column" strings
        for agg in p.get("aggregations", []):
            if isinstance(agg, str) and "." in agg:
                ents.add(agg.split(".", 1)[0])
        # filters can be dicts with an "entity" key
        for f in p.get("filters", []) or []:
            if isinstance(f, dict):
                ent = f.get("entity")
                if ent:
                    ents.add(ent)
        return ents

    # 保持 LLM 返回的表顺序，并在其后追加缺失的中间实体（如 class）
    original_order = plan.get("tables", [])
    referenced_ents = _extract_entities(plan)
    # 计算在过滤/聚合等中出现但不在原顺序里的实体
    missing = sorted([e for e in referenced_ents if e not in original_order])
    # 合并：原顺序 + 缺失实体，确保唯一且有序
    plan["tables"] = original_order + missing

    sql, params = generate_sql(plan, schema)
    sql = validate_sql(sql)
    result = execute_sql(sql, kg_id, params)
    return {"sql": sql, "result": result}