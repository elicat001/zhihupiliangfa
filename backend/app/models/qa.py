"""
知乎问答模型
问题抓取 + AI 回答生成
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ZhihuQuestion(Base):
    """知乎问题表 —— 抓取的待回答问题"""
    __tablename__ = "zhihu_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 知乎问题ID
    question_id: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    # 问题标题
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    # 问题描述/补充说明
    detail: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # 问题话题标签
    topics: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # 关注者数
    follower_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 现有回答数
    answer_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 浏览量
    view_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 来源: invited/recommended/topic/hot/manual
    source: Mapped[str] = mapped_column(String(20), nullable=False)
    # 智能评分
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    # 状态: pending/answered/skipped/failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # 抓取时使用的账号ID
    account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    # 抓取时间
    fetched_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)


class ZhihuAnswer(Base):
    """知乎回答表 —— AI生成的回答"""
    __tablename__ = "zhihu_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 关联的问题表ID
    question_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 知乎问题ID, for URL construction
    zhihu_question_id: Mapped[str] = mapped_column(String(50), nullable=False)
    # 回答的账号ID
    account_id: Mapped[int] = mapped_column(Integer, nullable=False)
    # 回答内容 Markdown
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 字数
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # AI 提供商
    ai_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    # 回答风格
    style: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    # 反AI检测强度: 0=关闭, 1=轻度, 2=中度, 3=强力
    anti_ai_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # 状态: draft/publishing/published/failed
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # 知乎回答URL
    zhihu_answer_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    # 截图路径
    screenshot_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, default=None)
    # 发布错误信息
    publish_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, default=None)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 发布时间
    published_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)
