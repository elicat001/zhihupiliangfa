"""
发布任务模型
记录每一次发布的任务和执行结果
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class PublishTask(Base):
    """发布任务表"""
    __tablename__ = "publish_tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 关联的文章 ID
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False
    )
    # 关联的账号 ID
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    # 任务状态：pending / running / success / failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 计划执行时间（为 None 表示立即执行）
    scheduled_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )
    # 重试次数
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 错误信息
    error_message: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, default=None
    )
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # 关系（用于联查）
    article = relationship("Article", lazy="selectin")
    account = relationship("Account", lazy="selectin")


class PublishRecord(Base):
    """发布执行记录表（详细记录每次发布的执行情况）"""
    __tablename__ = "publish_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 关联的任务 ID
    task_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("publish_tasks.id"), nullable=False
    )
    # 关联的文章 ID
    article_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("articles.id"), nullable=False
    )
    # 关联的账号 ID
    account_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("accounts.id"), nullable=False
    )
    # 发布后的知乎文章 URL
    zhihu_article_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )
    # 发布状态
    publish_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending"
    )
    # 截图路径
    screenshot_path: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True, default=None
    )
    # 开始时间
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )
    # 结束时间
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, nullable=True, default=None
    )
