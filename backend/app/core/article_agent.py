"""
智能文章生成 Agent
基于参考文章分析、规划并批量生成相关文章

工作流程：
1. 分析阶段：分析输入的参考文章，提取主题、风格、关键词、核心观点
2. 规划阶段：基于分析结果，规划 N 篇相关文章的大纲
3. 生成阶段：逐篇生成完整文章，保持风格一致但角度各异
"""

import json
import logging
import re
import uuid
from typing import Optional

from app.core.ai_generator import ai_generator
from app.core.ai_providers.base import BaseAIProvider

logger = logging.getLogger(__name__)


class ArticleAgent:
    """智能文章生成 Agent"""

    def __init__(self):
        self.ai_generator = ai_generator

    async def _call_chat(
        self, provider: BaseAIProvider, system_prompt: str, user_prompt: str
    ) -> str:
        """统一调用 AI Chat，复用 ai_generator 的方法"""
        return await self.ai_generator._call_provider_chat(
            provider, system_prompt, user_prompt
        )

    def _parse_json_response(self, text: str) -> dict:
        """解析 AI 返回的 JSON（strict=False 允许控制字符）"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

        try:
            return json.loads(text, strict=False)
        except json.JSONDecodeError:
            start = text.find("{")
            end = text.rfind("}") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end], strict=False)
            # Try finding array
            start = text.find("[")
            end = text.rfind("]") + 1
            if start != -1 and end > start:
                return json.loads(text[start:end], strict=False)
            raise ValueError(f"无法解析 AI 返回的 JSON: {text[:200]}...")

    async def analyze_articles(
        self,
        articles: list[dict],
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        第一步：分析参考文章

        Args:
            articles: 参考文章列表，每篇包含 title, content
            ai_provider: AI 提供商

        Returns:
            分析结果 dict，包含主题、风格、关键词等
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        # 构建参考文章文本
        articles_text = ""
        for i, article in enumerate(articles, 1):
            content_preview = article["content"][:2000]
            articles_text += f"\n\n--- 参考文章 {i}: {article['title']} ---\n{content_preview}"

        system_prompt = """你是一位资深的内容策略分析师，擅长分析文章的主题、风格和受众特征。
请认真分析给出的参考文章，提取关键信息。
你必须严格按照指定的 JSON 格式返回，不要返回任何其他内容。"""

        user_prompt = f"""请分析以下 {len(articles)} 篇参考文章，提取核心信息：

{articles_text}

请严格按照以下 JSON 格式返回分析结果：
{{
    "main_topic": "这些文章的核心主题领域（10字以内）",
    "sub_topics": ["子主题1", "子主题2", "子主题3"],
    "writing_style": "overall写作风格描述（如：专业严谨、轻松幽默等）",
    "target_audience": "目标读者群体描述",
    "keywords": ["关键词1", "关键词2", "关键词3", "关键词4", "关键词5"],
    "core_viewpoints": ["核心观点1", "核心观点2", "核心观点3"],
    "content_gaps": ["这些文章未覆盖但相关的角度1", "角度2", "角度3"]
}}"""

        logger.info(f"Agent 分析阶段：分析 {len(articles)} 篇参考文章")

        text = await self._call_chat(provider, system_prompt, user_prompt)
        analysis = self._parse_json_response(text)

        logger.info(f"Agent 分析完成：主题={analysis.get('main_topic', '未知')}")
        return analysis

    async def plan_articles(
        self,
        analysis: dict,
        count: int = 5,
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        第二步：规划文章大纲

        Args:
            analysis: 分析阶段的结果
            count: 要生成的文章数量
            ai_provider: AI 提供商

        Returns:
            规划结果 dict，包含文章大纲列表
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        system_prompt = """你是一位资深的知乎专栏策划编辑，擅长基于已有内容策划新的系列文章。
你需要基于对参考文章的分析结果，规划出全新的、有差异化角度的文章系列。
每篇文章都应该有独特的切入点，避免和参考文章的内容雷同。
你必须严格按照指定的 JSON 格式返回，不要返回任何其他内容。"""

        user_prompt = f"""基于以下对参考文章的分析结果，请规划 {count} 篇全新的相关文章：

