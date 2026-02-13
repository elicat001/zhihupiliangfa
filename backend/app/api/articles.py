"""
文章相关 API 路由
包含 AI 生成、CRUD 操作、SSE 流式生成
"""

import csv
import io
import json
import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.connection import get_db
from app.models.article import Article
from app.models.log import SystemLog
from app.schemas.article import (
    ArticleGenerateRequest,
    ArticleCreateRequest,
    ArticleUpdateRequest,
    ArticleResponse,
    ArticleListResponse,
    SeriesOutlineRequest,
    SeriesOutlineResponse,
    SeriesGenerateRequest,
    ArticleRewriteRequest,
)
from app.core.ai_generator import ai_generator
from app.schemas.article import AgentGenerateRequest, StoryGenerateRequest
from app.core.article_agent import article_agent
from app.core.story_agent import story_agent

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/articles", tags=["文章管理"])


@router.post("/generate", response_model=ArticleResponse, summary="AI 生成文章")
async def generate_article(
    request: ArticleGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    使用 AI 生成知乎风格文章

    - **topic**: 文章主题
    - **style**: 写作风格（professional / casual / storytelling / tutorial）
    - **word_count**: 目标字数（300-10000）
    - **ai_provider**: AI 提供商（openai / deepseek / claude）
    """
    try:
        # 调用 AI 生成（根据 enable_images 决定是否配图）
        if request.enable_images:
            generated = await ai_generator.generate_with_images(
                topic=request.topic,
                style=request.style,
                word_count=request.word_count,
                ai_provider=request.ai_provider,
            )
        else:
            generated = await ai_generator.generate(
                topic=request.topic,
                style=request.style,
                word_count=request.word_count,
                ai_provider=request.ai_provider,
            )

        # 保存到数据库
        article = Article(
            title=generated.title,
            content=generated.content,
            summary=generated.summary,
            tags=generated.tags,
            word_count=generated.word_count,
            ai_provider=request.ai_provider,
            status="draft",
            created_at=datetime.now(timezone.utc),
            images=getattr(generated, 'images', None),
        )
        db.add(article)

        # 记录日志
        log = SystemLog(
            event_type="generate",
            level="info",
            message=f"AI 生成文章成功: {generated.title}",
            details={
                "topic": request.topic,
                "style": request.style,
                "word_count": generated.word_count,
                "ai_provider": request.ai_provider,
            },
        )
        db.add(log)

        await db.commit()
        await db.refresh(article)

        logger.info(f"文章生成并保存: id={article.id}, title={article.title}")
        return article

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文章生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"文章生成失败: {str(e)}")


@router.post("/generate-stream", summary="AI 流式生成文章 (SSE)")
async def generate_article_stream(
    request: ArticleGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    使用 AI 流式生成知乎风格文章 (Server-Sent Events)

    返回 SSE 事件流：
    - content: 文章内容的增量 chunk
    - done: 生成完毕，附带完整文章数据（已保存到数据库）
    - error: 生成过程中出现错误
    """

    # Pre-validate provider availability before entering the stream
    # so we can return a proper HTTP error instead of an SSE error
    provider = ai_generator.get_provider(request.ai_provider)
    if not provider:
        available = ai_generator.get_available_providers()
        if not available:
            raise HTTPException(
                status_code=400,
                detail="没有可用的 AI 提供商，请先配置 API Key",
            )
        raise HTTPException(
            status_code=400,
            detail=(
                f"AI 提供商 '{request.ai_provider}' 不可用。"
                f"可用的提供商: {', '.join(available)}"
            ),
        )

    async def event_generator():
        full_text = ""
        try:
            async for chunk in ai_generator.generate_stream(
                topic=request.topic,
                style=request.style,
                word_count=request.word_count,
                ai_provider=request.ai_provider,
            ):
                full_text += chunk
                # 发送内容 chunk
                event_data = json.dumps(
                    {"type": "content", "text": chunk},
                    ensure_ascii=False,
                )
                yield f"data: {event_data}\n\n"

            # 流式完成后检查是否收到了任何内容
            if not full_text.strip():
                event_data = json.dumps(
                    {
                        "type": "error",
                        "message": "AI 未返回任何内容，请稍后重试",
                    },
                    ensure_ascii=False,
                )
                yield f"data: {event_data}\n\n"
                return

            # 流式完成后，解析完整文本并保存到数据库
            try:
                # 使用提供商的 _parse_response 来解析 JSON
                generated = provider._parse_response(full_text)
            except Exception as parse_err:
                logger.error(f"流式生成后解析失败: {parse_err}")
                event_data = json.dumps(
                    {
                        "type": "error",
                        "message": f"文章解析失败: {str(parse_err)}",
                    },
                    ensure_ascii=False,
                )
                yield f"data: {event_data}\n\n"
                return

            # 流式完成后，若启用图片则获取图片
            if request.enable_images and (generated.images or generated.cover_image):
                try:
                    generated = await ai_generator.fetch_images_for_article(generated)
                except Exception as img_err:
                    logger.warning(f"图片获取失败，继续保存纯文本: {img_err}")

            # 保存到数据库
            try:
                article = Article(
                    title=generated.title,
                    content=generated.content,
                    summary=generated.summary,
                    tags=generated.tags,
                    word_count=generated.word_count,
                    ai_provider=request.ai_provider,
                    status="draft",
                    created_at=datetime.now(timezone.utc),
                    images=getattr(generated, 'images', None),
                )
                db.add(article)

                log = SystemLog(
                    event_type="generate",
                    level="info",
                    message=f"AI 流式生成文章成功: {generated.title}",
                    details={
                        "topic": request.topic,
                        "style": request.style,
                        "word_count": generated.word_count,
                        "ai_provider": request.ai_provider,
                    },
                )
                db.add(log)

                await db.commit()
                await db.refresh(article)
            except Exception as db_err:
                logger.error(f"流式生成后保存数据库失败: {db_err}")
                event_data = json.dumps(
                    {
                        "type": "error",
                        "message": f"文章保存失败: {str(db_err)}",
                    },
                    ensure_ascii=False,
                )
                yield f"data: {event_data}\n\n"
                return

            logger.info(
                f"流式文章生成并保存: id={article.id}, title={article.title}"
            )

            # 发送完成事件，附带完整文章数据
            article_data = {
                "id": article.id,
                "title": article.title,
                "content": article.content,
                "summary": article.summary,
                "tags": article.tags,
                "word_count": article.word_count,
                "ai_provider": article.ai_provider,
                "status": article.status,
                "created_at": article.created_at.isoformat(),
            }
            event_data = json.dumps(
                {"type": "done", "article": article_data},
                ensure_ascii=False,
            )
            yield f"data: {event_data}\n\n"

        except ValueError as e:
            logger.error(f"流式生成参数错误: {e}")
            event_data = json.dumps(
                {"type": "error", "message": str(e)},
                ensure_ascii=False,
            )
            yield f"data: {event_data}\n\n"
        except Exception as e:
            logger.error(f"流式生成失败: {e}")
            event_data = json.dumps(
                {"type": "error", "message": f"文章生成失败: {str(e)}"},
                ensure_ascii=False,
            )
            yield f"data: {event_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post(
    "/series-outline",
    response_model=SeriesOutlineResponse,
    summary="生成系列文章大纲",
)
async def generate_series_outline(
    request: SeriesOutlineRequest,
):
    """
    使用 AI 生成系列文章大纲

    - **topic**: 系列主题
    - **count**: 文章数量（2-20）
    - **ai_provider**: AI 提供商
    """
    try:
        outline = await ai_generator.generate_series_outline(
            topic=request.topic,
            count=request.count,
            ai_provider=request.ai_provider,
        )
        return outline
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"系列大纲生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"系列大纲生成失败: {str(e)}")


