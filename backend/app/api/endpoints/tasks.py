"""
任务管理 API 端点

提供发布任务的查询与取消功能。
"""

from typing import Optional
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()


@router.get("")
async def list_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[str] = None,
    article_id: Optional[int] = None,
    account_id: Optional[int] = None,
):
    """获取任务列表（分页）"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int):
    """取消任务"""
    raise HTTPException(status_code=501, detail="尚未实现")
