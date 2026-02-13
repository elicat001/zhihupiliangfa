"""
知乎账号模型
管理多个知乎账号的登录态和配置
"""

from datetime import datetime, timezone
from sqlalchemy import Integer, String, Text, Boolean, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow():
    """返回当前 UTC 时间（兼容 Python 3.12+ 弃用 datetime.utcnow）"""
    return datetime.now(timezone.utc)


class Account(Base):
    """知乎账号表"""
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 知乎昵称
    nickname: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    # 知乎用户 UID
    zhihu_uid: Mapped[str] = mapped_column(String(100), nullable=True, default="")
    # Cookie 数据（JSON 字符串）
    cookie_data: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # 浏览器 profile 目录名
    browser_profile: Mapped[str] = mapped_column(String(200), nullable=True, default="")
    # 是否启用
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 登录状态：logged_in / logged_out / expired
    login_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="logged_out"
    )
    # 每日发布上限
    daily_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=_utcnow
    )
