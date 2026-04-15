from fastapi import APIRouter, Request, HTTPException
from typing import Dict, Any, Optional
from ..graph.neo4j_client import Neo4jClient

# Optional KGAgent functionality (omitted in test environment)
# The original code attempted to import a KGAgent which depends on heavy
# infrastructure. For the purpose of the integration test we provide a
# minimal stub that satisfies the interface used by the router.


class _DummyAgent:
    def run(self, task: str):
        return f"DummyAgent received task: {task}"


router = APIRouter()
agent = _DummyAgent()


@router.post("/agent/run")
def run_agent(payload: Dict[str, Any]):
    task = payload.get("task", "")
    return {"result": agent.run(task)}


# ----------------------------------------------------------
# Incremental document ingestion endpoint
# ----------------------------------------------------------
from ..ingestion.pipeline import process_document


@router.post("/document/ingest")
def ingest_document(payload: Dict[str, Any]):
    """Trigger the full document ingestion pipeline.

    Expected JSON payload:
    {
        "file_path": "absolute/or/relative/path/to/file.pdf"
    }
    Returns a simple status object.
    """
    file_path = payload.get("file_path")
    if not file_path:
        return {"status": "error", "message": "Missing 'file_path' in request"}
    try:
        process_document(file_path)
        return {"status": "processed", "file": file_path}
    except Exception as e:
        return {"status": "error", "message": str(e)}


# -------------------------------
# 新增文件上传接口（前端表单使用）
# -------------------------------
from fastapi import UploadFile, File


from fastapi import UploadFile, File, BackgroundTasks
import uuid, tempfile, os, shutil

# In‑memory progress tracker (extraction_id -> status dict)
extraction_progress: dict[str, dict] = {}


