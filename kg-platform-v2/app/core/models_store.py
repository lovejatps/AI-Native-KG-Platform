"""Model storage using Neo4j.
Each model node has label `Model` with properties:
- id (str, uuid)
- kg_id (str)
- version (str)
- created_at (ISO timestamp)
- status ("草稿" or "正式")
- schema (JSON string)
"""

import json, uuid, datetime
from typing import List, Dict, Any, Optional, Mapping
from ..graph.neo4j_client import Neo4jClient
from ..core.logger import get_logger

# ---------------------------------------------------------------------
# ① sync_schema_to_graph(kg_id, schema)
# ---------------------------------------------------------------------
def sync_schema_to_graph(kg_id: str, schema: Dict[str, Any]) -> None:
    """将模型的实体与关系同步到 Neo4j（或 fallback 存储）。

    1. 清空当前 KG 的所有 Entity 节点（fallback 中直接删除内存库）
    2. 为每个 entity 创建 ``:Entity`` 节点，保留 ``name`` 与 ``type`` 字段。
    3. 为每条外键（relations/relationships）创建统一的 ``REL`` 边，
       并在属性 ``type`` 中记录原始 FK 类型（默认 ``FK``）。
    该函数在模型**创建**、**编辑**、**发布** 等会改变 schema 的场景调用，
    保证前端通过 ``/entity/{name}`` 查询时能够获得最新的 1‑跳关系。
    """
    client = Neo4jClient()
    # ---- 1️⃣ 清理旧数据 ----
    client.run("MATCH (n:Entity) DETACH DELETE n")
    # fallback store also keeps relationships in a list; clear it explicitly
    if getattr(client, "_fallback", False):
        client._relationships.clear()

    # ---- 2️⃣ 写入实体节点 ----
    for ent in schema.get("entities", []):
        # Tag schema‑origin entities for isolation
        client.run(
            "MERGE (e:Entity {name: $name}) SET e.type = $type, e.origin = $origin",
            {"name": ent["name"], "type": ent.get("type", "Table"), "origin": "schema"},
        )

    # ---- 3️⃣ 写入关系 ----
    rels = schema.get("relations") or schema.get("relationships") or []
    for rel in rels:
        src = rel["from"].split(".")[0]
        dst = rel["to"].split(".")[0]
        # Use relationship type as Neo4j label (back‑ticked to support non‑ASCII)
        rel_type = rel.get("type", "FK")
        rel_query = f"""
            MATCH (a:Entity {{name: $a}})
            MATCH (b:Entity {{name: $b}})
            MERGE (a)-[r:`{rel_type}`]->(b)
            SET r.origin = $origin
            """
        client.run(rel_query, {"a": src, "b": dst, "origin": "schema"})


# Singleton Neo4j client (fallback works in tests)
_neo = Neo4jClient()

def _serialize_schema(schema: Dict[str, Any]) -> str:
    """Store schema as a JSON string for Neo4j compatibility."""
    return json.dumps(schema, ensure_ascii=False)

def _deserialize_schema(schema_str: str) -> Dict[str, Any]:
    return json.loads(schema_str)

# ---------------------------------------------------------------------
# Helper queries
# ---------------------------------------------------------------------

def _run(query: str, params: Optional[Dict[str, Any]] = None) -> List[Mapping[str, Any]]:
    return _neo.run(query, params or {})

# ---------------------------------------------------------------------
# Version handling
# ---------------------------------------------------------------------

def _next_version(existing_versions: List[str]) -> str:
    """Return a simple sequential version string.
    - Starts at "V1".
    - If existing versions are like "V2", "V3", picks the max and adds 1.
    """
    if not existing_versions:
        return "V1"
    max_num = 0
    for ver in existing_versions:
        try:
            # Strip any leading non‑digit characters (e.g., 'V')
            num_part = ''.join(ch for ch in ver if ch.isdigit())
            num = int(num_part) if num_part else 0
            if num > max_num:
                max_num = num
        except Exception:
            continue
    return f"V{max_num + 1}"

# ---------------------------------------------------------------------
# CRUD operations (Neo4j)
# ---------------------------------------------------------------------

