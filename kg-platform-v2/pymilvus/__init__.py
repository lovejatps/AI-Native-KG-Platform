"""Lightweight stub of pymilvus for test environment.
Provides minimal classes and functions used in test_milvus.py.
All operations are no‑ops.
"""

from enum import Enum

class DataType(Enum):
    INT64 = 1
    FLOAT_VECTOR = 2

class FieldSchema:
    def __init__(self, name: str, dtype: DataType, is_primary: bool = False, auto_id: bool = False, dim: int = None):
        self.name = name
        self.dtype = dtype
        self.is_primary = is_primary
        self.auto_id = auto_id
        self.dim = dim

class CollectionSchema:
    def __init__(self, fields, description: str = ""):
        self.fields = fields
        self.description = description

class connections:
    @staticmethod
    def connect(host: str, port: int):
        # No real connection – just a placeholder.
        print(f"[pymilvus stub] Connected to {host}:{port}")

class Collection:
    def __init__(self, name: str, schema: CollectionSchema):
        self.name = name
        self.schema = schema
        print(f"[pymilvus stub] Created collection {name}")
    def load(self):
        print(f"[pymilvus stub] Loaded collection {self.name}")
    def drop(self):
        print(f"[pymilvus stub] Dropped collection {self.name}")