分析结果：
- 核心主题：{analysis.get('main_topic', '')}
- 子主题：{', '.join(analysis.get('sub_topics', []))}
- 写作风格：{analysis.get('writing_style', '')}
- 目标读者：{analysis.get('target_audience', '')}
- 关键词：{', '.join(analysis.get('keywords', []))}
- 核心观点：{json.dumps(analysis.get('core_viewpoints', []), ensure_ascii=False)}
- 未覆盖的角度：{json.dumps(analysis.get('content_gaps', []), ensure_ascii=False)}

规划要求：
1. 每篇文章有独特的角度和切入点，不要和参考文章雷同
2. 覆盖参考文章未涉及的维度和观点
3. 文章之间有逻辑关联但不重复
4. 标题要符合知乎爆款标题特征（疑问式、数字式、颠覆认知式）
5. 每篇文章带有明确的关键要点列表

请严格按照以下 JSON 格式返回：
{{
    "series_title": "系列总标题",
    "description": "系列介绍（50字以内）",
    "recommended_style": "推荐的写作风格（professional/casual/humorous/academic/storytelling/tutorial）",
    "articles": [
        {{
            "order": 1,
            "title": "文章标题（15-25字）",
            "angle": "本文的独特切入角度（20字以内）",
            "description": "文章内容概述（50字以内）",
            "key_points": ["要点1", "要点2", "要点3", "要点4"]
        }}
    ]
}}"""

        logger.info(f"Agent 规划阶段：规划 {count} 篇文章")

        text = await self._call_chat(provider, system_prompt, user_prompt)
        plan = self._parse_json_response(text)

        logger.info(
            f"Agent 规划完成：系列={plan.get('series_title', '未知')}, "
            f"篇数={len(plan.get('articles', []))}"
        )
        return plan

    async def generate_articles(
        self,
        plan: dict,
        analysis: dict,
        reference_articles: list[dict],
        style: Optional[str] = None,
        word_count: int = 1500,
        ai_provider: Optional[str] = None,
    ) -> list[dict]:
        """
        第三步：批量生成文章

        Args:
            plan: 规划阶段的结果
            analysis: 分析阶段的结果
            reference_articles: 原始参考文章
            style: 写作风格（None则使用规划推荐的风格）
            word_count: 每篇目标字数
            ai_provider: AI 提供商

        Returns:
            生成的文章列表
        """
        ai_provider = self.ai_generator._resolve_provider(ai_provider)
        provider = self.ai_generator._get_provider_or_raise(ai_provider)

        actual_style = style or plan.get("recommended_style", "professional")
        series_id = str(uuid.uuid4())
        series_title = plan.get("series_title", "智能生成系列")
        planned_articles = plan.get("articles", [])

        generated = []

        for idx, article_plan in enumerate(planned_articles):
            title = article_plan.get("title", f"文章 {idx + 1}")
            angle = article_plan.get("angle", "")
            description = article_plan.get("description", "")
            key_points = article_plan.get("key_points", [])
            points_text = "\n".join(f"- {p}" for p in key_points)

            # 使用简洁的系统提示词（不含图片指令，避免与 JSON 格式冲突）
            system_prompt = """你是一位拥有10万+粉丝的知乎头部创作者，文章多次登上知乎热榜。

## 知乎排版规范
- 使用 ## 二级标题分段
- 重要观点用 **加粗** 标注
- 适当使用 > 引用块来突出金句或数据
- 使用有序/无序列表来归纳要点
- 段与段之间用 --- 分割线过渡

## 反AI检测写作规范（极其重要）
- 绝对禁止使用："然而""不禁""竟然""值得一提的是""毫无疑问""与此同时""总而言之""综上所述"
- 必须用口语化过渡："说白了""简单来说""你想啊""坦白讲"
- 插入个人化表达："我个人觉得""说实话""据我了解"
- 段落长度随机变化，不要每段都一样长
- 每篇文章至少包含2个具体案例或"个人经历"
- 句式长短交替，偶尔用反问句或感叹句
- 允许表达不确定："可能""大概""或许"
- 偶尔跑题再拉回："扯远了，说回正题"