def create_model(kg_id: str, schema: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new model for a KG (status defaults to 草稿)"""
    # Determine next version for this KG
    records = _run("MATCH (m:Model {kg_id: $kg_id}) RETURN m.version AS version", {"kg_id": kg_id})
    existing = [rec["version"] for rec in records if rec.get("version")]
    version = _next_version(existing)
    model_id = uuid.uuid4().hex
    now = datetime.datetime.utcnow().isoformat()
    node_props = {
        "id": model_id,
        "kg_id": kg_id,
        "version": version,
        "created_at": now,
        "status": "草稿",
        "schema": _serialize_schema(schema),
    }
    _run("MERGE (m:Model {id: $id}) SET m += $props", {"id": model_id, "props": node_props})
    # Return in original shape (schema as dict)
    model = node_props.copy()
    model["schema"] = schema
    return model

def list_models(kg_id: str) -> List[Dict[str, Any]]:
    """List models for a specific KG (existing function)."""
    records = _run("MATCH (m:Model {kg_id: $kg_id}) RETURN m", {"kg_id": kg_id})
    result = []
    for rec in records:
        m = rec["m"] if isinstance(rec, dict) else rec
        # m may be a dict of properties
        schema_str = m.get("schema", "{}")
        m_out = dict(m)
        m_out["schema"] = _deserialize_schema(schema_str)
        result.append(m_out)
    # Fallback: if no records (fallback store), filter in-memory store
    if not result:
        for m in _neo._store.values():
            if m.get("kg_id") == kg_id:
                schema_str = m.get("schema", "{}")
                m_out = dict(m)
                m_out["schema"] = _deserialize_schema(schema_str)
                result.append(m_out)
    return result

def get_model(model_id: str) -> Optional[Dict[str, Any]]:
    records = _run("MATCH (m:Model {id: $id}) RETURN m", {"id": model_id})
    if records:
        m = records[0]["m"] if isinstance(records[0], dict) else records[0]
    else:
        # Fallback to in‑memory store
        m = _neo._store.get(model_id)
        if not m:
            return None
    schema_str = m.get("schema", "{}")
    out = dict(m)
    out["schema"] = _deserialize_schema(schema_str)
    return out

def edit_model(model_id: str, new_schema: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    # Validate schema basics
    if not isinstance(new_schema, dict) or "entities" not in new_schema:
        raise ValueError("Missing required key: 'entities'")
    # Fetch existing model
    existing = get_model(model_id)
    if not existing:
        return None
    # Preserve relations if not supplied
    old_schema = existing.get("schema", {})
    if "relations" not in new_schema:
        new_schema["relations"] = old_schema.get("relations", [])

    # Update node
    _run(
        "MATCH (m:Model {id: $id}) SET m.schema = $schema, m.status = '草稿', m.updated_at = $now",
        {
            "id": model_id,
            "schema": _serialize_schema(new_schema),
            "now": datetime.datetime.utcnow().isoformat(),
        },
    )
    # Ensure fallback store reflects changes (in case of in‑memory mode)
    if model_id in _neo._store:
        node = _neo._store[model_id]
        node["schema"] = _serialize_schema(new_schema)
        node["status"] = "草稿"
        node["updated_at"] = datetime.datetime.utcnow().isoformat()
        _neo._store[model_id] = node
    # Return updated representation
    updated = get_model(model_id)
    return updated

def delete_model(model_id: str) -> bool:
    _run("MATCH (m:Model {id: $id}) DETACH DELETE m", {"id": model_id})
    # Verify deletion
    return get_model(model_id) is None

# New helper: list all models regardless of KG (used when KG ID not provided)
def list_all_models() -> List[Dict[str, Any]]:
    """Return all models across all KG (fallback to in‑memory store)."""
    records = _run("MATCH (m:Model) RETURN m")
    result = []
    for rec in records:
        m = rec["m"] if isinstance(rec, dict) else rec
        schema_str = m.get("schema", "{}")
        m_out = dict(m)
        m_out["schema"] = _deserialize_schema(schema_str)
        result.append(m_out)
    if not result:
        for m in _neo._store.values():
            schema_str = m.get("schema", "{}")
            m_out = dict(m)
            m_out["schema"] = _deserialize_schema(schema_str)
            result.append(m_out)
    return result
    _run("MATCH (m:Model {id: $id}) DETACH DELETE m", {"id": model_id})
    # Verify deletion
    return get_model(model_id) is None

def publish_model(kg_id: str, model_id: str) -> Optional[Dict[str, Any]]:
    target = get_model(model_id)
    if not target or target.get("kg_id") != kg_id:
        return None
    # Demote any other published model for this KG
    _run(
        "MATCH (m:Model {kg_id: $kg_id, status: '正式'}) SET m.status = '草稿'",
        {"kg_id": kg_id},
    )
    # Promote target
    _run(
        "MATCH (m:Model {id: $id}) SET m.status = '正式'",
        {"id": model_id},
    )
    return get_model(model_id)

def rollback_model(kg_id: str, model_id: str) -> Optional[Dict[str, Any]]:
    model = get_model(model_id)
    if not model or model.get("kg_id") != kg_id or model.get("status") != "正式":
        return None
    _run(
        "MATCH (m:Model {id: $id}) SET m.status = '草稿', m.updated_at = $now",
        {"id": model_id, "now": datetime.datetime.utcnow().isoformat()},
    )
    return get_model(model_id)

# ---------------------------------------------------------------------
# Legacy helper – generate schema (unchanged logic, returns dict)
# ---------------------------------------------------------------------

def generate_schema_for_kg(kg_id: str) -> Dict[str, Any]:
    """Generate a schema (model) for the given KG **based on the linked data sources**.

    1️⃣ 读取 KG ↔ DataSource 链接；
    2️⃣ 对每个关联的数据源调用 ``get_schema`` 获得库‑表‑字段结构；
    3️⃣ 把每张表映射为 ``entity``（type="Table"），列信息放在 ``properties``；
    4️⃣ **使用 LLM 为每个列生成自然语言描述**（中文简要说明）；
    5️⃣ 暂不生成跨表 ``relations``（后续可基于外键扩展）。
    6️⃣ 返回符合 PRD‑V3 要求的 ``{entities, relations, relationships}`` 结构。
    """
    # 1️⃣ 读取 KG ↔ DataSource 链接
    from ..core.kg_datasource_store import list_links
    from ..core.datasource_store import get_schema
    from ..core.llm import llm  # LLM 用于生成列描述

    links = list_links(kg_id)
    # 使用 dict 先收集实体，避免同名表重复（即使同一数据源被多次关联）
    entity_map: Dict[str, Dict[str, Any]] = {}
    # 直接遍历所有 link，不提前过滤 ds_id，确保即使同一数据源被多次关联且表选择不同，也能合并所有表
    for link in links:
        ds_id = link.get("ds_id")
        if not ds_id:
            continue
        # 2️⃣ 获取数据源完整结构
        ds_schema = get_schema(ds_id)
        tables = ds_schema.get("tables", [])
        # 3️⃣ 只处理用户在链接中指定的表（若未指定则全部）
        selected_tables = set(link.get("tables", [])) or {t["name"] for t in tables}
        for tbl in tables:
            tbl_name = tbl.get("name")
            if tbl_name not in selected_tables:
                continue
            # 将列信息转化为数组形式，兼容前端 UI（e.properties 需要是数组）
            column_props: List[Dict[str, Any]] = []
            for col in tbl.get("columns", []):
                col_name = col.get("name")
                col_type = col.get("type")
                col_comment = col.get("comment", "")
                # 4️⃣ LLM 生成自然语言描述
                prompt = (
                    f"请用简洁的中文描述以下数据库列信息，返回一句话：\n"
                    f"表名: {tbl_name}\n"
                    f"列名: {col_name}\n"
                    f"类型: {col_type}\n"
                    f"备注: {col_comment}\n"
                )
                try:
                    description = llm.chat(prompt).strip()
                except Exception as e:
                    description = f"列 {col_name}（类型 {col_type}）"  # 兜底
                column_props.append({
                    "name": col_name,
                    "type": col_type,
                    "comment": col_comment,
                    "description": description,
                })
            # 5️⃣ 合并到实体 map（按表名合并）
            if tbl_name not in entity_map:
                entity_map[tbl_name] = {"name": tbl_name, "type": "Table", "properties": column_props}
            else:
                # 合并列，防止重复列名
                existing_props = {p["name"] for p in entity_map[tbl_name]["properties"]}
                for prop in column_props:
                    if prop["name"] not in existing_props:
                        entity_map[tbl_name]["properties"].append(prop)
    # 最终实体列表
    entities = list(entity_map.values())

    # 6️⃣ 提取跨表关系（外键）
    relations: List[Dict[str, Any]] = []
    # 为每个关联的数据源获取外键信息并转化为关系
    from ..core.datasource_store import get_datasource
    for link in links:
        ds_id = link.get("ds_id")
        if not ds_id:
            continue
        ds = get_datasource(ds_id)
        if not ds:
            continue
        db_type = ds.get("db_type")
        # 重新获取该数据源的表结构，供外键遍历使用
        ds_schema = get_schema(ds_id)
        tables_fk = ds_schema.get("tables", [])
        try:
            if db_type == "sqlite":
                # SQLite 必须提供文件路径
                sqlite_path = ds.get("host")
                if not sqlite_path:
                    continue
                import sqlite3
                conn = sqlite3.connect(sqlite_path)
                cur = conn.cursor()
                # 对每张表查询外键
                for tbl in tables_fk:
                    tbl_name = tbl.get("name")
                    cur.execute(f"PRAGMA foreign_key_list('{tbl_name}')")
                    rows = cur.fetchall()
                    for row in rows:
                        # (id, seq, table, from, to, on_update, on_delete, match)
                        ref_table = row[2]
                        from_col = row[3]
                        to_col = row[4]
                        relations.append({
                            "from": f"{tbl_name}.{from_col}",
                            "to": f"{ref_table}.{to_col}",
                            "type": "FK",
                        })
                conn.close()
            elif db_type == "mysql":
                # MySQL 需要 host、database 等信息
                if not (ds.get("host") and ds.get("database")):
                    continue
                try:
                    import pymysql
                except Exception:
                    # pymysql 不可用时直接跳过
                    get_logger(__name__).warning("pymysql not installed, skipping MySQL FK extraction")
                    continue
                conn = pymysql.connect(
                    host=ds.get("host"),
                    port=ds.get("port") or 3306,
                    user=ds.get("username"),
                    password=ds.get("password"),
                    database=ds.get("database"),
                    charset="utf8mb4",
                )
                cur = conn.cursor()
                cur.execute(
                    "SELECT TABLE_NAME, COLUMN_NAME, REFERENCED_TABLE_NAME, REFERENCED_COLUMN_NAME "
                    "FROM INFORMATION_SCHEMA.KEY_COLUMN_USAGE "
                    "WHERE TABLE_SCHEMA=%s AND REFERENCED_TABLE_NAME IS NOT NULL",
                    (ds.get("database"),),
                )
                for row in cur.fetchall():
                    tbl, col, ref_tbl, ref_col = row
                    relations.append({
                        "from": f"{tbl}.{col}",
                        "to": f"{ref_tbl}.{ref_col}",
                        "type": "FK",
                    })
                conn.close()
        except Exception as e:
            # 记录但不终止整体流程
            from ..core.logger import get_logger
            get_logger(__name__).warning(f"提取外键关系失败: {e}")
            continue
    # 8️⃣ 去重关系（防止同一外键因多数据源重复出现）
    unique_rel: Dict[tuple, Dict[str, Any]] = {}
    for r in relations:
        key = (r["from"], r["to"], r["type"])  # type: ignore
        if key not in unique_rel:
            unique_rel[key] = r
    relations = list(unique_rel.values())
    # 9️⃣ 将实体与关系写入 Neo4j（fallback）以供前端路径查询使用
    client = Neo4jClient()
    # 创建实体节点
    for ent in entities:
        # Tag schema‑origin entities for isolation
        client.run(
            "MERGE (e:Entity {name: $name}) SET e.type = $type, e.origin = $origin",
            {"name": ent["name"], "type": ent.get("type", "Table"), "origin": "schema"},
        )
        # 创建关系（使用关系类型作为 Neo4j 标签）
        for rel in relations:
            src = rel["from"].split(".")[0]
            dst = rel["to"].split(".")[0]
            rel_type = rel.get("type", "FK")
            rel_query = f"""
                MATCH (a:Entity {{name: $a}})
                MATCH (b:Entity {{name: $b}})
                MERGE (a)-[r:`{rel_type}`]->(b)
            """
            client.run(rel_query, {"a": src, "b": dst})
    # 返回符合 GraphRAG 期待的完整 schema
    return {"entities": entities, "relations": relations, "relationships": relations}
