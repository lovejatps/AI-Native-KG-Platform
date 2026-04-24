import json
import hashlib
from app.core.llm import LLM
from . import schema_cache
from ..core.redis_client import RedisCache
from ..core.logger import get_logger
from typing import Dict, Any, Optional
from pydantic import ValidationError
from .models import KGSchema

_logger = get_logger(__name__)

# NOTE:
# - Redis 只用于 **缓存最新** schema（键 `schema:{hash}`），此键不设 TTL，始终持久化。
# - 每次生成新版本后，会把该版本持久化到键 `schema:{hash}:{version}`（永久），并将版本号加入集合
#   `schema:{hash}:versions` 供历史查询。
# - 如果传入 ``kg_id``，还会把版本号记录到集合 `schema_versions:{kg_id}`，方便按 KG 查询所有历史版本。
# - 文件系统（`schema_cache.save_schema`）仍是唯一的可靠持久化介质。




def build_schema(text: str, kg_id: Optional[str] = None):
    # existing function unchanged (kept for external use)
    """Generate or retrieve a cached schema for *text*.

    1. Compute a SHA‑256 hash of the input text – this serves as a deterministic
       cache key.
    2. Attempt to fetch a cached schema from Redis (key ``schema:{hash}``).
    3. If Redis miss, generate schema via LLM.
    4. Persist versioned schema locally.
    5. Store in Redis for fast future look‑ups (latest version with TTL) and
       maintain historical versions (per‑hash and per‑KG collections) without TTL.
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
    # Validate schema against Pydantic model (will raise if malformed)
    try:
        validated = KGSchema.parse_obj(schema)
        schema = validated.dict()
    except ValidationError as ve:
        _logger.error(f"Schema validation failed: {ve}")
        raise
    if not schema:
        schema = {"entities": ["Unknown"], "relations": [], "properties": {}}

    # 4️⃣ Persist versioned schema locally
    version = None
    try:
        version = schema_cache.save_schema(schema)
        schema["_version"] = version
    except Exception as e:
        _logger.error(f"Failed to save schema locally: {e}")

    # 5️⃣ Store in Redis for fast future look‑ups
    # 如果已经成功生成 version，则持久化该版本并维护版本集合
    if "version" in locals():
        # 永久保存当前版本（不设 TTL）
        redis_cache.set(f"{cache_key}:{version}", schema)
        # 将 version 加入对应 hash 的集合，以供历史查询
        redis_cache.sadd(f"{cache_key}:versions", version)  # type: ignore
        # If a KG ID is supplied, also record this version under the KG‑specific set
        if kg_id:
            redis_cache.sadd(f"schema_versions:{kg_id}", version)  # type: ignore
        # 同时保持原来的 TTL 缓存（最新版本，便于快速读取）
        # Store the latest version under the plain key (no TTL) for quick access
        redis_cache.set(cache_key, schema)

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

