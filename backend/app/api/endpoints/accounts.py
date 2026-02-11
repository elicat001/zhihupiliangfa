"""
账号管理 API 端点

提供知乎账号的增删查以及登录管理功能。
"""

from fastapi import APIRouter, HTTPException

router = APIRouter()


@router.get("")
async def list_accounts():
    """获取账号列表"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("")
async def create_account(data: dict):
    """添加账号"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.delete("/{account_id}")
async def delete_account(account_id: int):
    """删除账号"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/{account_id}/check-login")
async def check_login(account_id: int):
    """检查账号登录状态"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/{account_id}/qrcode-login")
async def qrcode_login(account_id: int):
    """发起二维码登录"""
    raise HTTPException(status_code=501, detail="尚未实现")


@router.post("/{account_id}/import-cookie")
async def import_cookie(account_id: int, data: dict):
    """导入 Cookie 登录"""
    raise HTTPException(status_code=501, detail="尚未实现")