@router.post(
    "/series-generate",
    response_model=list[ArticleResponse],
    summary="批量生成系列文章",
)
async def generate_series_articles(
    request: SeriesGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    根据系列大纲批量生成所有文章

    - **series_title**: 系列标题
    - **articles**: 文章列表（每篇含 title, description, key_points）
    - **style**: 写作风格
    - **word_count**: 每篇目标字数
    - **ai_provider**: AI 提供商
    """
    try:
        series_id = str(uuid.uuid4())
        series_context = f"系列「{request.series_title}」，共 {len(request.articles)} 篇"
        saved_articles = []

        for idx, article_input in enumerate(request.articles):
            # 生成单篇文章
            generated = await ai_generator.generate_series_article(
                title=article_input.title,
                description=article_input.description,
                key_points=article_input.key_points,
                series_context=series_context,
                style=request.style,
                word_count=request.word_count,
                ai_provider=request.ai_provider,
            )

            # 保存到数据库
            article = Article(
                title=generated.title,
                content=generated.content,
                summary=generated.summary,
                tags=generated.tags,
                word_count=generated.word_count,
                ai_provider=request.ai_provider,
                status="draft",
                created_at=datetime.now(timezone.utc),
                series_id=series_id,
                series_order=idx + 1,
                series_title=request.series_title,
            )
            db.add(article)

            # 记录日志
            log = SystemLog(
                event_type="generate",
                level="info",
                message=f"系列文章生成成功: {generated.title} (系列: {request.series_title})",
                details={
                    "series_id": series_id,
                    "series_title": request.series_title,
                    "series_order": idx + 1,
                    "word_count": generated.word_count,
                    "ai_provider": request.ai_provider,
                },
            )
            db.add(log)

            await db.commit()
            await db.refresh(article)
            saved_articles.append(article)

            logger.info(
                f"系列文章 [{idx + 1}/{len(request.articles)}] 生成并保存: "
                f"id={article.id}, title={article.title}"
            )

        return saved_articles

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"系列文章生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"系列文章生成失败: {str(e)}")


@router.post("/rewrite", response_model=ArticleResponse, summary="改写文章")
async def rewrite_article(
    request: ArticleRewriteRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    改写指定文章，生成新的文章

    - **article_id**: 原文章 ID
    - **style**: 改写风格
    - **instruction**: 额外改写指令（可选）
    """
    # 获取原文章
    original = await db.get(Article, request.article_id)
    if not original:
        raise HTTPException(status_code=404, detail="原文章不存在")

    # 确定使用的 AI 提供商（优先用原文章的提供商，若不可用则用默认）
    ai_provider = original.ai_provider or ""
    non_ai_sources = ("manual", "rewrite", "import", "agent-generated", "")
    if ai_provider in non_ai_sources or not ai_generator.get_provider(ai_provider):
        available = ai_generator.get_available_providers()
        if not available:
            raise HTTPException(status_code=400, detail="没有可用的 AI 提供商")
        ai_provider = available[0]

    try:
        generated = await ai_generator.rewrite_article(
            content=original.content,
            style=request.style,
            instruction=request.instruction or "",
            ai_provider=ai_provider,
        )

        # 保存为新文章
        article = Article(
            title=generated.title,
            content=generated.content,
            summary=generated.summary,
            tags=generated.tags,
            word_count=generated.word_count,
            ai_provider="rewrite",
            status="draft",
            created_at=datetime.now(timezone.utc),
        )
        db.add(article)

        # 记录日志
        log = SystemLog(
            event_type="rewrite",
            level="info",
            message=f"文章改写成功: {generated.title} (原文: {original.title})",
            details={
                "original_id": request.article_id,
                "style": request.style,
                "instruction": request.instruction,
                "ai_provider": ai_provider,
            },
        )
        db.add(log)

        await db.commit()
        await db.refresh(article)

        logger.info(
            f"文章改写并保存: id={article.id}, title={article.title}, "
            f"original_id={request.article_id}"
        )
        return article

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"文章改写失败: {e}")
        raise HTTPException(status_code=500, detail=f"文章改写失败: {str(e)}")


