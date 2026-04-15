import os, json, uuid
from datetime import datetime

# Directory to store extraction snapshots (ensure exists)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "extractions"))
os.makedirs(BASE_DIR, exist_ok=True)


def _meta_path(extraction_id: str) -> str:
    return os.path.join(BASE_DIR, f"{extraction_id}.json")


def save_extraction(filename: str, graph: dict) -> str:
    """Save a snapshot of the extracted graph.
    Returns a UUID string identifying the extraction.
    """
    extraction_id = str(uuid.uuid4())
    data = {
        "id": extraction_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "filename": filename,
        "graph": graph,
    }
    with open(_meta_path(extraction_id), "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return extraction_id


def list_extractions():
    """Return a list of stored extractions sorted by timestamp descending."""
    entries = []
    for fname in os.listdir(BASE_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(BASE_DIR, fname), "r", encoding="utf-8") as f:
                data = json.load(f)
                entries.append(
                    {
                        "id": data.get("id"),
                        "timestamp": data.get("timestamp"),
                        "filename": data.get("filename"),
                    }
                )
        except Exception:
            continue
    entries.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return entries


def load_extraction(extraction_id: str):
    """Load a stored extraction by its UUID. Returns the full data dict or None."""
    path = _meta_path(extraction_id)
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