## 输出格式要求
你必须严格按照以下 JSON 格式返回，不要返回任何其他内容：
{
    "title": "文章标题（15-25字，含核心关键词）",
    "content": "文章正文内容（Markdown 格式，不要插入任何图片占位符）",
    "summary": "100字以内的文章摘要",
    "tags": ["标签1", "标签2", "标签3", "标签4", "标签5"]
}"""

            user_prompt = f"""请以「{title}」为标题，写一篇知乎专栏文章。

背景信息：
- 这是系列「{series_title}」的第 {idx + 1}/{len(planned_articles)} 篇
- 核心主题领域：{analysis.get('main_topic', '')}
- 目标读者：{analysis.get('target_audience', '')}
- 本文独特角度：{angle}
- 文章描述：{description}

需要覆盖的关键要点：
{points_text}

写作要求：
- 写作风格：{actual_style}
- 目标字数：约 {word_count} 字
- 内容必须原创，不要照搬参考资料
- 在本文独特角度上深入展开，提供独到见解
- 使用 Markdown 格式排版
- 选择 5 个知乎上热度高的相关话题标签
- 文末加一个引导评论的互动问题

请严格按照指定的 JSON 格式返回。"""

            logger.info(
                f"Agent 生成阶段：[{idx + 1}/{len(planned_articles)}] {title}"
            )

            try:
                text = await self._call_chat(provider, system_prompt, user_prompt)
                data = self._parse_json_response(text)

                content = data.get("content", "")
                # 清理可能残留的图片占位符
                content = re.sub(r'\[IMG\d+\]', '', content)
                title_out = data.get("title", title)
                actual_word_count = len(
                    content.replace(" ", "").replace("\n", "")
                )

                generated.append({
                    "title": title_out,
                    "content": content,
                    "summary": data.get("summary", ""),
                    "tags": data.get("tags", []),
                    "word_count": actual_word_count,
                    "ai_provider": ai_provider,
                    "series_id": series_id,
                    "series_order": idx + 1,
                    "series_title": series_title,
                })

                logger.info(
                    f"Agent 生成完成：[{idx + 1}/{len(planned_articles)}] "
                    f"{title_out} (字数: {actual_word_count})"
                )
            except Exception as e:
                logger.error(
                    f"Agent 生成失败：[{idx + 1}/{len(planned_articles)}] "
                    f"{title}: {e}"
                )
                generated.append({
                    "title": title,
                    "content": f"生成失败: {str(e)}",
                    "summary": "",
                    "tags": [],
                    "word_count": 0,
                    "ai_provider": ai_provider,
                    "series_id": series_id,
                    "series_order": idx + 1,
                    "series_title": series_title,
                    "error": str(e),
                })

        return generated

    async def run(
        self,
        articles: list[dict],
        count: int = 5,
        style: Optional[str] = None,
        word_count: int = 1500,
        ai_provider: Optional[str] = None,
    ) -> dict:
        """
        一键运行完整的 Agent 工作流

        Args:
            articles: 参考文章列表，每篇含 title, content
            count: 要生成的文章数量
            style: 写作风格（None=AI自动推荐）
            word_count: 每篇目标字数
            ai_provider: AI 提供商

        Returns:
            包含分析结果、规划和生成文章的完整结果
        """
        logger.info(
            f"Agent 启动：参考文章={len(articles)}篇, "
            f"目标生成={count}篇, provider={ai_provider}"
        )

        # Step 1: 分析
        analysis = await self.analyze_articles(articles, ai_provider)

        # Step 2: 规划
        plan = await self.plan_articles(analysis, count, ai_provider)

        # Step 3: 生成
        generated = await self.generate_articles(
            plan=plan,
            analysis=analysis,
            reference_articles=articles,
            style=style,
            word_count=word_count,
            ai_provider=ai_provider,
        )

        result = {
            "analysis": analysis,
            "plan": plan,
            "articles": generated,
            "stats": {
                "reference_count": len(articles),
                "planned_count": len(plan.get("articles", [])),
                "generated_count": len([a for a in generated if "error" not in a]),
                "failed_count": len([a for a in generated if "error" in a]),
            },
        }

        logger.info(
            f"Agent 完成：成功={result['stats']['generated_count']}篇, "
            f"失败={result['stats']['failed_count']}篇"
        )
        return result


# 全局单例
article_agent = ArticleAgent()
