"""Pydantic schemas for API endpoints.

Existing schemas for auth are defined in `app/auth/schemas.py`. This file
contains shared request/response models for other endpoints.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Literal, List


class DataSourceCreate(BaseModel):
    system_name: str = Field(..., description="系统名称/业务标识")
    db_type: Literal["mysql", "sqlite"] = Field(..., description="库类型")
    host: str = Field(..., description="主机名/IP或sqlite文件路径")
    port: Optional[int] = Field(None, description="端口（sqlite 可为空）")
    username: Optional[str] = Field(None, description="用户名（sqlite 可为空）")
    password: Optional[str] = Field(None, description="密码（sqlite 可为空）")
    database: Optional[str] = Field(None, description="数据库名（sqlite 可为空）")


class DataSourceUpdate(BaseModel):
    # 允许更新状态字段（仅后端使用）
    status: Optional[Literal["正常", "失败", "未知"]] = None
    system_name: Optional[str] = None
    db_type: Optional[Literal["mysql", "sqlite"]] = None
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None
    database: Optional[str] = None

# ---------------------------------------------------------------------------
# Semantic Dictionary schemas (字段语义字典 & 值映射字典)
# ---------------------------------------------------------------------------

class FieldDictBase(BaseModel):
    library_name: Optional[str] = None
    table_name: str = Field(..., description="所属表名")
    column_name: str = Field(..., description="字段名")
    synonyms: List[str] = Field(default_factory=list, description="同义词 JSON 数组")
    description: Optional[str] = None

    @validator("synonyms", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                raise ValueError("synonyms 必须是 JSON 数组")
        return v

class FieldDictCreate(FieldDictBase):
    pass

class FieldDictUpdate(FieldDictBase):
    pass

class FieldDictOut(FieldDictBase):
    id: int

class PagedFieldDictResponse(BaseModel):
    total: int
    items: List[FieldDictOut]

class ValueDictBase(BaseModel):
    library_name: Optional[str] = None
    table_name: str = Field(..., description="所属表名")
    column_name: str = Field(..., description="关联字段名")
    display_value: str = Field(..., description="前端显示值")
    actual_value: str = Field(..., description="数据库实际值")
    synonyms: List[str] = Field(default_factory=list, description="值同义词 JSON 数组")

    @validator("synonyms", pre=True)
    def ensure_list(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except Exception:
                raise ValueError("synonyms 必须是 JSON 数组")
        return v

class ValueDictCreate(ValueDictBase):
    pass

class ValueDictUpdate(ValueDictBase):
    pass

class ValueDictOut(ValueDictBase):
    id: int

class PagedValueDictResponse(BaseModel):
    total: int
    items: List[ValueDictOut]
