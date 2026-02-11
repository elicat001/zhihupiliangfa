"""
数据统计 API 端点

提供仪表盘统计数据。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_stats():
    """获取仪表盘统计数据"""
    raise HTTPException(status_code=501, detail="尚未实现")
