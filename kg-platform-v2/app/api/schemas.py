"""Pydantic schemas for API endpoints.

Existing schemas for auth are defined in `app/auth/schemas.py`. This file
contains shared request/response models for other endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, Literal


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
