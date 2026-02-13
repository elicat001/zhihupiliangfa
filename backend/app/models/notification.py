"""
通知模型
记录系统通知消息
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.models.base import Base


def _utcnow():
    """返回当前 UTC 时间（兼容 Python 3.12+ 弃用 datetime.utcnow）"""
    return datetime.now(timezone.utc)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=True)
    type = Column(String(50), default="info")  # info, success, warning, error
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
