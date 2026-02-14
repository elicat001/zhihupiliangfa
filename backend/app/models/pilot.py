"""
ContentPilot 自动驾驶模型
内容方向管理 + 已生成主题去重
"""

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Integer, String, Text, DateTime, Boolean, JSON, Float
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


def _utcnow():
    return datetime.now(timezone.utc)


class ContentDirection(Base):
    """内容方向表 —— 定义自动生成的内容方向"""
    __tablename__ = "content_directions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 方向名称，如 "Python教程"、"职场心理学"
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 方向描述
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # 关键词列表 JSON，如 ["Python", "编程", "后端开发"]
    keywords: Mapped[list | None] = mapped_column(JSON, nullable=True, default=list)
    # 参考素材/种子文本（用于 Agent 模式分析）
    seed_text: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # AI 提供商偏好
    ai_provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, default=None)
    # 生成模式: single=单篇, agent=智能体, story=故事
    generation_mode: Mapped[str] = mapped_column(String(20), nullable=False, default="single")
    # 写作风格
    style: Mapped[str] = mapped_column(String(50), nullable=False, default="professional")
    # 目标字数
    word_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1500)
    # 每日生成数量
    daily_count: Mapped[int] = mapped_column(Integer, nullable=False, default=24)
    # 是否启用自动生成
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # 是否自动发布（生成后自动加入发布队列）
    auto_publish: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # 自动发布的账号ID（为空则用第一个已登录账号）
    publish_account_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    # 发布间隔（分钟），批量入队时每篇间隔
    publish_interval: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    # 今日已生成数量（每日重置）
    today_generated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # 上次重置日期（用于判断是否需要重置 today_generated）
    last_reset_date: Mapped[Optional[str]] = mapped_column(String(10), nullable=True, default=None)
    # 反AI检测强度: 0=关闭, 1=轻度, 2=中度, 3=强力
    anti_ai_level: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
    # 更新时间
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, default=None)


class GeneratedTopic(Base):
    """已生成主题表 —— 用于内容去重"""
    __tablename__ = "generated_topics"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 关联的内容方向ID
    direction_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    # 生成的主题/标题
    topic: Mapped[str] = mapped_column(String(200), nullable=False)
    # 标题的简化哈希（用于快速去重）
    title_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    # 关联的文章ID（生成成功后填入）
    article_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, default=None)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=_utcnow)
