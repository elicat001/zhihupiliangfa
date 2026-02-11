"""
统计相关的 Pydantic 响应模型
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class DashboardStats(BaseModel):
    """仪表盘统计数据"""
    # 文章统计
    total_articles: int = 0
    draft_articles: int = 0
    published_articles: int = 0

    # 账号统计
    total_accounts: int = 0
    active_accounts: int = 0
    logged_in_accounts: int = 0

    # 任务统计
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    success_tasks: int = 0
    failed_tasks: int = 0

    # 今日统计
    today_published: int = 0
    today_generated: int = 0


class RecentRecordResponse(BaseModel):
    """最近发布记录"""
    id: int
    article_title: str = ""
    account_nickname: str = ""
    status: str = ""
    created_at: Optional[datetime] = None


class OptimalTimeResponse(BaseModel):
    """最佳发布时间建议"""
    hour: int
    score: float
    reason: str


class HourDistributionResponse(BaseModel):
    """发布时段分布"""
    hour: int
    total: int = 0
    success: int = 0
    failed: int = 0
