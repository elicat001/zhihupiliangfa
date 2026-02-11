"""
系统设置 API 端点

提供系统配置的读取与更新功能。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
async def get_settings():
    """获取当前系统设置"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.put("")
async def update_settings(data: dict):
    """更新系统设置"""
    raise HTTPException(status_code=501, detail="尚未实现")
