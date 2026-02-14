"""
ContentPilot 自动驾驶 API
提供内容方向 CRUD、自动驾驶控制、手动触发等接口
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select, func, delete

from app.database.connection import async_session_factory
from app.models.pilot import ContentDirection, GeneratedTopic
from app.core.content_pilot import content_pilot

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pilot", tags=["自动驾驶"])


# ==================== 请求/响应模型 ====================

class DirectionCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = ""
    keywords: list[str] = []
    seed_text: str = ""
    ai_provider: Optional[str] = None
    generation_mode: str = "single"
    style: str = "professional"
    word_count: int = 1500
    daily_count: int = 24
    is_active: bool = False
    auto_publish: bool = True
    publish_account_id: Optional[int] = None
    publish_interval: int = 30
    anti_ai_level: int = 3
    schedule_start: Optional[str] = None
    schedule_end: Optional[str] = None
    schedule_days: Optional[int] = None


class DirectionUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    keywords: Optional[list[str]] = None
    seed_text: Optional[str] = None
    ai_provider: Optional[str] = None
    generation_mode: Optional[str] = None
    style: Optional[str] = None
    word_count: Optional[int] = None
    daily_count: Optional[int] = None
    is_active: Optional[bool] = None
    auto_publish: Optional[bool] = None
    publish_account_id: Optional[int] = None
    publish_interval: Optional[int] = None
    anti_ai_level: Optional[int] = None
    schedule_start: Optional[str] = None
    schedule_end: Optional[str] = None
    schedule_days: Optional[int] = None


class DirectionResponse(BaseModel):
    id: int
    name: str
    description: str
    keywords: list
    seed_text: str
    ai_provider: Optional[str]
    generation_mode: str
    style: str
    word_count: int
    daily_count: int
    is_active: bool
    auto_publish: bool
    publish_account_id: Optional[int]
    publish_interval: int
    today_generated: int
    anti_ai_level: int
    schedule_start: Optional[str]
    schedule_end: Optional[str]
    schedule_days: Optional[int]
    created_at: Optional[str]
    updated_at: Optional[str]

    # 额外统计
    total_generated: int = 0


class PilotStatusResponse(BaseModel):
    is_running: bool
    active_directions: int
    total_directions: int
    today_total_generated: int


# ==================== 内容方向 CRUD ====================

@router.get("/directions", summary="获取所有内容方向")
async def list_directions():
    """获取所有内容方向列表（含统计信息）"""
    async with async_session_factory() as session:
        stmt = select(ContentDirection).order_by(ContentDirection.created_at.desc())
        result = await session.execute(stmt)
        directions = result.scalars().all()

        items = []
        for d in directions:
            # 统计该方向总生成数
            count_stmt = select(func.count(GeneratedTopic.id)).where(
                GeneratedTopic.direction_id == d.id
            )
            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            items.append(DirectionResponse(
                id=d.id,
                name=d.name,
                description=d.description or "",
                keywords=d.keywords or [],
                seed_text=d.seed_text or "",
                ai_provider=d.ai_provider,
                generation_mode=d.generation_mode,
                style=d.style,
                word_count=d.word_count,
                daily_count=d.daily_count,
                is_active=d.is_active,
                auto_publish=d.auto_publish,
                publish_account_id=d.publish_account_id,
                publish_interval=d.publish_interval,
                today_generated=d.today_generated,
                anti_ai_level=d.anti_ai_level,
                schedule_start=d.schedule_start,
                schedule_end=d.schedule_end,
                schedule_days=d.schedule_days,
                created_at=str(d.created_at) if d.created_at else None,
                updated_at=str(d.updated_at) if d.updated_at else None,
                total_generated=total,
            ))

        return {"total": len(items), "items": items}


@router.post("/directions", summary="创建内容方向")
async def create_direction(request: DirectionCreateRequest):
    """创建新的内容方向"""
    async with async_session_factory() as session:
        direction = ContentDirection(
            name=request.name,
            description=request.description,
            keywords=request.keywords,
            seed_text=request.seed_text,
            ai_provider=request.ai_provider,
            generation_mode=request.generation_mode,
            style=request.style,
            word_count=request.word_count,
            daily_count=request.daily_count,
            is_active=request.is_active,
            auto_publish=request.auto_publish,
            publish_account_id=request.publish_account_id,
            publish_interval=request.publish_interval,
            anti_ai_level=request.anti_ai_level,
            schedule_start=request.schedule_start,
            schedule_end=request.schedule_end,
            schedule_days=request.schedule_days,
        )
        session.add(direction)
        await session.commit()
        await session.refresh(direction)

        logger.info(f"创建内容方向: {direction.name} (ID={direction.id})")
        return {"message": "创建成功", "id": direction.id}


@router.put("/directions/{direction_id}", summary="更新内容方向")
async def update_direction(direction_id: int, request: DirectionUpdateRequest):
    """更新内容方向配置"""
    async with async_session_factory() as session:
        direction = await session.get(ContentDirection, direction_id)
        if not direction:
            raise HTTPException(status_code=404, detail="内容方向不存在")

        update_data = request.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(direction, key, value)
        direction.updated_at = datetime.now(timezone.utc)

        await session.commit()

        logger.info(f"更新内容方向: {direction.name} (ID={direction.id})")
        return {"message": "更新成功"}


@router.delete("/directions/{direction_id}", summary="删除内容方向")
async def delete_direction(direction_id: int):
    """删除内容方向及其关联的已生成主题记录"""
    async with async_session_factory() as session:
        direction = await session.get(ContentDirection, direction_id)
        if not direction:
            raise HTTPException(status_code=404, detail="内容方向不存在")

        # 删除关联的已生成主题
        await session.execute(
            delete(GeneratedTopic).where(
                GeneratedTopic.direction_id == direction_id
            )
        )

        await session.delete(direction)
        await session.commit()

        logger.info(f"删除内容方向: {direction.name} (ID={direction_id})")
        return {"message": "删除成功"}


# ==================== 自动驾驶控制 ====================

@router.get("/status", response_model=PilotStatusResponse, summary="获取自动驾驶状态")
async def get_pilot_status():
    """获取自动驾驶整体状态"""
    async with async_session_factory() as session:
        # 总方向数
        total_stmt = select(func.count(ContentDirection.id))
        total = (await session.execute(total_stmt)).scalar() or 0

        # 活跃方向数
        active_stmt = select(func.count(ContentDirection.id)).where(
            ContentDirection.is_active == True  # noqa: E712
        )
        active = (await session.execute(active_stmt)).scalar() or 0

        # 今日总生成数
        today_stmt = select(func.sum(ContentDirection.today_generated))
        today_total = (await session.execute(today_stmt)).scalar() or 0

    return PilotStatusResponse(
        is_running=active > 0,
        active_directions=active,
        total_directions=total,
        today_total_generated=today_total,
    )


@router.post("/directions/{direction_id}/toggle", summary="启用/停用方向")
async def toggle_direction(direction_id: int):
    """切换内容方向的启用状态"""
    async with async_session_factory() as session:
        direction = await session.get(ContentDirection, direction_id)
        if not direction:
            raise HTTPException(status_code=404, detail="内容方向不存在")

        direction.is_active = not direction.is_active
        direction.updated_at = datetime.now(timezone.utc)
        await session.commit()

        status = "启用" if direction.is_active else "停用"
        logger.info(f"内容方向{status}: {direction.name} (ID={direction.id})")
        return {"message": f"已{status}", "is_active": direction.is_active}


@router.post("/run/{direction_id}", summary="手动触发单个方向")
async def run_direction(direction_id: int):
    """手动触发指定方向的一轮自动生成"""
    result = await content_pilot.run_direction(direction_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/run-all", summary="手动触发所有方向")
async def run_all_directions():
    """手动触发所有启用方向的自动生成"""
    results = await content_pilot.run_all_directions()
    return {"results": results}


@router.get("/directions/{direction_id}/topics", summary="查看已生成主题")
async def list_generated_topics(
    direction_id: int,
    page: int = 1,
    page_size: int = 20,
):
    """查看指定方向的已生成主题列表"""
    async with async_session_factory() as session:
        # 总数
        count_stmt = select(func.count(GeneratedTopic.id)).where(
            GeneratedTopic.direction_id == direction_id
        )
        total = (await session.execute(count_stmt)).scalar() or 0

        # 分页查询
        stmt = (
            select(GeneratedTopic)
            .where(GeneratedTopic.direction_id == direction_id)
            .order_by(GeneratedTopic.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await session.execute(stmt)
        topics = result.scalars().all()

        items = [
            {
                "id": t.id,
                "topic": t.topic,
                "article_id": t.article_id,
                "created_at": str(t.created_at) if t.created_at else None,
            }
            for t in topics
        ]

        return {"total": total, "items": items}


@router.post("/directions/{direction_id}/reset-count", summary="重置今日计数")
async def reset_today_count(direction_id: int):
    """重置指定方向的今日已生成计数"""
    async with async_session_factory() as session:
        direction = await session.get(ContentDirection, direction_id)
        if not direction:
            raise HTTPException(status_code=404, detail="内容方向不存在")

        direction.today_generated = 0
        direction.updated_at = datetime.now(timezone.utc)
        await session.commit()

        return {"message": "已重置"}
