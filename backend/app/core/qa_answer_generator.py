"""
知乎问答回答生成器
使用 AI 为知乎问题生成高质量回答
与文章生成不同：回答更口语化、更直接、更个人化
"""

import json
import logging
import re
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select

from app.core.ai_generator import ai_generator
from app.database.connection import async_session_factory
from app.models.qa import ZhihuQuestion, ZhihuAnswer

logger = logging.getLogger(__name__)


def _utcnow():
    return datetime.now(timezone.utc)


# ==================== 回答专用 Anti-AI Prompt ====================

ANSWER_ANTI_AI_SYSTEM = """
## 反AI检测写作规范（极重要）

### 绝对禁用
禁用词：然而、不禁、竟然、值得一提的是、毫无疑问、与此同时、综上所述、
由此可见、不言而喻、众所周知、显而易见、事实上、总而言之

### 必须使用的真人回答特征
1. 开头不要用"关于这个问题"之类的AI套话，直接切入主题
2. 口语化：说白了、简单来说、换句话说、坦白讲、说实话
3. 个人化：我个人觉得、据我了解、我之前遇到过、有个朋友跟我说
4. 不确定表达：可能、大概、或许、我也不太确定、好像是
5. 跑题与拉回：扯远了说回正题、顺带提一下
6. 段落长短不一：有的2-3句，有的6-8句
7. 具体细节：用"去年年底"而非"近期"
8. 至少1-2个看似亲身经历的案例
9. 自嘲或承认局限："这一点我可能理解有偏差""不一定对仅供参考"
10. 行业黑话和圈内梗
"""

ANSWER_ANTI_AI_USER = """
反AI检测要求：
- 像一个真实知乎用户在回答问题，有个人风格
- 绝对不能用AI套话开头
- 穿插1-2个具体案例或"个人经历"
- 段落长短不一，句式有变化
"""

ANSWER_ANTI_AI_LIGHT = """
## 自然度要求
- 避免AI常见套话如'然而''不禁''值得一提的是'
- 适当使用口语化表达
- 段落长度要有变化
"""


