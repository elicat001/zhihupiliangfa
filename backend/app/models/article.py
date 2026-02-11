"""
文章模型
存储 AI 生成的文章数据
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Article(Base):
    """文章表"""
    __tablename__ = "articles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 文章标题
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    # 文章正文内容（Markdown / HTML）
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # 文章摘要
    summary: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # 话题标签列表 JSON，如 ["Python", "编程"]
    tags: Mapped[dict | list | None] = mapped_column(JSON, nullable=True, default=list)
    # 字数统计
    word_count: Mapped[int] = mapped_column(Integer, nullable=True, default=0)
    # 使用的 AI 提供商，如 openai / deepseek / claude
    ai_provider: Mapped[str] = mapped_column(String(50), nullable=True, default="")
    # 文章状态：draft=草稿, published=已发布
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="draft")
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    # 文章分类
    category: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)

    # ---- 系列文章字段 ----
    # 系列 UUID，同一系列的文章共享同一个 series_id
    series_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, default=None)
    # 在系列中的顺序
    series_order: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    # 系列标题
    series_title: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, default=None)