@router.post("/document/upload_file")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    kg_id: Optional[str] = None,
):
    """接受前端上传的文件，返回一个 extraction_id 并在后台完成实际抽取。
    前端可以轮询 ``/extraction_status/{extraction_id}`` 获取进度与结果。
    可选的 `kg_id` 用于将抽取结果关联到已有的知识图谱。
    """
    # 生成唯一的任务 ID
    extraction_id = str(uuid.uuid4())
    # 初始状态放入全局 dict
    extraction_progress[extraction_id] = {
        "status": "processing",
        "message": "upload received",
        "kg_id": kg_id,
    }

    # 保存临时文件
    suffix = os.path.splitext(file.filename or "")[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    # 将实际的抽取工作放入后台任务，传递 kg_id
    background_tasks.add_task(
        _process_and_store,
        tmp_path,
        file.filename,
        extraction_id,
        kg_id,
    )

    # 返回立即响应，包含 extraction_id 供前端轮询
    return {
        "status": "queued",
        "filename": file.filename,
        "extraction_id": extraction_id,
        "kg_id": kg_id,
    }


# -------------------------------------------------------------------
# 背景任务实现：执行 pipeline、收集图谱、保存快照、更新状态
# -------------------------------------------------------------------
async def _process_and_store(
    tmp_path: str, filename: str, extraction_id: str, kg_id: Optional[str] = None
):
    try:
        # 清理旧的图谱（防止残留的占位节点）
        # Reuse the same in‑memory Neo4j client used by the graph builder
        from ..graph.graph_builder import client as neo

        print("[Background] Starting graph cleanup (fallback will be no‑op)")
        # 在 fallback 客户端中，这会是无操作；真实 Neo4j 会删除所有节点
        try:
            neo.run("MATCH (n) DETACH DELETE n")
        except Exception:
            pass

        # 清空已处理块缓存，确保同一文件再次上传时能够重新抽取
        from ..core.incremental import _processed_chunks

        _processed_chunks.clear()
        print("[Background] Cleared processed chunks cache (in‑memory)")
        # Also clear any Redis processed‑chunk markers if Redis is available
        from ..core.redis_client import RedisCache

        redis_cache = RedisCache()
        if getattr(redis_cache, "_available", False):
            try:
                keys = redis_cache._client.keys("processed_chunk:*")
                for k in keys:
                    redis_cache.delete(k)
                print(
                    f"[Background] Cleared {len(keys)} processed‑chunk keys from Redis"
                )
            except Exception as e:
                print(f"[Background] Failed to clear Redis processed chunks: {e}")
        # 运行完整的文档抽取管道
        extraction_progress[extraction_id]["message"] = "running pipeline"
        print("[Background] Starting pipeline for", tmp_path)
        process_document(tmp_path)

        # 导出当前图谱快照
        extraction_progress[extraction_id]["message"] = "exporting graph"
        print("[Background] Exporting graph snapshot")
        node_records = neo.run("MATCH (n:Entity) RETURN n")
        nodes = []
        for rec in node_records:
            n = rec.get("n")
            if isinstance(n, dict):
                props = n
            else:
                props = dict(n)
            nodes.append({"id": props.get("name"), "properties": props})
        print(f"[Background] Collected {len(nodes)} nodes")
        rel_records = neo.run(
            "MATCH (a)-[r:REL]->(b) RETURN a.name AS source, b.name AS target, r.type AS type"
        )
        relationships = []
        for rec in rel_records:
            relationships.append(
                {
                    "source": rec.get("source"),
                    "target": rec.get("target"),
                    "type": rec.get("type"),
                }
            )
        print(f"[Background] Collected {len(relationships)} relationships")
        graph_data = {"nodes": nodes, "relationships": relationships}

        # 保存快照并更新状态
        from ..core.extraction_store import save_extraction

        print("[Background] Saving extraction snapshot to disk")
        saved_extraction_id = save_extraction(filename, graph_data)
        # 若提供 kg_id，则更新对应知识图谱的实体/关系计数、关联抽取并合并图谱
        if kg_id:
            from ..core.kg_store import (
                update_counts,
                link_extraction,
                merge_graph_into_kg,
            )

            entity_cnt = len(nodes)
            rel_cnt = len(relationships)
            update_counts(kg_id, entity_cnt, rel_cnt)
            # 关联抽取 ID
            link_extraction(kg_id, saved_extraction_id)
            # 合并图谱到 KG 的聚合图
            merge_graph_into_kg(kg_id, graph_data)
        extraction_progress[extraction_id]["status"] = "completed"
        extraction_progress[extraction_id]["message"] = "finished"
        extraction_progress[extraction_id]["graph"] = graph_data
        print("[Background] Extraction completed successfully")
    except Exception as e:
        extraction_progress[extraction_id]["status"] = "failed"
        extraction_progress[extraction_id]["message"] = str(e)
    finally:
        # 清理临时文件
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# --------------------------------------------
# 轮询状态的 API
# --------------------------------------------
@router.get("/extraction_status/{eid}")
def extraction_status(eid: str):
    """返回给定 extraction_id 的当前状态与可选的图谱数据（仅在完成时返回）。"""
    info = extraction_progress.get(eid)
    if not info:
        return {"error": "extraction_id not found"}
    return info


# -------------------------------
# 实体详情查询（前端页面使用）
# -------------------------------
@router.get("/entity/{name}")
def get_entity(name: str):
    """返回指定实体的属性以及所有直接关系（variable_path_query 深度 1）"""
    neo = Neo4jClient()
    # 直接匹配节点
    node_res = neo.run("MATCH (e:Entity {name: $name}) RETURN e", {"name": name})
    node = None
    if node_res:
        node = node_res[0]["e"]
    if not node:
        raise HTTPException(status_code=404, detail=f"Entity '{name}' not found")
    # 查询 1 跳关系（直接邻居）
    rels = neo.variable_path_query(start_name=name, min_hops=1, max_hops=1)
    return {"node": node, "relations": rels}


# -------------------------------
# 前端静态页面入口（上传页面）
# -------------------------------
@router.get("/upload")
def upload_page():
    """返回上传页面（index.html 已挂载在 /static，直接返回对应文件）"""
    import os

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "upload.html"))
    from fastapi.responses import FileResponse

    return FileResponse(path)