@router.post("/agent-generate", response_model=list[ArticleResponse], summary="智能体批量生成文章")
async def agent_generate_articles(
    request: AgentGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    智能文章生成 Agent

    基于参考文章自动分析、规划并批量生成相关文章：
    1. 分析参考文章的主题、风格、关键词
    2. 规划差异化角度的新文章大纲
    3. 逐篇生成完整文章并保存

    - **article_ids**: 参考文章 ID 列表（1-10篇）
    - **count**: 要生成的文章数量（1-20）
    - **style**: 写作风格（为空则由 AI 自动推荐）
    - **word_count**: 每篇目标字数
    - **ai_provider**: AI 提供商
    """
    # 获取参考文章
    reference_articles = []
    for article_id in request.article_ids:
        article = await db.get(Article, article_id)
        if not article:
            raise HTTPException(
                status_code=404,
                detail=f"参考文章 ID={article_id} 不存在",
            )
        reference_articles.append({
            "title": article.title,
            "content": article.content,
        })

    try:
        # 运行 Agent 完整流程
        result = await article_agent.run(
            articles=reference_articles,
            count=request.count,
            style=request.style,
            word_count=request.word_count,
            ai_provider=request.ai_provider,
        )

        # 保存生成的文章到数据库
        saved_articles = []
        for article_data in result["articles"]:
            if article_data.get("error"):
                continue

            article = Article(
                title=article_data["title"],
                content=article_data["content"],
                summary=article_data["summary"],
                tags=article_data["tags"],
                word_count=article_data["word_count"],
                ai_provider=request.ai_provider,
                status="draft",
                created_at=datetime.now(timezone.utc),
                category="agent-generated",
                series_id=article_data.get("series_id"),
                series_order=article_data.get("series_order"),
                series_title=article_data.get("series_title"),
            )
            db.add(article)

            log = SystemLog(
                event_type="agent_generate",
                level="info",
                message=f"智能体生成文章: {article_data['title']}",
                details={
                    "reference_ids": request.article_ids,
                    "series_title": article_data.get("series_title"),
                    "series_order": article_data.get("series_order"),
                    "word_count": article_data["word_count"],
                    "ai_provider": request.ai_provider,
                },
            )
            db.add(log)

            await db.commit()
            await db.refresh(article)
            saved_articles.append(article)

            logger.info(
                f"智能体文章保存: id={article.id}, title={article.title}"
            )

        return saved_articles

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"智能体生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"智能体生成失败: {str(e)}")


@router.post(
    "/story-generate",
    response_model=list[ArticleResponse],
    summary="故事生成",
)
async def story_generate(
    request: StoryGenerateRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    故事生成 Agent

    基于参考素材自动生成知乎盐选风格故事：
    1. 素材提取 — 分析参考素材的人物、冲突、时代背景
    2. 故事规划 — 设计故事弧线、人物卡片、章节大纲
    3. 分章草稿 — 逐章生成 2000-3000 字内容
    4. 组装润色 — 合并章节、添加过渡和伏笔回收
    5. 去AI味 — 替换模板表达、添加自然语感
    """
    # 获取可选的参考文章
    reference_articles = []
    if request.reference_article_ids:
        for article_id in request.reference_article_ids:
            article = await db.get(Article, article_id)
            if article:
                reference_articles.append({
                    "title": article.title,
                    "content": article.content,
                })

    try:
        result = await story_agent.run(
            reference_text=request.reference_text,
            reference_articles=reference_articles,
            chapter_count=request.chapter_count,
            total_word_count=request.total_word_count,
            story_type=request.story_type,
            ai_provider=request.ai_provider,
        )

        final = result["final_story"]
        story_content = final.get("full_story", "")
        word_count = len(story_content.replace(" ", "").replace("\n", ""))
        series_id = str(uuid.uuid4())
        saved_articles = []

        # 保存完整故事
        article = Article(
            title=final.get("title", "AI生成故事"),
            content=story_content,
            summary=final.get("summary", ""),
            tags=final.get("tags", []),
            word_count=word_count,
            ai_provider=request.ai_provider,
            status="draft",
            created_at=datetime.now(timezone.utc),
            category="story-generated",
            series_id=series_id,
            series_title=final.get("title", ""),
        )
        db.add(article)

        log = SystemLog(
            event_type="story_generate",
            level="info",
            message=f"故事生成成功: {final.get('title', '未知')}",
            details={
                "story_type": request.story_type,
                "chapter_count": request.chapter_count,
                "total_word_count": word_count,
                "ai_provider": request.ai_provider,
            },
        )
        db.add(log)

        await db.commit()
        await db.refresh(article)
        saved_articles.append(article)

        # 保存各章节为独立文章
        chapters = result.get("chapters", [])
        for ch in chapters:
            if ch.get("error"):
                continue
            ch_article = Article(
                title=f"{final.get('title', '故事')} - 第{ch['chapter_num']}章: {ch.get('title', '')}",
                content=ch.get("content", ""),
                summary=ch.get("summary", "")[:200],
                tags=final.get("tags", []),
                word_count=ch.get("word_count", 0),
                ai_provider=request.ai_provider,
                status="draft",
                created_at=datetime.now(timezone.utc),
                category="story-chapter",
                series_id=series_id,
                series_order=ch["chapter_num"],
                series_title=final.get("title", ""),
            )
            db.add(ch_article)
            await db.commit()
            await db.refresh(ch_article)
            saved_articles.append(ch_article)

        logger.info(
            f"故事生成完成：标题={final.get('title')}, "
            f"总字数={word_count}, 章节数={len(chapters)}"
        )
        return saved_articles

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"故事生成失败: {e}")
        raise HTTPException(status_code=500, detail=f"故事生成失败: {str(e)}")


