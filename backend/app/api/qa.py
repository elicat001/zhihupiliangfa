"""
知乎问答 API
问题抓取、AI回答生成、自动发布
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select, func, desc

from app.database.connection import async_session_factory
from app.models.qa import ZhihuQuestion, ZhihuAnswer
from app.models.account import Account
from app.schemas.qa import (
    QuestionFetchRequest,
    AnswerGenerateRequest,
    AnswerUpdateRequest,
    AnswerPublishRequest,
    QuestionResponse,
    AnswerResponse,
    QAStatsResponse,
)
from app.api.events import event_bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/qa", tags=["问答"])


def _utcnow():
    return datetime.now(timezone.utc)


# ==================== 问题相关 ====================

@router.get("/questions")
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    source: Optional[str] = None,
    sort_by: str = Query("score", pattern="^(score|created_at|follower_count|answer_count)$"),
):
    """获取问题列表（分页、筛选、排序）"""
    async with async_session_factory() as session:
        query = select(ZhihuQuestion)
        count_query = select(func.count(ZhihuQuestion.id))

        if status:
            query = query.where(ZhihuQuestion.status == status)
            count_query = count_query.where(ZhihuQuestion.status == status)
        if source:
            query = query.where(ZhihuQuestion.source == source)
            count_query = count_query.where(ZhihuQuestion.source == source)

        # Sort
        sort_column = {
            "score": ZhihuQuestion.score,
            "created_at": ZhihuQuestion.created_at,
            "follower_count": ZhihuQuestion.follower_count,
            "answer_count": ZhihuQuestion.answer_count,
        }.get(sort_by, ZhihuQuestion.score)
        query = query.order_by(desc(sort_column))

        # Count
        result = await session.execute(count_query)
        total = result.scalar() or 0

        # Paginate
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        questions = result.scalars().all()

        return {
            "total": total,
            "items": [QuestionResponse.model_validate(q) for q in questions],
        }


@router.post("/questions/fetch")
async def fetch_questions(req: QuestionFetchRequest):
    """从知乎抓取问题"""
    # Validate account
    async with async_session_factory() as session:
        account = await session.get(Account, req.account_id)
        if not account:
            raise HTTPException(400, "账号不存在")
        if account.login_status != "logged_in":
            raise HTTPException(400, "账号未登录，请先登录")
        profile_name = account.browser_profile or f"account_{account.id}"

    from app.core.zhihu_qa_fetcher import zhihu_qa_fetcher
    result = await zhihu_qa_fetcher.fetch_questions(
        profile_name=profile_name,
        account_id=req.account_id,
        sources=req.sources,
        max_count=req.max_count,
    )

    if "error" in result:
        raise HTTPException(500, result["error"])

    # Emit event
    await event_bus.publish("notification_created", {
        "title": "问题抓取完成",
        "content": f"新增 {result['new_questions']} 个问题",
        "type": "success",
    })

    return result


@router.post("/questions/manual")
async def add_manual_question(
    url: str = Query(..., description="知乎问题URL"),
    account_id: Optional[int] = None,
):
    """手动添加问题URL"""
    from app.core.zhihu_qa_fetcher import zhihu_qa_fetcher
    result = await zhihu_qa_fetcher.add_manual_question(url, account_id)
    if "error" in result:
        raise HTTPException(400, result["error"])
    return result


@router.delete("/questions/{question_id}")
async def skip_question(question_id: int):
    """跳过/删除问题"""
    async with async_session_factory() as session:
        question = await session.get(ZhihuQuestion, question_id)
        if not question:
            raise HTTPException(404, "问题不存在")

        # Check if there are answers
        stmt = select(func.count(ZhihuAnswer.id)).where(
            ZhihuAnswer.question_id == question_id
        )
        result = await session.execute(stmt)
        answer_count = result.scalar() or 0

        if answer_count > 0:
            # Just mark as skipped
            question.status = "skipped"
        else:
            # Delete entirely
            await session.delete(question)

        await session.commit()
        return {"message": "已跳过该问题"}


# ==================== 回答相关 ====================

@router.get("/answers")
async def list_answers(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = None,
    question_id: Optional[int] = None,
):
    """获取回答列表（分页）"""
    async with async_session_factory() as session:
        query = select(ZhihuAnswer)
        count_query = select(func.count(ZhihuAnswer.id))

        if status:
            query = query.where(ZhihuAnswer.status == status)
            count_query = count_query.where(ZhihuAnswer.status == status)
        if question_id:
            query = query.where(ZhihuAnswer.question_id == question_id)
            count_query = count_query.where(ZhihuAnswer.question_id == question_id)

        query = query.order_by(desc(ZhihuAnswer.created_at))

        result = await session.execute(count_query)
        total = result.scalar() or 0

        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await session.execute(query)
        answers = result.scalars().all()

        # Enrich with question title and account nickname
        items = []
        for answer in answers:
            data = AnswerResponse.model_validate(answer)
            # Get question title
            question = await session.get(ZhihuQuestion, answer.question_id)
            if question:
                data.question_title = question.title
            # Get account nickname
            account = await session.get(Account, answer.account_id)
            if account:
                data.account_nickname = account.nickname
            items.append(data)

        return {"total": total, "items": items}


@router.get("/answers/{answer_id}")
async def get_answer(answer_id: int):
    """获取回答详情"""
    async with async_session_factory() as session:
        answer = await session.get(ZhihuAnswer, answer_id)
        if not answer:
            raise HTTPException(404, "回答不存在")

        data = AnswerResponse.model_validate(answer)
        question = await session.get(ZhihuQuestion, answer.question_id)
        if question:
            data.question_title = question.title
        account = await session.get(Account, answer.account_id)
        if account:
            data.account_nickname = account.nickname

        return data


@router.post("/answers/generate")
async def generate_answer(req: AnswerGenerateRequest):
    """AI生成回答"""
    from app.core.qa_answer_generator import qa_answer_generator
    result = await qa_answer_generator.generate_answer(
        question_id=req.question_id,
        account_id=req.account_id,
        style=req.style,
        word_count=req.word_count,
        ai_provider=req.ai_provider,
        anti_ai_level=req.anti_ai_level,
    )

    if not result:
        raise HTTPException(500, "回答生成失败")

    await event_bus.publish("notification_created", {
        "title": "回答生成完成",
        "content": f"问题: {result.get('question_title', '')[:30]}",
        "type": "success",
    })

    return result


@router.put("/answers/{answer_id}")
async def update_answer(answer_id: int, req: AnswerUpdateRequest):
    """编辑回答内容"""
    async with async_session_factory() as session:
        answer = await session.get(ZhihuAnswer, answer_id)
        if not answer:
            raise HTTPException(404, "回答不存在")
        if answer.status not in ("draft", "failed"):
            raise HTTPException(400, "只能编辑草稿或失败状态的回答")

        if req.content is not None:
            answer.content = req.content
            answer.word_count = len(req.content.replace(" ", "").replace("\n", ""))
        if req.style is not None:
            answer.style = req.style

        await session.commit()
        return {"message": "更新成功"}


@router.post("/answers/{answer_id}/publish")
async def publish_answer(answer_id: int, req: AnswerPublishRequest = None):
    """发布回答到知乎"""
    if req is None:
        req = AnswerPublishRequest()

    async with async_session_factory() as session:
        answer = await session.get(ZhihuAnswer, answer_id)
        if not answer:
            raise HTTPException(404, "回答不存在")
        if answer.status == "published":
            raise HTTPException(400, "该回答已发布")

        # Determine account
        account_id = req.account_id or answer.account_id
        account = await session.get(Account, account_id)
        if not account:
            raise HTTPException(400, "账号不存在")
        if account.login_status != "logged_in":
            raise HTTPException(400, "账号未登录")

        profile_name = account.browser_profile or f"account_{account.id}"

        # Update status
        answer.status = "publishing"
        await session.commit()

    # Publish
    from app.core.zhihu_qa_publisher import zhihu_qa_publisher
    result = await zhihu_qa_publisher.publish_answer(
        profile_name=profile_name,
        question_id=answer.zhihu_question_id,
        content=answer.content,
    )

    # Update answer record
    async with async_session_factory() as session:
        answer = await session.get(ZhihuAnswer, answer_id)
        if result["success"]:
            answer.status = "published"
            answer.zhihu_answer_url = result.get("answer_url")
            answer.screenshot_path = result.get("screenshot_path")
            answer.published_at = _utcnow()

            await event_bus.publish("notification_created", {
                "title": "回答发布成功",
                "content": f"问题 ID: {answer.zhihu_question_id}",
                "type": "success",
            })
        else:
            answer.status = "failed"
            answer.publish_error = result.get("message")
            answer.screenshot_path = result.get("screenshot_path")

            await event_bus.publish("notification_created", {
                "title": "回答发布失败",
                "content": result.get("message", "未知错误"),
                "type": "error",
            })

        await session.commit()

    return result


@router.delete("/answers/{answer_id}")
async def delete_answer(answer_id: int):
    """删除回答"""
    async with async_session_factory() as session:
        answer = await session.get(ZhihuAnswer, answer_id)
        if not answer:
            raise HTTPException(404, "回答不存在")
        if answer.status == "published":
            raise HTTPException(400, "已发布的回答不能删除")

        # Reset question status if no other answers
        stmt = select(func.count(ZhihuAnswer.id)).where(
            ZhihuAnswer.question_id == answer.question_id,
            ZhihuAnswer.id != answer_id,
        )
        result = await session.execute(stmt)
        other_answers = result.scalar() or 0

        if other_answers == 0:
            question = await session.get(ZhihuQuestion, answer.question_id)
            if question and question.status == "answered":
                question.status = "pending"

        await session.delete(answer)
        await session.commit()
        return {"message": "已删除"}


# ==================== 统计 ====================

@router.get("/stats")
async def get_qa_stats():
    """获取问答统计"""
    async with async_session_factory() as session:
        # Question stats
        total_q = (await session.execute(
            select(func.count(ZhihuQuestion.id))
        )).scalar() or 0
        pending_q = (await session.execute(
            select(func.count(ZhihuQuestion.id)).where(ZhihuQuestion.status == "pending")
        )).scalar() or 0
        answered_q = (await session.execute(
            select(func.count(ZhihuQuestion.id)).where(ZhihuQuestion.status == "answered")
        )).scalar() or 0

        # Answer stats
        total_a = (await session.execute(
            select(func.count(ZhihuAnswer.id))
        )).scalar() or 0
        published_a = (await session.execute(
            select(func.count(ZhihuAnswer.id)).where(ZhihuAnswer.status == "published")
        )).scalar() or 0
        failed_a = (await session.execute(
            select(func.count(ZhihuAnswer.id)).where(ZhihuAnswer.status == "failed")
        )).scalar() or 0

        return QAStatsResponse(
            total_questions=total_q,
            pending_questions=pending_q,
            answered_questions=answered_q,
            total_answers=total_a,
            published_answers=published_a,
            failed_answers=failed_a,
        )