class QAAnswerGenerator:
    """知乎问答回答生成器"""

    def __init__(self):
        self.ai_generator = ai_generator

    async def generate_answer(
        self,
        question_id: int,
        account_id: int,
        style: str = "professional",
        word_count: int = 1000,
        ai_provider: Optional[str] = None,
        anti_ai_level: int = 3,
    ) -> Optional[dict]:
        """
        为指定问题生成AI回答

        Args:
            question_id: 问题表ID（非知乎问题ID）
            account_id: 回答账号ID
            style: 回答风格
            word_count: 目标字数
            ai_provider: AI提供商
            anti_ai_level: 反AI等级 0-3

        Returns:
            dict with answer data or None
        """
        # 获取问题信息
        async with async_session_factory() as session:
            question = await session.get(ZhihuQuestion, question_id)
            if not question:
                logger.error(f"问题不存在: ID={question_id}")
                return None

        logger.info(
            f"开始生成回答: 问题='{question.title[:50]}...' "
            f"风格={style}, 字数={word_count}"
        )

        # 解析AI提供商
        resolved_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(resolved_provider)

        # 构建 prompt
        system_prompt = self._build_system_prompt(style, anti_ai_level)
        user_prompt = self._build_user_prompt(question, style, word_count, anti_ai_level)

        try:
            text = await provider.chat(system_prompt, user_prompt)
            text = text.strip()

            # 解析JSON
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                data = json.loads(text, strict=False)
            except json.JSONDecodeError:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    data = json.loads(text[start:end], strict=False)
                else:
                    # 如果不是JSON，直接把整个文本作为回答内容
                    data = {"content": text}

            content = data.get("content", text)
            # 清理可能的占位符
            content = re.sub(r'\[IMG\d+\]', '', content)

            actual_word_count = len(content.replace(" ", "").replace("\n", ""))

            # 保存到数据库
            async with async_session_factory() as session:
                answer = ZhihuAnswer(
                    question_id=question.id,
                    zhihu_question_id=question.question_id,
                    account_id=account_id,
                    content=content,
                    word_count=actual_word_count,
                    ai_provider=resolved_provider,
                    style=style,
                    anti_ai_level=anti_ai_level,
                    status="draft",
                )
                session.add(answer)

                # 更新问题状态
                q = await session.get(ZhihuQuestion, question.id)
                if q and q.status == "pending":
                    q.status = "answered"

                await session.commit()
                await session.refresh(answer)

                result = {
                    "id": answer.id,
                    "question_id": question.id,
                    "question_title": question.title,
                    "content": content,
                    "word_count": actual_word_count,
                    "ai_provider": resolved_provider,
                    "style": style,
                }
                logger.info(
                    f"回答生成成功: answer_id={answer.id}, "
                    f"字数={actual_word_count}"
                )
                return result

        except Exception as e:
            logger.error(f"回答生成失败 (问题: {question.title[:30]}): {e}")
            return None

    def _build_system_prompt(self, style: str, anti_ai_level: int) -> str:
        """构建系统提示词"""
        style_map = {
            "professional": "你是一位专业领域的资深从业者，回答严谨、有数据支撑、引用行业案例",
            "casual": "你是一位经验丰富的知乎老用户，回答轻松幽默、通俗易懂、贴近生活",
            "personal": "你是一位喜欢分享个人经历的知乎用户，回答注重真实体验和感悟",
            "detailed": "你是一位擅长深度分析的知乎答主，回答结构清晰、论证充分、干货满满",
            "concise": "你是一位言简意赅的知乎答主，直切要害、不废话、观点明确",
            "storytelling": "你是一位善于讲故事的知乎答主，用故事和案例让回答引人入胜",
            "controversial": "你是一位有独到见解的知乎答主，敢于提出不同观点、引发思考",
        }
        style_desc = style_map.get(style, style_map["professional"])

        anti_ai_addon = ""
        if anti_ai_level >= 2:
            anti_ai_addon = ANSWER_ANTI_AI_SYSTEM
        elif anti_ai_level == 1:
            anti_ai_addon = ANSWER_ANTI_AI_LIGHT

        return f"""你是一位知乎高赞答主，经常在知乎上回答问题。{style_desc}。

## 回答核心原则
- 开头直接给结论或观点，不要用"关于这个问题"之类的废话开头
- 用第一人称，像真实的人在回答问题
- 排版用 Markdown：**加粗**重点、> 引用金句、有序/无序列表归纳、--- 分割
- 结尾可以反问或邀请讨论，增加互动
- 不要在回答中提到"我是AI"或暴露AI身份
{anti_ai_addon}

## 输出格式
你必须严格按照以下 JSON 格式返回，不要返回其他内容：
{{
    "content": "回答正文（Markdown格式）"
}}"""

    def _build_user_prompt(
        self,
        question: ZhihuQuestion,
        style: str,
        word_count: int,
        anti_ai_level: int,
    ) -> str:
        """构建用户提示词"""
        anti_ai_user = ""
        if anti_ai_level >= 2:
            anti_ai_user = ANSWER_ANTI_AI_USER
        elif anti_ai_level == 1:
            anti_ai_user = "\n注意：避免AI常见套话，文风要自然。\n"

        detail_text = ""
        if question.detail:
            detail_text = f"\n问题补充说明：{question.detail[:1000]}"

        topics_text = ""
        if question.topics:
            topics = question.topics if isinstance(question.topics, list) else []
            if topics:
                topics_text = f"\n相关话题：{'、'.join(topics[:5])}"

        meta_text = ""
        if question.follower_count > 0 or question.answer_count > 0:
            parts = []
            if question.follower_count > 0:
                parts.append(f"{question.follower_count} 人关注")
            if question.answer_count > 0:
                parts.append(f"已有 {question.answer_count} 个回答")
            if question.view_count > 0:
                parts.append(f"{question.view_count} 次浏览")
            meta_text = f"\n问题数据：{'，'.join(parts)}"

        return f"""请回答以下知乎问题：

问题：{question.title}{detail_text}{topics_text}{meta_text}

要求：
- 目标字数：约 {word_count} 字
- 回答要有深度、有见解、有个人风格
- 开头直接给出核心观点，不要铺垫太多
- 使用 Markdown 格式排版
- 如果问题已有较多回答（{question.answer_count}个），试着找到差异化角度
- 结尾加一个引导互动的问句
{anti_ai_user}
请严格按照 JSON 格式返回。"""

    async def regenerate_answer(
        self,
        answer_id: int,
        style: Optional[str] = None,
        word_count: Optional[int] = None,
        ai_provider: Optional[str] = None,
    ) -> Optional[dict]:
        """
        重新生成回答（覆盖已有的draft回答）
        """
        async with async_session_factory() as session:
            answer = await session.get(ZhihuAnswer, answer_id)
            if not answer:
                logger.error(f"回答不存在: ID={answer_id}")
                return None
            if answer.status != "draft":
                logger.error(f"只能重新生成草稿状态的回答: status={answer.status}")
                return None

            question = await session.get(ZhihuQuestion, answer.question_id)
            if not question:
                logger.error(f"关联的问题不存在: ID={answer.question_id}")
                return None

        # 用原有参数或新参数
        return await self.generate_answer(
            question_id=answer.question_id,
            account_id=answer.account_id,
            style=style or answer.style,
            word_count=word_count or answer.word_count or 1000,
            ai_provider=ai_provider or answer.ai_provider,
            anti_ai_level=answer.anti_ai_level,
        )


# 全局单例
qa_answer_generator = QAAnswerGenerator()