@router.post("/batch-delete", summary="批量删除文章")
async def batch_delete_articles(
    data: dict,
    db: AsyncSession = Depends(get_db),
):
    """批量删除文章"""
    ids = data.get("ids", [])
    if not ids:
        raise HTTPException(status_code=400, detail="请提供要删除的文章 ID 列表")

    deleted = 0
    for article_id in ids:
        article = await db.get(Article, article_id)
        if article:
            await db.delete(article)
            deleted += 1

    await db.commit()
    logger.info(f"批量删除文章: {deleted}/{len(ids)} 篇")
    return {"message": f"已删除 {deleted} 篇文章", "deleted": deleted}


@router.get("", response_model=ArticleListResponse, summary="获取文章列表")
async def list_articles(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: str = Query(None, description="状态过滤：draft / published"),
    category: str = Query(None, description="分类过滤"),
    keyword: str = Query(None, description="关键词搜索（标题/内容模糊匹配）"),
    db: AsyncSession = Depends(get_db),
):
    """获取文章列表，支持分页、状态、分类过滤和关键词搜索"""
    # 构建查询
    stmt = select(Article).order_by(Article.created_at.desc())
    count_stmt = select(func.count(Article.id))

    if status:
        stmt = stmt.where(Article.status == status)
        count_stmt = count_stmt.where(Article.status == status)

    if category:
        stmt = stmt.where(Article.category == category)
        count_stmt = count_stmt.where(Article.category == category)

    if keyword:
        keyword_filter = Article.title.ilike(f"%{keyword}%")
        stmt = stmt.where(keyword_filter)
        count_stmt = count_stmt.where(keyword_filter)

    # 总数
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 分页
    offset = (page - 1) * page_size
    stmt = stmt.offset(offset).limit(page_size)
    result = await db.execute(stmt)
    articles = result.scalars().all()

    return ArticleListResponse(total=total, items=articles)


