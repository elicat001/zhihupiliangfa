"""
知乎问答相关的 Pydantic 请求/响应模型
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# ==================== 请求模型 ====================

class QuestionFetchRequest(BaseModel):
    """抓取知乎问题请求"""
    account_id: int = Field(..., description="用于抓取的账号ID")
    sources: list[str] = Field(default=["invited", "recommended"], description="抓取来源")
    max_count: int = Field(default=20, ge=1, le=50, description="最大抓取数量")


class AnswerGenerateRequest(BaseModel):
    """AI 生成回答请求"""
    question_id: int = Field(..., description="问题表ID")
    account_id: int = Field(..., description="回答账号ID")
    style: str = Field(default="professional", description="回答风格")
    word_count: int = Field(default=1000, ge=200, le=5000, description="目标字数")
    ai_provider: Optional[str] = Field(default=None, description="AI提供商")
    anti_ai_level: int = Field(default=3, ge=0, le=3, description="反AI检测等级")


class AnswerUpdateRequest(BaseModel):
    """更新回答请求"""
    content: Optional[str] = Field(None, min_length=1)
    style: Optional[str] = None


class AnswerPublishRequest(BaseModel):
    """发布回答请求"""
    account_id: Optional[int] = Field(default=None, description="发布账号ID，为空则用生成时的账号")


# ==================== 响应模型 ====================

class QuestionResponse(BaseModel):
    """问题响应"""
    id: int
    question_id: str
    title: str
    detail: str | None
    topics: list[str] | None
    follower_count: int
    answer_count: int
    view_count: int
    source: str
    score: float
    status: str
    account_id: int | None
    fetched_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}


class AnswerResponse(BaseModel):
    """回答响应"""
    id: int
    question_id: int
    zhihu_question_id: str
    account_id: int
    content: str
    word_count: int
    ai_provider: str | None
    style: str
    anti_ai_level: int
    status: str
    zhihu_answer_url: str | None
    screenshot_path: str | None
    publish_error: str | None
    created_at: datetime
    published_at: datetime | None
    # Joined fields
    question_title: str | None = None
    account_nickname: str | None = None

    model_config = {"from_attributes": True}


class QAStatsResponse(BaseModel):
    """问答统计响应"""
    total_questions: int = 0
    pending_questions: int = 0
    answered_questions: int = 0
    total_answers: int = 0
    published_answers: int = 0
    failed_answers: int = 0
