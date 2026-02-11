"""
系统日志模型
记录系统运行事件，方便排查问题
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class SystemLog(Base):
    """系统日志表"""
    __tablename__ = "system_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 事件类型，如 login / publish / generate / error
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # 日志级别：info / warning / error
    level: Mapped[str] = mapped_column(String(20), nullable=False, default="info")
    # 日志消息
    message: Mapped[str] = mapped_column(Text, nullable=False)
    # 额外详情 JSON
    details: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, default=None)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