@router.post("/import", summary="导入文章")
async def import_article(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """从文件导入文章，支持 .md 和 .txt 格式"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="文件名不能为空")

    ext = file.filename.rsplit('.', 1)[-1].lower()
    if ext not in ('md', 'txt', 'markdown'):
        raise HTTPException(status_code=400, detail="仅支持 .md / .txt 格式")

    content = (await file.read()).decode('utf-8')

    # Extract title from first heading or first line
    title = "导入的文章"
    lines = content.strip().split('\n')
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#'):
            title = stripped.lstrip('#').strip()
            break
        elif stripped:
            title = stripped[:50]
            break

    word_count = len(content.replace(' ', '').replace('\n', ''))

    article = Article(
        title=title,
        content=content,
        summary=content[:100].replace('\n', ' '),
        tags=[],
        word_count=word_count,
        ai_provider="import",
        status="draft",
        created_at=datetime.now(timezone.utc),
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    logger.info(f"导入文章: id={article.id}, title={article.title}, file={file.filename}")
    return article


@router.get("/export", summary="导出文章")
async def export_articles(
    format: str = Query("csv", description="导出格式：csv"),
    db: AsyncSession = Depends(get_db),
):
    """导出所有文章为 CSV 文件"""
    if format != "csv":
        raise HTTPException(status_code=400, detail="目前仅支持 CSV 格式导出")

    stmt = select(Article).order_by(Article.created_at.desc())
    result = await db.execute(stmt)
    articles = result.scalars().all()

    output = io.StringIO()
    writer = csv.writer(output)
    # 写入表头
    writer.writerow([
        "ID", "标题", "摘要", "分类", "标签", "字数",
        "来源", "状态", "创建时间",
    ])
    # 写入数据
    for a in articles:
        tags_str = ", ".join(a.tags) if a.tags else ""
        writer.writerow([
            a.id,
            a.title,
            (a.summary or "")[:100],
            a.category or "",
            tags_str,
            a.word_count,
            a.ai_provider,
            a.status,
            a.created_at.isoformat() if a.created_at else "",
        ])

    csv_content = output.getvalue()
    output.close()

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=articles_export.csv",
        },
    )


@router.get("/{article_id}", response_model=ArticleResponse, summary="获取文章详情")
async def get_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    """根据 ID 获取文章详情"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")
    return article


