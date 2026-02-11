"""
通知相关 API 路由
提供通知的增删改查功能
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.notification import Notification

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["通知中心"])


# ==================== Pydantic 模型 ====================


class NotificationResponse(BaseModel):
    """通知响应"""
    id: int
    title: str
    content: Optional[str] = None
    type: str = "info"
    is_read: bool = False
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """通知列表响应"""
    total: int
    items: list[NotificationResponse]


class UnreadCountResponse(BaseModel):
    """未读数量响应"""
    count: int


class NotificationCreateRequest(BaseModel):
    """创建通知请求"""
    title: str
    content: Optional[str] = None
    type: str = "info"


# ==================== API 路由 ====================


@router.get("/unread-count", response_model=UnreadCountResponse, summary="获取未读通知数量")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
):
    """获取未读通知数量"""
    result = await db.execute(
        select(func.count(Notification.id)).where(Notification.is_read == False)  # noqa: E712
    )
    count = result.scalar() or 0
    return UnreadCountResponse(count=count)


@router.put("/read-all", summary="标记所有通知为已读")
async def mark_all_read(
    db: AsyncSession = Depends(get_db),
):
    """标记所有未读通知为已读"""
    await db.execute(
        update(Notification)
        .where(Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "所有通知已标记为已读"}


@router.get("", response_model=NotificationListResponse, summary="获取通知列表")
async def list_notifications(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    is_read: Optional[bool] = Query(None, description="是否已读"),
    db: AsyncSession = Depends(get_db),
):
    """获取通知列表（分页，可按已读状态筛选）"""
    # 计算总数
    count_stmt = select(func.count(Notification.id))
    if is_read is not None:
        count_stmt = count_stmt.where(Notification.is_read == is_read)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页查询
    stmt = select(Notification).order_by(Notification.created_at.desc())
    if is_read is not None:
        stmt = stmt.where(Notification.is_read == is_read)
    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(stmt)
    notifications = result.scalars().all()

    items = [
        NotificationResponse(
            id=n.id,
            title=n.title,
            content=n.content,
            type=n.type,
            is_read=n.is_read,
            created_at=n.created_at,
        )
        for n in notifications
    ]

    return NotificationListResponse(total=total, items=items)


@router.post("", response_model=NotificationResponse, summary="创建通知")
async def create_notification(
    request: NotificationCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建一条新通知"""
    notification = Notification(
        title=request.title,
        content=request.content,
        type=request.type,
    )
    db.add(notification)
    await db.commit()
    await db.refresh(notification)

    logger.info(f"创建通知: id={notification.id}, title={notification.title}")
    return NotificationResponse(
        id=notification.id,
        title=notification.title,
        content=notification.content,
        type=notification.type,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )


@router.put("/{notification_id}/read", response_model=NotificationResponse, summary="标记单条通知为已读")
async def mark_as_read(
    notification_id: int,
    db: AsyncSession = Depends(get_db),
):
    """标记单条通知为已读"""
    notification = await db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return NotificationResponse(
        id=notification.id,
        title=notification.title,
        content=notification.content,
        type=notification.type,
        is_read=notification.is_read,
        created_at=notification.created_at,
    )
