"""
任务相关 API 路由
查询发布任务列表和详情
"""

import csv
import io
import logging
import os
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.task import PublishTask, PublishRecord
from pydantic import BaseModel
from app.schemas.task import (
    TaskResponse,
    TaskListResponse,
    PublishRecordResponse,
)
from app.api.events import event_bus
from app.core.task_scheduler import task_scheduler

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/tasks", tags=["任务管理"])


def _task_to_response(task: PublishTask) -> TaskResponse:
    """将 PublishTask ORM 对象转换为 TaskResponse schema（避免重复构造代码）"""
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
        article_title=task.article.title if task.article else None,
        account_nickname=task.account.nickname if task.account else None,
    )


@router.get("", response_model=TaskListResponse, summary="获取任务列表")
async def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query(None, description="状态过滤：pending / running / success / failed"),
    account_id: int = Query(None, description="账号ID过滤"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """获取发布任务列表"""
    # 解析日期参数
    parsed_start = None
    parsed_end = None
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass

    # 总数
    count_stmt = select(func.count(PublishTask.id))
    if status:
        count_stmt = count_stmt.where(PublishTask.status == status)
    if account_id:
        count_stmt = count_stmt.where(PublishTask.account_id == account_id)
    if parsed_start:
        count_stmt = count_stmt.where(PublishTask.created_at >= parsed_start)
    if parsed_end:
        count_stmt = count_stmt.where(PublishTask.created_at < parsed_end)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页查询（使用 selectin 预加载关联数据）
    stmt = select(PublishTask).order_by(PublishTask.created_at.desc())
    if status:
        stmt = stmt.where(PublishTask.status == status)
    if account_id:
        stmt = stmt.where(PublishTask.account_id == account_id)
    if parsed_start:
        stmt = stmt.where(PublishTask.created_at >= parsed_start)
    if parsed_end:
        stmt = stmt.where(PublishTask.created_at < parsed_end)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    # 组装响应
    items = [_task_to_response(task) for task in tasks]

    return TaskListResponse(total=total, items=items)


# NOTE: static routes MUST be before /{task_id} to avoid FastAPI treating them as a task_id


@router.get("/export", summary="导出任务为CSV")
async def export_tasks(
    format: str = Query("csv", description="导出格式，目前仅支持 csv"),
    status: str = Query(None, description="状态过滤"),
    account_id: int = Query(None, description="账号ID过滤"),
    start_date: str = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str = Query(None, description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """导出任务列表为CSV文件"""
    if format != "csv":
        raise HTTPException(status_code=400, detail="目前仅支持 CSV 格式导出")

    # 解析日期参数
    parsed_start = None
    parsed_end = None
    if start_date:
        try:
            parsed_start = datetime.strptime(start_date, "%Y-%m-%d")
        except ValueError:
            pass
    if end_date:
        try:
            parsed_end = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        except ValueError:
            pass

    # 查询所有匹配的任务（不分页）
    stmt = select(PublishTask).order_by(PublishTask.created_at.desc())
    if status:
        stmt = stmt.where(PublishTask.status == status)
    if account_id:
        stmt = stmt.where(PublishTask.account_id == account_id)
    if parsed_start:
        stmt = stmt.where(PublishTask.created_at >= parsed_start)
    if parsed_end:
        stmt = stmt.where(PublishTask.created_at < parsed_end)

    result = await db.execute(stmt)
    tasks = result.scalars().all()

    # 生成 CSV
    output = io.StringIO()
    # Write BOM for Excel compatibility with Chinese characters
    output.write('\ufeff')
    writer = csv.writer(output)
    writer.writerow([
        "任务ID", "文章标题", "发布账号", "状态", "计划时间",
        "重试次数", "错误信息", "创建时间"
    ])

    status_map = {
        "pending": "等待中",
        "running": "运行中",
        "success": "成功",
        "failed": "失败",
        "cancelled": "已取消",
    }

    for task in tasks:
        writer.writerow([
            task.id,
            task.article.title if task.article else "",
            task.account.nickname if task.account else "",
            status_map.get(task.status, task.status),
            task.scheduled_at.strftime("%Y-%m-%d %H:%M:%S") if task.scheduled_at else "",
            task.retry_count,
            task.error_message or "",
            task.created_at.strftime("%Y-%m-%d %H:%M:%S") if task.created_at else "",
        ])

    output.seek(0)
    logger.info(f"导出任务CSV: {len(tasks)} 条记录")

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename=tasks_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        },
    )


@router.get("/calendar", response_model=list[TaskResponse], summary="获取日历视图任务")
async def get_calendar_tasks(
    start: str = Query(..., description="开始日期 YYYY-MM-DD"),
    end: str = Query(..., description="结束日期 YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """获取日期范围内的所有任务（用于日历视图）

    查询逻辑：返回 scheduled_at 或 created_at 落在 [start, end) 范围内的任务。
    定时任务以 scheduled_at 为准，立即执行的任务（scheduled_at 为空）以 created_at 为准。
    """
    try:
        parsed_start = datetime.strptime(start, "%Y-%m-%d")
        parsed_end = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(status_code=400, detail="日期格式错误，请使用 YYYY-MM-DD")

    from sqlalchemy import or_, and_

    stmt = (
        select(PublishTask)
        .where(
            or_(
                # 有 scheduled_at 的任务：按 scheduled_at 筛选
                and_(
                    PublishTask.scheduled_at.isnot(None),
                    PublishTask.scheduled_at >= parsed_start,
                    PublishTask.scheduled_at < parsed_end,
                ),
                # 没有 scheduled_at 的立即执行任务：按 created_at 筛选
                and_(
                    PublishTask.scheduled_at.is_(None),
                    PublishTask.created_at >= parsed_start,
                    PublishTask.created_at < parsed_end,
                ),
            )
        )
        .order_by(PublishTask.created_at.asc())
    )
    result = await db.execute(stmt)
    tasks = result.scalars().all()

    return [_task_to_response(task) for task in tasks]


@router.get("/{task_id}", response_model=TaskResponse, summary="获取任务详情")
async def get_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取任务详情"""
    task = await db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    return _task_to_response(task)


@router.get(
    "/{task_id}/records",
    response_model=list[PublishRecordResponse],
    summary="获取任务的发布记录",
)
async def get_task_records(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取某个任务的所有发布执行记录"""
    # 检查任务是否存在
    task = await db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    stmt = (
        select(PublishRecord)
        .where(PublishRecord.task_id == task_id)
        .order_by(PublishRecord.started_at.desc())
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    return records


@router.get("/{task_id}/screenshot", summary="获取任务截图")
async def get_task_screenshot(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """获取发布成功后的截图"""
    stmt = (
        select(PublishRecord)
        .where(PublishRecord.task_id == task_id)
        .where(PublishRecord.screenshot_path.isnot(None))
        .order_by(PublishRecord.finished_at.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    record = result.scalar_one_or_none()

    if not record or not record.screenshot_path:
        raise HTTPException(status_code=404, detail="截图不存在")

    if not os.path.exists(record.screenshot_path):
        raise HTTPException(status_code=404, detail="截图文件未找到")

    return FileResponse(
        record.screenshot_path,
        media_type="image/png",
        filename=os.path.basename(record.screenshot_path),
    )


@router.delete("/{task_id}", response_model=TaskResponse, summary="取消任务")
async def cancel_task(
    task_id: int,
    db: AsyncSession = Depends(get_db),
):
    """取消 pending 状态的任务"""
    task = await db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status != "pending":
        raise HTTPException(
            status_code=400,
            detail=f"只能取消 pending 状态的任务，当前状态: {task.status}",
        )

    task.status = "cancelled"
    task.error_message = "用户手动取消"
    task.updated_at = datetime.now()
    await db.commit()
    await db.refresh(task)

    # 移除 APScheduler 中对应的 job（防止已调度的 job 继续触发）
    await task_scheduler.cancel_task(task_id)

    # 发布 task_cancelled SSE 事件
    await event_bus.publish("task_cancelled", {
        "task_id": task.id,
        "article_id": task.article_id,
        "account_id": task.account_id,
        "status": "cancelled",
    })

    logger.info(f"取消任务: task_id={task_id}")
    return _task_to_response(task)


# ==================== 任务更新 ====================


class TaskUpdateRequest(BaseModel):
    """任务更新请求"""
    scheduled_at: datetime | None = None


@router.put("/{task_id}", response_model=TaskResponse, summary="更新任务")
async def update_task(
    task_id: int,
    request: TaskUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新任务（如重新调度时间）"""
    task = await db.get(PublishTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if task.status not in ("pending",):
        raise HTTPException(
            status_code=400,
            detail=f"只能更新 pending 状态的任务，当前状态: {task.status}",
        )

    if request.scheduled_at is not None:
        task.scheduled_at = request.scheduled_at
        task.updated_at = datetime.now()
        logger.info(f"更新任务调度时间: task_id={task_id}, scheduled_at={request.scheduled_at}")

    await db.commit()
    await db.refresh(task)

    return _task_to_response(task)
