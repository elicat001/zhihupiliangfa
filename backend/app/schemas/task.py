"""
任务相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class PublishNowRequest(BaseModel):
    """立即发布请求"""
    article_id: int = Field(..., description="文章 ID")
    account_id: int = Field(..., description="账号 ID")


class PublishScheduleRequest(BaseModel):
    """定时发布请求"""
    article_id: int = Field(..., description="文章 ID")
    account_id: int = Field(..., description="账号 ID")
    scheduled_at: datetime = Field(..., description="计划执行时间（ISO 8601格式）")


class PublishBatchRequest(BaseModel):
    """批量发布请求"""
    article_ids: list[int] = Field(..., min_length=1, description="文章 ID 列表")
    account_id: int = Field(..., description="账号 ID")
    interval_minutes: int = Field(
        default=10, ge=5, le=1440, description="每篇发布间隔（分钟）"
    )


# ==================== 响应模型 ====================

class TaskResponse(BaseModel):
    """任务响应"""
    id: int
    article_id: int
    account_id: int
    status: str
    scheduled_at: Optional[datetime] = None
    retry_count: int = 0
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    # 关联信息
    article_title: Optional[str] = None
    account_nickname: Optional[str] = None

    model_config = {"from_attributes": True}


class TaskListResponse(BaseModel):
    """任务列表响应"""
    total: int
    items: list[TaskResponse]


class PublishRecordResponse(BaseModel):
    """发布记录响应"""
    id: int
    task_id: int
    article_id: int
    account_id: int
    zhihu_article_url: Optional[str]
    publish_status: str
    screenshot_path: Optional[str]
    started_at: Optional[datetime]
    finished_at: Optional[datetime]

    model_config = {"from_attributes": True}
