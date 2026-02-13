"""
文章相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class ArticleGenerateRequest(BaseModel):
    """AI 生成文章请求"""
    topic: str = Field(..., min_length=1, max_length=200, description="文章主题")
    style: str = Field(
        default="professional",
        description="写作风格：professional(专业) / casual(轻松) / storytelling(叙事) / tutorial(教程)",
    )
    word_count: int = Field(default=1500, ge=300, le=10000, description="目标字数")
    ai_provider: str = Field(
        default="gemini",
        description="AI 提供商：gemini / openai / claude",
    )
    enable_images: bool = Field(
        default=False,
        description="是否启用 AI 配图（封面+正文插图）",
    )


class ArticleCreateRequest(BaseModel):
    """手动创建文章请求"""
    title: str = Field(..., min_length=1, max_length=200, description="文章标题")
    content: str = Field(..., min_length=1, description="文章内容")
    summary: Optional[str] = Field(default="", description="文章摘要")
    tags: Optional[list[str]] = Field(default=[], description="话题标签")
    ai_provider: Optional[str] = Field(default="manual", description="来源")
    category: Optional[str] = Field(default=None, description="文章分类")
    images: Optional[dict | list] = Field(default=None, description="图片数据")


class ArticleUpdateRequest(BaseModel):
    """更新文章请求"""
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    summary: Optional[str] = None
    tags: Optional[list[str]] = None
    status: Optional[str] = None
    category: Optional[str] = None


# ==================== 系列文章请求模型 ====================

class SeriesOutlineRequest(BaseModel):
    """系列文章大纲生成请求"""
    topic: str = Field(..., min_length=1, max_length=200, description="系列主题")
    count: int = Field(default=5, ge=2, le=20, description="系列文章数量")
    ai_provider: str = Field(default="gemini", description="AI 提供商")


class SeriesOutlineArticle(BaseModel):
    """系列大纲中的单篇文章"""
    order: int
    title: str
    description: str
    key_points: list[str]


class SeriesOutlineResponse(BaseModel):
    """系列文章大纲响应"""
    series_title: str
    description: str
    articles: list[SeriesOutlineArticle]


class SeriesArticleInput(BaseModel):
    """系列生成时单篇文章的输入"""
    title: str
    description: str
    key_points: list[str]


class SeriesGenerateRequest(BaseModel):
    """系列文章批量生成请求"""
    series_title: str = Field(..., min_length=1, max_length=200, description="系列标题")
    articles: list[SeriesArticleInput] = Field(..., description="文章列表")
    style: str = Field(default="professional", description="写作风格")
    word_count: int = Field(default=1500, ge=300, le=10000, description="每篇目标字数")
    ai_provider: str = Field(default="gemini", description="AI 提供商")


# ==================== 改写请求模型 ====================

class ArticleRewriteRequest(BaseModel):
    """文章改写请求"""
    article_id: int = Field(..., description="原文章 ID")
    style: str = Field(default="professional", description="改写风格")
    instruction: Optional[str] = Field(default=None, description="额外改写指令")


# ==================== 响应模型 ====================

class ArticleResponse(BaseModel):
    """文章响应"""
    id: int
    title: str
    content: str
    summary: str
    tags: list[str] | None
    word_count: int
    ai_provider: str
    status: str
    created_at: datetime
    category: Optional[str] = None
    # 图片数据
    images: Optional[dict | list] = None
    # 系列文章字段
    series_id: Optional[str] = None
    series_order: Optional[int] = None
    series_title: Optional[str] = None

    model_config = {"from_attributes": True}


class ArticleListResponse(BaseModel):
    """文章列表响应"""
    total: int
    items: list[ArticleResponse]


# ==================== 智能体请求/响应模型 ====================

class AgentGenerateRequest(BaseModel):
    """智能体生成请求"""
    article_ids: list[int] = Field(..., min_length=1, max_length=10, description="参考文章 ID 列表")
    count: int = Field(default=5, ge=1, le=20, description="要生成的文章数量")
    style: Optional[str] = Field(default=None, description="写作风格（为空则由 AI 自动推荐）")
    word_count: int = Field(default=1500, ge=300, le=10000, description="每篇目标字数")
    ai_provider: str = Field(default="gemini", description="AI 提供商")


# ==================== 故事生成请求模型 ====================

class StoryGenerateRequest(BaseModel):
    """故事生成请求"""
    reference_text: str = Field(
        ..., min_length=50, max_length=50000,
        description="参考素材原文（新闻、背景资料、故事种子等）",
    )
    reference_article_ids: Optional[list[int]] = Field(
        default=None, max_length=5,
        description="可选：已有文章ID作为额外参考",
    )
    chapter_count: int = Field(
        default=5, ge=3, le=8,
        description="章节数量（3-8章）",
    )
    total_word_count: int = Field(
        default=15000, ge=8000, le=25000,
        description="总目标字数（8000-25000）",
    )
    story_type: str = Field(
        default="corruption",
        description="故事类型：corruption/historical/suspense/romance/workplace",
    )
    ai_provider: str = Field(default="gemini", description="AI 提供商")
