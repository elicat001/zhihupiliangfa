"""
内容模板模型
存储 AI 生成文章的 Prompt 模板
"""

from datetime import datetime
from sqlalchemy import Integer, String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class PromptTemplate(Base):
    """Prompt 模板表"""
    __tablename__ = "prompt_templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # 模板名称
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    # 模板描述
    description: Mapped[str] = mapped_column(Text, nullable=True, default="")
    # 系统提示词（覆盖默认 system prompt）
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # 用户提示词模板，支持 {topic}, {style}, {word_count} 占位符
    user_prompt_template: Mapped[str] = mapped_column(Text, nullable=False)
    # 默认写作风格
    default_style: Mapped[str] = mapped_column(String(50), nullable=True, default="professional")
    # 默认目标字数
    default_word_count: Mapped[int] = mapped_column(Integer, nullable=True, default=1500)
    # 是否为内置模板（内置模板不可删除）
    is_builtin: Mapped[bool] = mapped_column(Integer, nullable=False, default=False)
    # 创建时间
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )
