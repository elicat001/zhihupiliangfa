"""
内容模板相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class TemplateCreateRequest(BaseModel):
    """创建模板请求"""
    name: str = Field(..., min_length=1, max_length=100, description="模板名称")
    description: str = Field(default="", description="模板描述")
    system_prompt: str = Field(..., min_length=1, description="系统提示词")
    user_prompt_template: str = Field(..., min_length=1, description="用户提示词模板")
    default_style: str = Field(default="professional", description="默认写作风格")
    default_word_count: int = Field(default=1500, ge=300, le=10000, description="默认目标字数")


class TemplateUpdateRequest(BaseModel):
    """更新模板请求"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    system_prompt: Optional[str] = Field(None, min_length=1)
    user_prompt_template: Optional[str] = Field(None, min_length=1)
    default_style: Optional[str] = None
    default_word_count: Optional[int] = Field(None, ge=300, le=10000)


# ==================== 响应模型 ====================

class TemplateResponse(BaseModel):
    """模板响应"""
    id: int
    name: str
    description: str
    system_prompt: str
    user_prompt_template: str
    default_style: str
    default_word_count: int
    is_builtin: bool
    created_at: datetime

    model_config = {"from_attributes": True}
