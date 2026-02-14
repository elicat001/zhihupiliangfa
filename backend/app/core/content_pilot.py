"""
ContentPilot 自动驾驶引擎
全自动：选题 → 去重 → 生成 → 入库 → 发布队列

核心流程：
1. 定时扫描所有启用的内容方向
2. 为每个方向 AI 自动选题（含去重检查）
3. 调用 AI 生成文章（带反AI检测 prompt）
4. 生成的文章自动入库
5. 如开启自动发布，自动加入发布调度队列
"""

import hashlib
import json
import logging
import random
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, func

from app.config import settings
from app.database.connection import async_session_factory
from app.models.article import Article
from app.models.account import Account
from app.models.pilot import ContentDirection, GeneratedTopic
from app.core.ai_generator import ai_generator
from app.api.events import event_bus

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


def _topic_hash(text: str) -> str:
    """生成主题的简化哈希，用于去重"""
    # 去掉标点、空格，转小写后取 sha256
    cleaned = re.sub(r'[^\w]', '', text.lower())
    return hashlib.sha256(cleaned.encode('utf-8')).hexdigest()[:32]


# ==================== 反AI检测增强 prompt ====================

ANTI_AI_SYSTEM_ADDON = """

## 反AI检测写作规范（极其重要！违反会被平台处罚）

### 绝对禁止的表达
禁用词列表：然而、不禁、竟然(最多1次)、值得一提的是、毫无疑问、与此同时、
如同……一般、在这个……的时代、随着……的发展、不难发现、总而言之、综上所述、
由此可见、不言而喻、众所周知、显而易见、事实上

### 必须使用的真人写作特征
1. 口语化过渡词：说白了、简单来说、换句话说、你想啊、坦白讲、说实话
2. 个人化表达：我个人觉得、据我了解、我之前遇到过、有个朋友跟我说
3. 不确定表达：可能、大概、或许、我也不太确定、好像是
4. 跑题与拉回：扯远了说回正题、这里多说一句、顺带提一下
5. 段落长度随机：有的段2-3句，有的段7-8句，绝不能每段都一样长
6. 句式变化：长短句交替、偶尔用感叹句反问句、偶尔用省略号表示停顿
7. 具体细节：用"去年年底"而非"近期"、用"大概70%左右"而非"72.3%"
8. 每篇至少2个看似亲身经历的案例
9. 偶尔自嘲或承认局限："这一点我可能理解有偏差""不一定对，仅供参考"
10. 使用行业黑话和圈内梗
"""

ANTI_AI_USER_ADDON = """
反AI检测要求（必须遵守）：
- 绝对不能用"然而""不禁""值得一提的是""毫无疑问"等AI套话
- 必须像一个真实的知乎大V写作，有个人风格和口语化表达
- 穿插2-3个具体案例或"个人经历"
- 段落长短不一，句式要有变化
- 允许有不完美和不确定的表达
"""


