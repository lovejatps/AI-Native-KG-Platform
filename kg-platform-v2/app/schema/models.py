from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional, Dict, Any

class Property(BaseModel):
    name: str
    type: str
    comment: Optional[str] = ''
    description: Optional[str] = ''
    source_column: str
    metadata: Dict[str, Any] = Field(default_factory=dict)

class Entity(BaseModel):
    name: str
    type: str = 'Node'
    properties: List[Property]
    metadata: Dict[str, Any] = Field(default_factory=dict)

class KGSchema(BaseModel):
    entities: List[Entity]
    relations: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