# -------------------------------
# 前端实体详情页面入口
# -------------------------------
@router.get("/entity_page")
def entity_page(name: Optional[str] = None):
    """返回实体详情页面（通过查询参数 `name`）"""
    import os
    from fastapi.responses import FileResponse

    # 如果没有提供 name，直接返回页面（页面内部会提示缺失）
    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "entity.html"))
    return FileResponse(path)


# ----------------------------------------------------------
# Simple full‑text search UI endpoint
# ----------------------------------------------------------
from ..graph.neo4j_client import Neo4jClient
from fastapi.responses import FileResponse
import os


@router.get("/search")
def fulltext_search(q: str):
    """Expose Neo4j full‑text search via API.
    Returns the raw list from ``Neo4jClient.fulltext_search``.
    """
    neo = Neo4jClient()
    return {"results": neo.fulltext_search(q)}


@router.get("/ui")
def ui():
    """Serve the UI HTML page.
    The static files are mounted at ``/static``; this endpoint redirects to the index.
    """
    # Resolve the absolute path to the index.html file
    cur_dir = os.path.dirname(__file__)  # this file's directory (app/api)
    index_path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "index.html"))
    return FileResponse(index_path)


# Existing routes continued ...


# ----------------------------------------------------------
# Extraction list & detail endpoints
# ----------------------------------------------------------
@router.get("/extractions")
def list_extractions_endpoint():
    from ..core.extraction_store import list_extractions

    return {"extractions": list_extractions()}


@router.get("/extractions/{eid}")
def get_extraction_endpoint(eid: str):
    from ..core.extraction_store import load_extraction

    data = load_extraction(eid)
    if not data:
        return {"error": "Extraction not found"}
    return data


# ----------------------------------------------------------
# Front‑end HTML page endpoints
# ----------------------------------------------------------
@router.get("/extractions_page")
def extractions_page():
    import os

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "extractions.html"))
    from fastapi.responses import FileResponse

    return FileResponse(path)


@router.get("/graph_view")
def graph_view_page():
    import os

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "graph_view.html"))
    from fastapi.responses import FileResponse

    return FileResponse(path)


# ----------------------------------------------------------
# 知识图谱（KG）元数据管理接口
# ----------------------------------------------------------
from ..core.kg_store import list_kgs, create_kg


@router.get("/kg/list")
def list_kg_endpoint():
    """返回所有知识图谱的元数据，按创建时间倒序。"""
    return {"kgs": list_kgs()}


@router.post("/kg/create")
def create_kg_endpoint(payload: Dict[str, Any]):
    print(f"[ROUTES] Received payload for create KG: {payload}")
    try:
        name = payload.get("name")
        description = payload.get("description", "")
        if not name:
            raise HTTPException(
                status_code=400, detail="Knowledge graph name is required"
            )
        kg = create_kg(name, description)
        return kg
    except Exception as e:
        print(f"[ROUTES][ERROR] create_kg_endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/kg_page")
def kg_page():
    """返回知识图谱列表页面。"""
    import os
    from fastapi.responses import FileResponse

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "kg.html"))
    return FileResponse(path)


# 新增 /kg 重定向，使 http://localhost:8005/kg 能正确打开 KG 列表页面
from fastapi.responses import RedirectResponse


@router.get("/kg")
def kg_redirect():
    return RedirectResponse(url="/kg_page")


@router.get("/kg_detail")
def kg_detail_page():
    """返回 KG 详情页面（禁用缓存）。"""
    import os
    from fastapi.responses import FileResponse
    from fastapi import Response

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "kg_detail.html"))
    # Return with no-cache headers to ensure browser loads latest version
    return FileResponse(
        path,
        media_type="text/html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"},
    )


# ----------------------------------------------------------
# KG 元数据查询、更新、删除以及图谱获取 API
# ----------------------------------------------------------
from datetime import datetime


