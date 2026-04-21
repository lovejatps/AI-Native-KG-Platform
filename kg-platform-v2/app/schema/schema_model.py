import json
from datetime import datetime
from typing import List, Optional, Dict, Literal

from pydantic import BaseModel, Field

class PropertyModel(BaseModel):
    name: str
    type: str
    description: str
    comment: Optional[str] = ""
    nullable: Optional[bool] = False
    default: Optional[str] = None

class EntityModel(BaseModel):
    name: str
    type: Literal["Table", "View", "Node"] = "Table"
    description: Optional[str] = ""
    properties: List[PropertyModel] = Field(default_factory=list)
    metadata: Optional[Dict[str, str]] = None

class RelationModel(BaseModel):
    from_: str = Field(..., alias="from")
    to: str
    type: Literal["FK", "PK", "CUSTOM"] = "FK"
    description: Optional[str] = ""
    metadata: Optional[Dict[str, str]] = None

class SchemaModel(BaseModel):
    version: str = "V1"
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    author: Optional[str] = None
    entities: List[EntityModel] = Field(default_factory=list)
    relations: List[RelationModel] = Field(default_factory=list)
    # Backward‑compatibility: allow the old field name "relationships"
    relationships: Optional[List[RelationModel]] = None

    def model_dump_json(self) -> str:
        """Convenient JSON string (uses Pydantic's built‑in serialization)."""
        return self.model_dump(mode="json")
