import sys

sys.path.append("D:/app_Projects/AI-Native-KG-Platform/kg-platform-v2")
from app.core.config import get_settings

settings = get_settings()
print("Milvus host/port:", settings.MILVUS_HOST, settings.MILVUS_PORT)
from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType

try:
    connections.connect(host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    print("Milvus connection succeeded")
    # Create a temporary collection to test insert
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=768),
    ]
    schema = CollectionSchema(fields, description="test")
    coll = Collection("test_collection", schema)
    coll.load()
    print("Created test collection")
    # Clean up
    coll.drop()
    print("Dropped test collection")
except Exception as e:
    print("Milvus connection failed:", e)
