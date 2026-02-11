"""
账号相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class AccountCreateRequest(BaseModel):
    """创建账号请求"""
    nickname: str = Field(..., min_length=1, max_length=100, description="知乎昵称")
    zhihu_uid: Optional[str] = Field(default="", description="知乎 UID")
    cookie_data: Optional[str] = Field(default="", description="Cookie 数据（JSON）")
    daily_limit: Optional[int] = Field(default=5, ge=1, le=50, description="每日发布上限")


class AccountUpdateRequest(BaseModel):
    """更新账号请求"""
    nickname: Optional[str] = Field(None, min_length=1, max_length=100)
    cookie_data: Optional[str] = None
    is_active: Optional[bool] = None
    daily_limit: Optional[int] = Field(None, ge=1, le=50)


class CookieLoginRequest(BaseModel):
    """Cookie 导入登录请求"""
    cookie_data: str = Field(..., description="Cookie JSON 字符串或分号分隔的 Cookie")


# ==================== 响应模型 ====================

class AccountResponse(BaseModel):
    """账号响应"""
    id: int
    nickname: str
    zhihu_uid: str
    is_active: bool
    login_status: str
    daily_limit: int
    created_at: datetime

    model_config = {"from_attributes": True}


class AccountListResponse(BaseModel):
    """账号列表响应"""
    total: int
    items: list[AccountResponse]


class QRCodeLoginResponse(BaseModel):
    """扫码登录响应"""
    qrcode_base64: str = Field(..., description="二维码图片的 base64 编码")
    message: str = Field(default="请使用知乎 APP 扫描二维码登录")


class LoginCheckResponse(BaseModel):
    """登录态检查响应"""
    is_logged_in: bool
    nickname: Optional[str] = None
    message: str
