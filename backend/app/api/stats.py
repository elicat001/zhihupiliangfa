"""
统计相关 API 路由
提供仪表盘数据
"""

import logging
from datetime import datetime

from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.article import Article
from app.models.account import Account
from app.models.task import PublishTask
from app.schemas.stats import (
    DashboardStats,
    RecentRecordResponse,
    OptimalTimeResponse,
    HourDistributionResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/stats", tags=["统计数据"])


@router.get("/dashboard", response_model=DashboardStats, summary="仪表盘统计")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db),
):
    """
    获取仪表盘统计数据
    包含文章数、账号数、任务数、今日统计等
    """
    today_start = datetime.utcnow().replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    # ========== 文章统计 ==========
    # 总文章数
    result = await db.execute(select(func.count(Article.id)))
    total_articles = result.scalar() or 0

    # 草稿数
    result = await db.execute(
        select(func.count(Article.id)).where(Article.status == "draft")
    )
    draft_articles = result.scalar() or 0

    # 已发布数
    result = await db.execute(
        select(func.count(Article.id)).where(Article.status == "published")
    )
    published_articles = result.scalar() or 0

    # ========== 账号统计 ==========
    # 总账号数
    result = await db.execute(select(func.count(Account.id)))
    total_accounts = result.scalar() or 0

    # 活跃账号数
    result = await db.execute(
        select(func.count(Account.id)).where(Account.is_active == True)  # noqa: E712
    )
    active_accounts = result.scalar() or 0

    # 已登录账号数
    result = await db.execute(
        select(func.count(Account.id)).where(
            Account.login_status == "logged_in"
        )
    )
    logged_in_accounts = result.scalar() or 0

    # ========== 任务统计 ==========
    # 总任务数
    result = await db.execute(select(func.count(PublishTask.id)))
    total_tasks = result.scalar() or 0

    # 各状态任务数
    result = await db.execute(
        select(func.count(PublishTask.id)).where(
            PublishTask.status == "pending"
        )
    )
    pending_tasks = result.scalar() or 0

    result = await db.execute(
        select(func.count(PublishTask.id)).where(
            PublishTask.status == "running"
        )
    )
    running_tasks = result.scalar() or 0

    result = await db.execute(
        select(func.count(PublishTask.id)).where(
            PublishTask.status == "success"
        )
    )
    success_tasks = result.scalar() or 0

    result = await db.execute(
        select(func.count(PublishTask.id)).where(
            PublishTask.status == "failed"
        )
    )
    failed_tasks = result.scalar() or 0

    # ========== 今日统计 ==========
    # 今日发布成功数
    result = await db.execute(
        select(func.count(PublishTask.id)).where(
            PublishTask.status == "success",
            PublishTask.created_at >= today_start,
        )
    )
    today_published = result.scalar() or 0

    # 今日生成文章数
    result = await db.execute(
        select(func.count(Article.id)).where(
            Article.created_at >= today_start,
        )
    )
    today_generated = result.scalar() or 0

    return DashboardStats(
        total_articles=total_articles,
        draft_articles=draft_articles,
        published_articles=published_articles,
        total_accounts=total_accounts,
        active_accounts=active_accounts,
        logged_in_accounts=logged_in_accounts,
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        running_tasks=running_tasks,
        success_tasks=success_tasks,
        failed_tasks=failed_tasks,
        today_published=today_published,
        today_generated=today_generated,
    )


@router.get("/recent-records", response_model=list[RecentRecordResponse], summary="最近发布记录")
async def get_recent_records(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """获取最近的发布任务记录"""
    result = await db.execute(
        select(PublishTask)
        .order_by(PublishTask.created_at.desc())
        .limit(limit)
    )
    tasks = result.scalars().all()

    records = []
    for task in tasks:
        records.append(RecentRecordResponse(
            id=task.id,
            article_title=task.article.title if task.article else "",
            account_nickname=task.account.nickname if task.account else "",
            status=task.status,
            created_at=task.created_at,
        ))
    return records


@router.get(
    "/optimal-times",
    response_model=list[OptimalTimeResponse],
    summary="获取最佳发布时间建议",
)
async def get_optimal_times(
    account_id: Optional[int] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """
    分析历史数据并结合知乎活跃时段，推荐最佳发布时间。

    - **account_id**: 可选，按账号筛选
    - **days**: 分析的天数范围，默认 30 天
    - 返回 Top 5 推荐时段及评分理由
    """
    from app.core.analytics import get_optimal_publish_times

    times = await get_optimal_publish_times(db, account_id=account_id, days=days)
    return times


@router.get(
    "/hour-distribution",
    response_model=list[HourDistributionResponse],
    summary="获取发布时段分布",
)
async def get_hour_distribution(
    account_id: Optional[int] = None,
    days: int = 30,
    db: AsyncSession = Depends(get_db),
):
    """
    获取 24 小时发布时段分布数据（用于前端可视化图表）。

    - **account_id**: 可选，按账号筛选
    - **days**: 分析的天数范围，默认 30 天
    - 返回每小时的总数、成功数、失败数
    """
    from app.core.analytics import get_publish_hour_distribution

    distribution = await get_publish_hour_distribution(db, account_id=account_id, days=days)
    return distribution
