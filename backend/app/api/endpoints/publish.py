"""
发布操作 API 端点

提供立即发布、定时发布、批量发布功能。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.post("/now")
async def publish_now(data: dict):
    """立即发布文章到知乎"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/schedule")
async def schedule_publish(data: dict):
    """定时发布"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/batch")
async def batch_publish(data: dict):
    """批量发布"""
    raise HTTPException(status_code=501, detail="尚未实现")
