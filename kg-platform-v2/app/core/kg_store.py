import json
import os
import uuid
from datetime import datetime
from typing import List, Dict

# Simple JSON file to persist KG metadata (fallback for demo)
_STORE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "data", "kg_store.json")
)


def _ensure_store() -> None:
    """Ensure the storage file exists."""
    os.makedirs(os.path.dirname(_STORE_PATH), exist_ok=True)
    if not os.path.isfile(_STORE_PATH):
        with open(_STORE_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def _load_all() -> List[Dict]:
    _ensure_store()
    with open(_STORE_PATH, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            data = []
    return data


def _save_all(kgs: List[Dict]) -> None:
    with open(_STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(kgs, f, ensure_ascii=False, indent=2)


def list_kgs() -> List[Dict]:
    """Return the list of knowledge graphs, sorted by creation time descending."""
    kgs = _load_all()
    kgs.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return kgs


def create_kg(name: str, description: str) -> Dict:
    """Create a new KG entry and persist it. Returns the created dict."""
    new_kg = {
        "id": str(uuid.uuid4()),
        "name": name,
        "description": description,
        "entity_count": 0,
        "relation_count": 0,
        "created_at": datetime.utcnow().isoformat(),
    }
    kgs = _load_all()
    kgs.append(new_kg)
    _save_all(kgs)
    print(f"[KG_STORE] KG after merge: {new_kg}")
    return new_kg


def update_counts(kg_id: str, entity_count: int, relation_count: int) -> None:
    """Update entity/relation counts for a given KG (used after extraction)."""
    kgs = _load_all()
    for kg in kgs:
        if kg["id"] == kg_id:
            kg["entity_count"] = entity_count
            kg["relation_count"] = relation_count
            kg["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_all(kgs)
    print(f"[KG_STORE] KG after operation for kg_id: {kg_id}")


# ---------- 新增合并图谱功能 ----------
def _merge_graph(kg: dict, new_graph: dict) -> None:
    """把 new_graph 合并到 kg 中的聚合图（去重）。
    kg 里约定有键 `graph`，结构: {"nodes": [...], "relationships": [...]}
    """
    agg = kg.get("graph")
    if not agg:
        agg = {"nodes": [], "relationships": []}
        kg["graph"] = agg
    # 合并 nodes（按 name 去重并更新属性）
    # 建立 name -> node 映射以便更新已有节点的属性（如类型）
    node_map = {
        (n.get("properties", {}).get("name") or n.get("id")): n
        for n in agg.get("nodes", [])
    }
    for n in new_graph.get("nodes", []):
        name = n.get("properties", {}).get("name") or n.get("id")
        if name in node_map:
            # 更新已有节点的属性，确保类型等信息保持最新
            existing_node = node_map[name]
            # 合并属性，优先使用新属性覆盖旧属性
            existing_props = existing_node.get("properties", {}) or {}
            new_props = n.get("properties", {}) or {}
            existing_props.update(new_props)
            existing_node["properties"] = existing_props
        else:
            # 新节点，直接加入并记录到映射
            agg.setdefault("nodes", []).append(n)
            node_map[name] = n
    # 合并 relationships（source,target,type 去重）
    existing_rels = {
        (r.get("source"), r.get("target"), r.get("type"))
        for r in agg.get("relationships", [])
    }
    # Ensure nodes for each relationship exist
    existing_node_names = {
        (n.get("properties", {}).get("name") or n.get("id"))
        for n in agg.get("nodes", [])
    }
    for r in new_graph.get("relationships", []):
        # Add missing source node
        if r.get("source") and r.get("source") not in existing_node_names:
            agg.setdefault("nodes", []).append(
                {
                    "id": r.get("source"),
                    "properties": {"name": r.get("source"), "type": "实体"},
                }
            )
            existing_node_names.add(r.get("source"))
        # Add missing target node
        if r.get("target") and r.get("target") not in existing_node_names:
            agg.setdefault("nodes", []).append(
                {
                    "id": r.get("target"),
                    "properties": {"name": r.get("target"), "type": "实体"},
                }
            )
            existing_node_names.add(r.get("target"))
        # Add relationship if not duplicate
        key = (r.get("source"), r.get("target"), r.get("type"))
        if key not in existing_rels:
            agg.setdefault("relationships", []).append(r)
            existing_rels.add(key)


def merge_graph_into_kg(kg_id: str, new_graph: dict) -> None:
    print(
        f"[KG_STORE] merge_graph_into_kg called for kg_id={kg_id}, new_graph nodes={len(new_graph.get('nodes', []))}, rels={len(new_graph.get('relationships', []))}"
    )
    """公开接口：把 new_graph 合并到指定 KG 的聚合图中。"""
    kgs = _load_all()
    for kg in kgs:
        if kg["id"] == kg_id:
            _merge_graph(kg, new_graph)
            # 更新计数
            kg["entity_count"] = len(kg["graph"].get("nodes", []))
            kg["relation_count"] = len(kg["graph"].get("relationships", []))
            kg["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_all(kgs)
    print(f"[KG_STORE] KG after operation for kg_id: {kg_id}")


def link_extraction(kg_id: str, extraction_id: str) -> None:
    """Associate an extraction_id with a KG (store list of extraction ids)."""
    kgs = _load_all()
    for kg in kgs:
        if kg["id"] == kg_id:
            if "extraction_ids" not in kg:
                kg["extraction_ids"] = []
            if extraction_id not in kg["extraction_ids"]:
                kg["extraction_ids"].append(extraction_id)
            kg["updated_at"] = datetime.utcnow().isoformat()
            break
    _save_all(kgs)
    print(f"[KG_STORE] KG after operation for kg_id: {kg_id}")


def ensure_graph_node_consistency() -> None:
    """Iterate all stored KGs and add missing nodes for each relationship.
    This fixes legacy KG entries where relationships exist but nodes were not created.
    """
    kgs = _load_all()
    for kg in kgs:
        graph = kg.get("graph")
        if not graph:
            continue
        nodes = graph.get("nodes", [])
        existing_names = {n.get("name") for n in nodes}
        # Ensure source/target nodes exist
        for rel in graph.get("relationships", []):
            src = rel.get("source")
            tgt = rel.get("target")
            if src and src not in existing_names:
                nodes.append({"id": src, "properties": {"name": src, "type": "实体"}})
                existing_names.add(src)
            if tgt and tgt not in existing_names:
                nodes.append({"id": tgt, "properties": {"name": tgt, "type": "实体"}})
                existing_names.add(tgt)
        # Update counts after fixing
        kg["entity_count"] = len(nodes)
        kg["relation_count"] = len(graph.get("relationships", []))
        kg["updated_at"] = datetime.utcnow().isoformat()
    _save_all(kgs)
    print("[KG_STORE] Completed graph node consistency fix")
