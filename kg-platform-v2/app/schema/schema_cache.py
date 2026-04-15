import os
import json
import time
from pathlib import Path

SCHEMA_DIR = Path(__file__).parent / "versions"
SCHEMA_DIR.mkdir(parents=True, exist_ok=True)


def _schema_path(version: str) -> Path:
    return SCHEMA_DIR / f"schema_{version}.json"


def save_schema(schema: dict, version: str | None = None) -> str:
    """Persist a schema JSON.
    If *version* is None, use a timestamp string.
    Returns the version used.
    """
    if version is None:
        version = time.strftime("%Y%m%d%H%M%S")
    path = _schema_path(version)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema, f, ensure_ascii=False, indent=2)
    return version


def load_schema(version: str) -> dict | None:
    """Load a specific schema version; returns None if not found."""
    path = _schema_path(version)
    if not path.is_file():
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
        # Inject version metadata for callers expecting it
        data["_version"] = version
        return data


def list_versions() -> list[str]:
    """Return sorted list of version strings (newest first)."""
    files = SCHEMA_DIR.glob("schema_*.json")
    versions = [p.stem.split("_")[1] for p in files]
    return sorted(versions, reverse=True)


def get_latest_schema() -> dict | None:
    versions = list_versions()
    if not versions:
        return None
    return load_schema(versions[0])