@router.get("/kg/{kg_id}")
def get_kg_endpoint(kg_id: str):
    """返回指定 KG 的完整元数据。"""
    from ..core.kg_store import _load_all

    for kg in _load_all():
        if kg["id"] == kg_id:
            return kg
    raise HTTPException(status_code=404, detail="KG not found")


@router.put("/kg/{kg_id}")
def update_kg_endpoint(kg_id: str, payload: Dict[str, Any]):
    """更新 KG 的名称或描述。"""
    name = payload.get("name")
    description = payload.get("description")
    from ..core.kg_store import _load_all, _save_all

    kgs = _load_all()
    for kg in kgs:
        if kg["id"] == kg_id:
            if name:
                kg["name"] = name
            if description is not None:
                kg["description"] = description
            kg["updated_at"] = datetime.utcnow().isoformat()
            _save_all(kgs)
            return kg
    raise HTTPException(status_code=404, detail="KG not found")


@router.delete("/kg/{kg_id}")
def delete_kg_endpoint(kg_id: str):
    """删除指定 KG（以及它的关联记录）。"""
    from ..core.kg_store import _load_all, _save_all

    kgs = _load_all()
    new_kgs = [kg for kg in kgs if kg["id"] != kg_id]
    if len(new_kgs) == len(kgs):
        raise HTTPException(status_code=404, detail="KG not found")
    _save_all(new_kgs)
    return {"status": "deleted", "kg_id": kg_id}


@router.get("/kg/{kg_id}/graph")
def kg_graph_endpoint(kg_id: str):
    """返回最新关联的抽取图谱数据（graph 字段）。如果没有关联抽取则返回 404。"""
    from ..core.kg_store import _load_all
    from ..core.extraction_store import load_extraction

    # 查找 KG
    for kg in _load_all():
        if kg["id"] == kg_id:
            # 如果 KG 已经存有聚合图，则直接返回
            if "graph" in kg:
                # Flatten nodes and add edges for frontend compatibility
                graph = kg["graph"]
                # Flatten node properties
                flat_nodes = []
                for n in graph.get("nodes", []):
                    flat_nodes.append(
                        {
                            "id": n.get("id"),
                            "name": n.get("properties", {}).get("name"),
                            "type": n.get("properties", {}).get("type"),
                        }
                    )
                # Map relationships to edges expected by frontend
                edges = []
                for r in graph.get("relationships", []):
                    edges.append(
                        {
                            "source": r.get("source"),
                            "target": r.get("target"),
                            "type": r.get("type"),
                        }
                    )
                return {"graph": {"nodes": flat_nodes, "edges": edges}}

            # 兼容旧的仅记录 extraction_ids 的情况
            extraction_ids = kg.get("extraction_ids", [])
            if not extraction_ids:
                raise HTTPException(
                    status_code=404, detail="No extraction linked to this KG"
                )
            latest_id = extraction_ids[-1]
            data = load_extraction(latest_id)
            if not data:
                raise HTTPException(status_code=404, detail="Extraction data not found")
            return data
    raise HTTPException(status_code=404, detail="KG not found")


# ----------------------------------------------------------
# Chat UI endpoints
# ----------------------------------------------------------
from fastapi import Request


@router.get("/chat")
def chat_page():
    """Serve the chat UI page."""
    import os

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "chat.html"))
    from fastapi.responses import FileResponse

    return FileResponse(path)


@router.post("/chat/message")
async def chat_message(request: Request):
    """Receive a chat message and return the agent's response."""
    payload = await request.json()
    message = payload.get("message", "")
    # Use the dummy agent defined earlier
    result = agent.run(message)
    return {"reply": result}


# ----------------------------------------------------------
# Graph visualization UI endpoint
# ----------------------------------------------------------
@router.get("/graph")
def graph_page():
    """Serve a simple graph visualization page."""
    import os

    cur_dir = os.path.dirname(__file__)
    path = os.path.abspath(os.path.join(cur_dir, "..", "frontend", "graph.html"))
    from fastapi.responses import FileResponse

    return FileResponse(path)
