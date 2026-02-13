"""
发布相关 API 路由
包含立即发布、定时发布、批量发布
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.article import Article
from app.models.account import Account
from app.schemas.task import (
    PublishNowRequest,
    PublishScheduleRequest,
    PublishBatchRequest,
    TaskResponse,
)
from app.core.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/publish", tags=["发布操作"])


def _validate_account(account: Account) -> None:
    """
    校验账号是否可用于发布

    Raises:
        HTTPException: 如果账号不可用
    """
    if not account.is_active:
        raise HTTPException(status_code=400, detail="账号已禁用")
    if account.login_status not in ("logged_in",):
        raise HTTPException(
            status_code=400,
            detail=f"账号未登录（当前状态: {account.login_status}），请先登录后再发布",
        )


@router.post("/now", response_model=TaskResponse, summary="立即发布")
async def publish_now(
    request: PublishNowRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    立即发布文章到知乎

    - **article_id**: 要发布的文章 ID
    - **account_id**: 使用的账号 ID
    """
    # 验证文章存在
    article = await db.get(Article, request.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 验证账号存在且可用
    account = await db.get(Account, request.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    _validate_account(account)

    try:
        task = await task_scheduler.add_immediate_task(
            article_id=request.article_id,
            account_id=request.account_id,
        )

        logger.info(
            f"创建立即发布任务: task_id={task.id}, "
            f"article={article.title}, account={account.nickname}"
        )

        return TaskResponse(
            id=task.id,
            article_id=task.article_id,
            account_id=task.account_id,
            status=task.status,
            scheduled_at=task.scheduled_at,
            retry_count=task.retry_count,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=getattr(task, "updated_at", None),
            article_title=article.title,
            account_nickname=account.nickname,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"创建发布任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/schedule", response_model=TaskResponse, summary="定时发布")
async def publish_schedule(
    request: PublishScheduleRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    定时发布文章到知乎

    - **article_id**: 要发布的文章 ID
    - **account_id**: 使用的账号 ID
    - **scheduled_at**: 计划执行时间（ISO 8601 格式）
    """
    # 验证文章存在
    article = await db.get(Article, request.article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 验证账号存在且可用
    account = await db.get(Account, request.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    _validate_account(account)

    try:
        task = await task_scheduler.add_scheduled_task(
            article_id=request.article_id,
            account_id=request.account_id,
            scheduled_at=request.scheduled_at,
        )

        logger.info(
            f"创建定时发布任务: task_id={task.id}, "
            f"scheduled_at={request.scheduled_at}"
        )

        return TaskResponse(
            id=task.id,
            article_id=task.article_id,
            account_id=task.account_id,
            status=task.status,
            scheduled_at=task.scheduled_at,
            retry_count=task.retry_count,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=getattr(task, "updated_at", None),
            article_title=article.title,
            account_nickname=account.nickname,
        )

    except Exception as e:
        logger.error(f"创建定时任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")


@router.post("/batch", response_model=list[TaskResponse], summary="批量发布")
async def publish_batch(
    request: PublishBatchRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    批量发布多篇文章到知乎
    文章按照指定间隔依次排入发布队列

    - **article_ids**: 文章 ID 列表
    - **account_id**: 使用的账号 ID
    - **interval_minutes**: 每篇发布间隔（分钟，默认10）
    """
    # 验证账号
    account = await db.get(Account, request.account_id)
    if not account:
        raise HTTPException(status_code=404, detail="账号不存在")
    _validate_account(account)

    # 验证所有文章
    for article_id in request.article_ids:
        article = await db.get(Article, article_id)
        if not article:
            raise HTTPException(
                status_code=404, detail=f"文章 ID {article_id} 不存在"
            )

    try:
        tasks = await task_scheduler.add_batch_tasks(
            article_ids=request.article_ids,
            account_id=request.account_id,
            interval_minutes=request.interval_minutes,
        )

        logger.info(
            f"创建批量发布任务: {len(tasks)} 个, "
            f"间隔 {request.interval_minutes} 分钟"
        )

        # 构建响应
        result = []
        for task in tasks:
            # 获取文章标题
            article = await db.get(Article, task.article_id)
            result.append(
                TaskResponse(
                    id=task.id,
                    article_id=task.article_id,
                    account_id=task.account_id,
                    status=task.status,
                    scheduled_at=task.scheduled_at,
                    retry_count=task.retry_count,
                    error_message=task.error_message,
                    created_at=task.created_at,
                    updated_at=getattr(task, "updated_at", None),
                    article_title=article.title if article else None,
                    account_nickname=account.nickname,
                )
            )

        return result

    except Exception as e:
        logger.error(f"创建批量任务失败: {e}")
        raise HTTPException(status_code=500, detail=f"创建任务失败: {str(e)}")