class ContentPilot:
    """内容自动驾驶引擎"""

    def __init__(self):
        self.ai_generator = ai_generator
        self._running = False

    async def generate_topics(
        self,
        direction: ContentDirection,
        count: int = 5,
    ) -> list[str]:
        """
        为指定方向 AI 自动选题

        Args:
            direction: 内容方向配置
            count: 需要生成的主题数量

        Returns:
            去重后的主题列表
        """
        ai_provider = direction.ai_provider or None
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        keywords = direction.keywords or []
        keywords_text = "、".join(keywords) if keywords else direction.name

        # 获取已有主题用于去重提示
        async with async_session_factory() as session:
            stmt = (
                select(GeneratedTopic.topic)
                .where(GeneratedTopic.direction_id == direction.id)
                .order_by(GeneratedTopic.created_at.desc())
                .limit(50)
            )
            result = await session.execute(stmt)
            existing_topics = [r[0] for r in result.fetchall()]

        existing_text = ""
        if existing_topics:
            existing_text = f"""

以下是已经写过的主题，你必须避免与这些主题重复或过于相似：
{chr(10).join(f'- {t}' for t in existing_topics[:30])}
"""

        system_prompt = """你是一位知乎内容策划专家，擅长发掘热门话题和读者感兴趣的选题角度。
你需要为指定的内容方向生成新鲜、有吸引力的文章主题。
你必须严格按照 JSON 格式返回，不要返回任何其他内容。"""

        user_prompt = f"""请为以下内容方向生成 {count * 2} 个文章主题（多生成一些，供筛选去重）：

内容方向：{direction.name}
描述：{direction.description or '无'}
核心关键词：{keywords_text}
{existing_text}

选题要求：
1. 每个主题必须有独特角度，不能和已有主题重复
2. 标题要符合知乎爆款特征：疑问式、数字式、颠覆认知式、经历分享式
3. 标题长度 15-25 字，包含核心关键词
4. 选题要有话题性和争议性，能引发讨论
5. 覆盖不同的子方向和切入角度

请严格按照以下 JSON 格式返回：
{{
    "topics": [
        "主题1标题",
        "主题2标题",
        ...
    ]
}}"""

        try:
            text = await provider.chat(system_prompt, user_prompt)
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            data = json.loads(text, strict=False)
            raw_topics = data.get("topics", [])
        except Exception as e:
            logger.error(f"AI 选题失败 (方向: {direction.name}): {e}")
            return []

        # 去重：检查与已有主题的哈希是否重复
        async with async_session_factory() as session:
            stmt = select(GeneratedTopic.title_hash).where(
                GeneratedTopic.direction_id == direction.id
            )
            result = await session.execute(stmt)
            existing_hashes = {r[0] for r in result.fetchall()}

        deduped = []
        for topic in raw_topics:
            h = _topic_hash(topic)
            if h not in existing_hashes:
                deduped.append(topic)
                existing_hashes.add(h)  # 同批次内也去重
            if len(deduped) >= count:
                break

        logger.info(
            f"选题完成 (方向: {direction.name}): "
            f"AI生成={len(raw_topics)}, 去重后={len(deduped)}"
        )
        return deduped

    async def generate_single_article(
        self,
        direction: ContentDirection,
        topic: str,
    ) -> Optional[dict]:
        """
        为指定主题生成单篇文章（带反AI检测增强）

        Returns:
            文章数据 dict 或 None（失败时）
        """
        ai_provider = direction.ai_provider or None
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        style_map = {
            "professional": "专业严谨，数据驱动，引用行业报告和研究",
            "casual": "轻松活泼，通俗易懂，用生活化的比喻和例子",
            "humorous": "幽默风趣，善用段子和反转，在笑点中传递知识",
            "academic": "学术严谨，逻辑缜密，引经据典，论证充分",
            "storytelling": "叙事型，通过真实故事和案例展开，情感共鸣",
            "tutorial": "教程型，步骤清晰，有代码示例或操作指南",
            "controversial": "观点碰撞型，提出大胆的反主流观点，引发讨论",
        }
        style_desc = style_map.get(direction.style, style_map["professional"])

        # 根据反AI等级构建增强 prompt
        anti_ai_addon = ""
        anti_ai_user = ""
        if direction.anti_ai_level >= 2:
            anti_ai_addon = ANTI_AI_SYSTEM_ADDON
            anti_ai_user = ANTI_AI_USER_ADDON
        elif direction.anti_ai_level == 1:
            anti_ai_addon = "\n\n## 写作自然度要求\n- 避免使用AI常见套话如'然而''不禁''值得一提的是'\n- 适当使用口语化表达\n- 段落长度要有变化\n"
            anti_ai_user = "\n注意：避免AI常见套话，文风要自然。\n"

        system_prompt = f"""你是一位拥有10万+粉丝的知乎头部创作者，文章多次登上知乎热榜。

## 写作思维
- 先构建骨架：核心论点 → 3-5个分论点 → 每个分论点的论据
- 在关键位置提出反直觉的观点，引发思考
- 确保每个观点有数据、案例或逻辑推理支撑

## 知乎排版规范
- 使用 ## 二级标题分段
- 重要观点用 **加粗** 标注
- 适当使用 > 引用块突出金句或数据
- 使用有序/无序列表归纳要点
- 段与段之间用 --- 分割线过渡
- 偶尔使用「」代替""增加平台感
{anti_ai_addon}
## 输出格式
你必须严格按照以下 JSON 格式返回，不要返回任何其他内容：
{{
    "title": "文章标题（15-25字，含核心关键词）",
    "content": "文章正文内容（Markdown 格式）",
    "summary": "100字以内的文章摘要",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}}"""

        user_prompt = f"""请以「{topic}」为主题，写一篇知乎专栏文章。

要求：
- 写作风格：{style_desc}
- 目标字数：约 {direction.word_count} 字
- 标题要吸引眼球，含核心关键词
- 内容要有深度、有独到见解
- 使用 Markdown 格式排版
- 选择 5 个知乎热门相关话题标签
- 文末加一个引导评论的互动问题
{anti_ai_user}
请严格按照 JSON 格式返回。"""

        try:
            text = await provider.chat(system_prompt, user_prompt)
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            # 提取 JSON
            try:
                data = json.loads(text, strict=False)
            except json.JSONDecodeError:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    data = json.loads(text[start:end], strict=False)
                else:
                    raise

            content = data.get("content", "")
            # 清理可能残留的图片占位符
            content = re.sub(r'\[IMG\d+\]', '', content)

            return {
                "title": data.get("title", topic),
                "content": content,
                "summary": data.get("summary", ""),
                "tags": data.get("tags", []),
                "word_count": len(content.replace(" ", "").replace("\n", "")),
                "ai_provider": ai_provider,
            }
        except Exception as e:
            logger.error(f"文章生成失败 (主题: {topic}): {e}")
            return None

    async def run_direction(self, direction_id: int) -> dict:
        """
        为指定方向执行一轮自动生成

        Returns:
            执行结果统计
        """
        async with async_session_factory() as session:
            direction = await session.get(ContentDirection, direction_id)
            if not direction:
                return {"error": "方向不存在"}
            if not direction.is_active:
                return {"error": "方向未启用"}

            # 检查运行周期
            today_str = datetime.now().strftime("%Y-%m-%d")
            if direction.schedule_start and today_str < direction.schedule_start:
                return {
                    "direction": direction.name,
                    "message": f"未到开始日期 {direction.schedule_start}",
                    "generated": 0,
                }
            if direction.schedule_end and today_str > direction.schedule_end:
                # 超过结束日期，自动停用
                direction.is_active = False
                direction.updated_at = _utcnow()
                await session.commit()
                logger.info(
                    f"ContentPilot: 方向 '{direction.name}' 已超过结束日期 "
                    f"{direction.schedule_end}，自动停用"
                )
                return {
                    "direction": direction.name,
                    "message": f"已超过结束日期 {direction.schedule_end}，已自动停用",
                    "generated": 0,
                }

            # 检查是否需要重置今日计数
            if direction.last_reset_date != today_str:
                direction.today_generated = 0
                direction.last_reset_date = today_str
                await session.commit()

            remaining = direction.daily_count - direction.today_generated
            if remaining <= 0:
                return {
                    "direction": direction.name,
                    "message": "今日生成数量已达上限",
                    "generated": 0,
                }

        # 本轮最多生成的数量（分批，每轮最多6篇，避免一次生成太多）
        batch_size = min(remaining, 6)

        logger.info(
            f"ContentPilot 开始生成 (方向: {direction.name}, "
            f"本轮目标: {batch_size}, 今日剩余: {remaining})"
        )

        # 1. AI 自动选题
        topics = await self.generate_topics(direction, count=batch_size)
        if not topics:
            return {
                "direction": direction.name,
                "message": "选题失败，无可用主题",
                "generated": 0,
            }

        # 2. 逐篇生成
        generated_count = 0
        generated_articles = []

        for topic in topics:
            article_data = await self.generate_single_article(direction, topic)
            if not article_data:
                continue

            # 3. 保存到数据库
            async with async_session_factory() as session:
                article = Article(
                    title=article_data["title"],
                    content=article_data["content"],
                    summary=article_data["summary"],
                    tags=article_data["tags"],
                    word_count=article_data["word_count"],
                    ai_provider=article_data["ai_provider"],
                    status="draft",
                    category=direction.name,
                )
                session.add(article)
                await session.commit()
                await session.refresh(article)

                # 记录已生成主题（去重表）
                gen_topic = GeneratedTopic(
                    direction_id=direction.id,
                    topic=topic,
                    title_hash=_topic_hash(topic),
                    article_id=article.id,
                )
                session.add(gen_topic)

                # 更新今日已生成计数
                dir_obj = await session.get(ContentDirection, direction.id)
                if dir_obj:
                    dir_obj.today_generated += 1
                    dir_obj.updated_at = _utcnow()

                await session.commit()

                generated_count += 1
                generated_articles.append({
                    "id": article.id,
                    "title": article.title,
                })

                logger.info(
                    f"ContentPilot 生成成功: [{generated_count}/{batch_size}] "
                    f"{article.title} (ID={article.id})"
                )

        # 4. 自动发布（如果启用）
        published_count = 0
        if direction.auto_publish and generated_articles:
            published_count = await self._auto_queue_articles(
                direction, [a["id"] for a in generated_articles]
            )

        result = {
            "direction": direction.name,
            "topics_generated": len(topics),
            "articles_generated": generated_count,
            "articles_published": published_count,
            "articles": generated_articles,
        }

        # 发布事件通知
        await event_bus.publish("pilot_batch_done", result)

        logger.info(
            f"ContentPilot 本轮完成 (方向: {direction.name}): "
            f"生成={generated_count}, 入队发布={published_count}"
        )
        return result

    async def _auto_queue_articles(
        self, direction: ContentDirection, article_ids: list[int]
    ) -> int:
        """将文章自动加入发布队列"""
        from app.core.task_scheduler import task_scheduler

        # 确定发布账号
        account_id = direction.publish_account_id
        if not account_id:
            # 自动选择第一个已登录的活跃账号
            async with async_session_factory() as session:
                stmt = (
                    select(Account.id)
                    .where(
                        Account.is_active == True,  # noqa: E712
                        Account.login_status == "logged_in",
                    )
                    .limit(1)
                )
                result = await session.execute(stmt)
                row = result.first()
                if row:
                    account_id = row[0]

        if not account_id:
            logger.warning(
                f"ContentPilot: 无可用发布账号，跳过自动发布 "
                f"(方向: {direction.name})"
            )
            return 0

        try:
            interval = direction.publish_interval or 30
            tasks = await task_scheduler.add_batch_tasks(
                article_ids=article_ids,
                account_id=account_id,
                interval_minutes=interval,
            )
            logger.info(
                f"ContentPilot: 已加入发布队列 {len(tasks)} 篇 "
                f"(方向: {direction.name}, 账号ID={account_id}, "
                f"间隔={interval}分钟)"
            )
            return len(tasks)
        except Exception as e:
            logger.error(
                f"ContentPilot: 自动发布入队失败 "
                f"(方向: {direction.name}): {e}"
            )
            return 0

    async def run_all_directions(self) -> list[dict]:
        """
        执行所有启用方向的自动生成（由调度器定时调用）
        """
        async with async_session_factory() as session:
            stmt = select(ContentDirection).where(
                ContentDirection.is_active == True  # noqa: E712
            )
            result = await session.execute(stmt)
            directions = result.scalars().all()

        if not directions:
            logger.debug("ContentPilot: 无启用的内容方向，跳过")
            return []

        results = []
        for direction in directions:
            try:
                result = await self.run_direction(direction.id)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"ContentPilot: 方向 '{direction.name}' 执行失败: {e}"
                )
                results.append({
                    "direction": direction.name,
                    "error": str(e),
                })

        return results


# 全局单例
content_pilot = ContentPilot()