@router.post("", response_model=ArticleResponse, summary="手动创建文章")
async def create_article(
    request: ArticleCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """手动创建文章（不通过 AI 生成）"""
    word_count = len(request.content.replace(" ", "").replace("\n", ""))

    article = Article(
        title=request.title,
        content=request.content,
        summary=request.summary or "",
        tags=request.tags or [],
        word_count=word_count,
        ai_provider=request.ai_provider or "manual",
        status="draft",
        created_at=datetime.now(timezone.utc),
        category=request.category,
    )
    db.add(article)
    await db.commit()
    await db.refresh(article)

    logger.info(f"手动创建文章: id={article.id}, title={article.title}")
    return article


@router.put("/{article_id}", response_model=ArticleResponse, summary="更新文章")
async def update_article(
    article_id: int,
    request: ArticleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """更新文章信息"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    # 更新非空字段
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(article, field, value)

    # 重新计算字数
    if request.content:
        article.word_count = len(
            request.content.replace(" ", "").replace("\n", "")
        )

    await db.commit()
    await db.refresh(article)

    logger.info(f"更新文章: id={article.id}")
    return article


@router.delete("/{article_id}", summary="删除文章")
async def delete_article(
    article_id: int,
    db: AsyncSession = Depends(get_db),
):
    """删除文章"""
    article = await db.get(Article, article_id)
    if not article:
        raise HTTPException(status_code=404, detail="文章不存在")

    await db.delete(article)
    await db.commit()

    logger.info(f"删除文章: id={article_id}")
    return {"message": "文章已删除", "id": article_id}
