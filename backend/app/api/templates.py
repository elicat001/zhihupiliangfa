"""
内容模板相关 API 路由
包含模板的 CRUD 操作
"""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.template import PromptTemplate
from app.schemas.template import (
    TemplateCreateRequest,
    TemplateUpdateRequest,
    TemplateResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/templates", tags=["内容模板"])


@router.get("", response_model=list[TemplateResponse], summary="获取模板列表")
async def list_templates(
    db: AsyncSession = Depends(get_db),
):
    """获取所有 Prompt 模板，按创建时间倒序"""
    stmt = select(PromptTemplate).order_by(PromptTemplate.created_at.desc())
    result = await db.execute(stmt)
    templates = result.scalars().all()
    return templates


@router.post("", response_model=TemplateResponse, summary="创建模板")
async def create_template(
    request: TemplateCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """创建新的 Prompt 模板"""
    template = PromptTemplate(
        name=request.name,
        description=request.description,
        system_prompt=request.system_prompt,
        user_prompt_template=request.user_prompt_template,
        default_style=request.default_style,
        default_word_count=request.default_word_count,
        is_builtin=False,
    )
    db.add(template)
    await db.commit()
    await db.refresh(template)

    logger.info(f"创建模板: id={template.id}, name={template.name}")
    return template


@router.put("/{template_id}", response_model=TemplateResponse, summary="更新模板")
async def update_template(
    template_id: int,
    request: TemplateUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新模板信息"""
    template = await db.get(PromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    # 更新非空字段
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(template, field, value)

    await db.commit()
    await db.refresh(template)

    logger.info(f"更新模板: id={template.id}")
    return template


@router.delete("/{template_id}", summary="删除模板")
async def delete_template(
    template_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除模板（内置模板不可删除）"""
    template = await db.get(PromptTemplate, template_id)
    if not template:
        raise HTTPException(status_code=404, detail="模板不存在")

    if template.is_builtin:
        raise HTTPException(status_code=400, detail="内置模板不可删除")

    await db.delete(template)
    await db.commit()

    logger.info(f"删除模板: id={template_id}")
    return {"message": "模板已删除", "id": template_id}
