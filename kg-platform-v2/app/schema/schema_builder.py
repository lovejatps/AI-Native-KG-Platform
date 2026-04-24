import json
import hashlib
from app.core.llm import LLM
from . import schema_cache
from ..core.redis_client import RedisCache
from ..core.logger import get_logger
from typing import Dict, Any

_logger = get_logger(__name__)


def build_schema(text: str):
    # existing function unchanged (kept for external use)
    """Generate or retrieve a cached schema for *text*.

    1. Compute a SHA‑256 hash of the input text – this serves as a deterministic
       cache key.
    2. Attempt to fetch a cached schema from Redis (key ``schema:{hash}``).
    3. If Redis miss, generate a fresh schema via the LLM.
    4. Persist the schema locally (versioned) and store it back into Redis.
    5. Return the schema (including ``_version``).
    """
    # 1️⃣ Compute hash for deterministic cache key
    text_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    redis_cache = RedisCache()
    cache_key = f"schema:{text_hash}"

    # 2️⃣ Try Redis cache first
    cached = redis_cache.get(cache_key)
    if cached:
        _logger.info(f"Schema cache hit (Redis) for hash {text_hash[:8]}")
        # Always persist a version for the cached schema (may be missing).
        try:
            version = schema_cache.save_schema(cached)
            cached["_version"] = version
        except Exception as e:
            _logger.error(f"Failed to persist cached schema version: {e}")
        return cached

    # 3️⃣ No Redis entry – generate schema via LLM
    llm = LLM()
    prompt = f"""
    你是知识图谱建模专家。
    请根据以下数据自动生成Schema：
    实体类型、关系类型、属性结构
    数据：
    {text}
    JSON格式输出
    """
    res = llm.chat(prompt)
    schema = llm._parse_response(res)
    # Ensure each entity's properties have `metadata.semanticName` (default to the property name)
    for ent in schema.get('entities', []):
        for prop in ent.get('properties', []):
            # Ensure source_column exists; if missing, fall back to the property name
            if not prop.get('source_column'):
                prop['source_column'] = prop.get('name')
            # Add metadata if absent
            meta = prop.get('metadata') or {}
            if 'semanticName' not in meta:
                meta['semanticName'] = prop.get('name')
            prop['metadata'] = meta
    if not schema:
        schema = {"entities": ["Unknown"], "relations": [], "properties": {}}

    # 4️⃣ Persist versioned schema locally
    try:
        version = schema_cache.save_schema(schema)
        schema["_version"] = version
    except Exception as e:
        _logger.error(f"Failed to save schema locally: {e}")

    # 5️⃣ Store in Redis for fast future look‑ups
    try:
        redis_cache.set(cache_key, schema)
    except Exception as e:
        _logger.warning(f"Unable to store schema in Redis: {e}")

    return schema

def generate_schema_for_kg(kg_id: str) -> Dict[str, Any]:
    """Fallback schema generator for a KG.
    If there is a published model for the KG, return its schema.
    Otherwise return an empty placeholder schema.
    """
    from ..core.models_store import list_models
    # Try to get a published schema (status "正式") similar to get_published_schema
    models = list_models(kg_id)
    published = [m for m in models if m.get('status') == '正式']
    if published:
        # choose highest version
        def version_key(m):
            v = m.get('version', 'V0')
            return int(''.join(ch for ch in v if ch.isdigit()) or 0)
        latest = max(published, key=version_key)
        return latest.get('schema', {'entities': [], 'relations': []})
    # No published model – return empty schema placeholder
    return {'entities': [], 'relations': []}

