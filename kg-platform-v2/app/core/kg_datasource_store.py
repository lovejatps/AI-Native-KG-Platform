"""Simple storage for KG ↔ DataSource integration.
Each entry stores:
- id (uuid)
- kg_id (str)
- ds_id (str)   # data source id
- tables (list[str])  # selected tables from that data source
"""

import json, os, uuid
from typing import List, Dict, Any

_DATA_FILE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "kg_datasource_links.json")
)

if os.path.exists(_DATA_FILE):
    with open(_DATA_FILE, "r", encoding="utf-8") as f:
        _LINKS: List[Dict[str, Any]] = json.load(f)
else:
    _LINKS = []


def _persist():
    with open(_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(_LINKS, f, ensure_ascii=False, indent=2)


def list_links(kg_id: str) -> List[Dict[str, Any]]:
    return [ln for ln in _LINKS if ln["kg_id"] == kg_id]


def add_link(kg_id: str, ds_id: str, tables: List[str]) -> Dict[str, Any]:
    link = {
        "id": uuid.uuid4().hex,
        "kg_id": kg_id,
        "ds_id": ds_id,
        "tables": tables,
    }
    _LINKS.append(link)
    _persist()
    return link


def delete_link(link_id: str) -> bool:
    global _LINKS
    orig = len(_LINKS)
    _LINKS = [ln for ln in _LINKS if ln["id"] != link_id]
    if len(_LINKS) != orig:
        _persist()
        return True
    return False
