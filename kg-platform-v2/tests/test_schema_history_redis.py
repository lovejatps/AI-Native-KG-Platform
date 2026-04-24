import json
import hashlib
from unittest.mock import patch

from app.schema.schema_builder import build_schema
from app.core.redis_client import RedisCache

class FakeRedis:
    """Very small in‑memory stand‑in for the subset of Redis we use.
    Supports ``set``, ``sadd`` and ``smembers``.
    """
    def __init__(self):
        self.store = {}
        self.sets = {}
    # ``set`` stores JSON‑serialisable objects (we keep them as Python objects for simplicity)
    def set(self, key, value, ex=None):  # pylint: disable=unused-argument
        # Deep‑copy via json to emulate serialization behaviour
        self.store[key] = json.loads(json.dumps(value))
        return True
    def sadd(self, key, member):
        self.sets.setdefault(key, set()).add(member)
        return True
    def smembers(self, key):
        return list(self.sets.get(key, set()))

def _fake_redis_init(self):
    # Bypass real Redis connection; inject our fake client and mark as available
    self._client = fake_redis_instance
    self._available = True

# Share a single FakeRedis instance across all test calls
fake_redis_instance = FakeRedis()

def test_schema_history_versions_per_hash_and_kg():
    # Patch RedisCache.__init__ to use the fake client
    with patch.object(RedisCache, "__init__", _fake_redis_init):
        # First schema generation for text "hello world" under KG "kgA"
        schema1 = build_schema("hello world", kg_id="kgA")
        v1 = schema1["_version"]
        # Second schema generation for a different text under the same KG
        schema2 = build_schema("goodbye", kg_id="kgA")
        v2 = schema2["_version"]
        # Verify per‑hash version sets contain their respective versions
        hash1 = hashlib.sha256("hello world".encode("utf-8")).hexdigest()
        hash2 = hashlib.sha256("goodbye".encode("utf-8")).hexdigest()
        versions_hash1 = fake_redis_instance.smembers(f"{hash1}:versions")
        versions_hash2 = fake_redis_instance.smembers(f"{hash2}:versions")
        assert v1 in versions_hash1
        assert v2 in versions_hash2
        # Verify KG‑level version set contains both versions
        kg_versions = fake_redis_instance.smembers("schema_versions:kgA")
        assert v1 in kg_versions and v2 in kg_versions
        # Verify versioned keys are stored permanently (no TTL handling needed in FakeRedis)
        assert f"{hash1}:{v1}" in fake_redis_instance.store
        assert f"{hash2}:{v2}" in fake_redis_instance.store
