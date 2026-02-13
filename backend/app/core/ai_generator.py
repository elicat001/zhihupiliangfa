"""
AI 文章生成器
统一管理多个 AI 提供商，根据用户选择调用对应的 API
"""

import json
import logging
import re
from typing import AsyncIterator, Optional

from app.config import settings
from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle
from app.core.image_service import image_service, ImageRequest
from app.core.ai_providers.openai_provider import OpenAIProvider
from app.core.ai_providers.deepseek_provider import DeepSeekProvider
from app.core.ai_providers.claude_provider import ClaudeProvider
from app.core.ai_providers.qwen_provider import QwenProvider
from app.core.ai_providers.zhipu_provider import ZhipuProvider
from app.core.ai_providers.moonshot_provider import MoonshotProvider
from app.core.ai_providers.doubao_provider import DoubaoProvider
from app.core.ai_providers.gemini_provider import GeminiProvider

logger = logging.getLogger(__name__)


class AIGenerator:
    """AI 文章生成器"""

    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {}
        self._init_providers()

    def _try_init_provider(
        self, name: str, provider_cls: type, api_key: Optional[str], base_url: str, model: str
    ):
        """
        安全地初始化单个提供商，捕获异常避免影响其他提供商。
        """
        if not api_key:
            return
        try:
            self._providers[name] = provider_cls(
                api_key=api_key,
                base_url=base_url,
                model=model,
            )
            logger.info(f"{name} 提供商已初始化 (model={model})")
        except Exception as e:
            logger.warning(f"{name} 提供商初始化失败: {e}")

    def _init_providers(self):
        """根据配置初始化可用的 AI 提供商"""

        self._try_init_provider(
            "openai", OpenAIProvider,
            settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL, settings.OPENAI_MODEL,
        )
        self._try_init_provider(
            "deepseek", DeepSeekProvider,
            settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_BASE_URL, settings.DEEPSEEK_MODEL,
        )
        self._try_init_provider(
            "claude", ClaudeProvider,
            settings.CLAUDE_API_KEY, settings.CLAUDE_BASE_URL, settings.CLAUDE_MODEL,
        )
        self._try_init_provider(
            "qwen", QwenProvider,
            settings.QWEN_API_KEY, settings.QWEN_BASE_URL, settings.QWEN_MODEL,
        )
        self._try_init_provider(
            "zhipu", ZhipuProvider,
            settings.ZHIPU_API_KEY, settings.ZHIPU_BASE_URL, settings.ZHIPU_MODEL,
        )
        self._try_init_provider(
            "moonshot", MoonshotProvider,
            settings.MOONSHOT_API_KEY, settings.MOONSHOT_BASE_URL, settings.MOONSHOT_MODEL,
        )
        self._try_init_provider(
            "doubao", DoubaoProvider,
            settings.DOUBAO_API_KEY, settings.DOUBAO_BASE_URL, settings.DOUBAO_MODEL,
        )
        self._try_init_provider(
            "gemini", GeminiProvider,
            settings.GEMINI_API_KEY, settings.GEMINI_BASE_URL, settings.GEMINI_MODEL,
        )

        if not self._providers:
            logger.warning(
                "没有配置任何 AI API Key，请在 .env 文件或环境变量中设置"
            )
        else:
            logger.info(
                f"已初始化 {len(self._providers)} 个 AI 提供商: "
                f"{', '.join(self._providers.keys())}"
            )

    def get_available_providers(self) -> list[str]:
        """获取可用的 AI 提供商列表"""
        return list(self._providers.keys())

    def get_provider(self, name: str) -> Optional[BaseAIProvider]:
        """获取指定的 AI 提供商"""
        return self._providers.get(name)

    def _get_provider_or_raise(self, ai_provider: str) -> BaseAIProvider:
        """获取指定的 AI 提供商，不存在则抛出异常"""
        provider = self._providers.get(ai_provider)
        if not provider:
            available = self.get_available_providers()
            if not available:
                raise ValueError("没有可用的 AI 提供商，请先配置 API Key")
            raise ValueError(
                f"AI 提供商 '{ai_provider}' 不可用。"
                f"可用的提供商: {', '.join(available)}"
            )
        return provider

    async def _call_provider_chat(
        self, provider: BaseAIProvider, system_prompt: str, user_prompt: str
    ) -> str:
        """
        通用方法：调用提供商的 Chat API 并返回原始文本响应。
        委托给各提供商自身的 chat() 方法，确保 Claude 等非 OpenAI 格式的
        提供商也能正确调用。
        """
        return await provider.chat(system_prompt, user_prompt)

    async def generate(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "gemini",
    ) -> GeneratedArticle:
        """
        生成文章

        Args:
            topic: 文章主题
            style: 写作风格
            word_count: 目标字数
            ai_provider: AI 提供商名称

        Returns:
            GeneratedArticle: 生成的文章

        Raises:
            ValueError: 当提供商不可用时
            Exception: 当 API 调用失败时
        """
        provider = self._get_provider_or_raise(ai_provider)

        logger.info(
            f"使用 {ai_provider} 生成文章: topic={topic}, "
            f"style={style}, word_count={word_count}"
        )

        try:
            article = await provider.generate_article(
                topic=topic, style=style, word_count=word_count
            )
            logger.info(
                f"文章生成成功: {article.title} "
                f"(实际字数: {article.word_count})"
            )
            return article
        except Exception as e:
            logger.error(f"文章生成失败 ({ai_provider}): {e}")
            raise

    async def generate_with_images(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "gemini",
    ) -> GeneratedArticle:
        """
        生成带图片的文章：
        1. LLM 生成文章 + 图片描述
        2. 获取图片（封面用 CogView，正文用 Unsplash）
        3. 将 [IMG] 占位符替换为 Markdown 图片语法
        """
        article = await self.generate(
            topic=topic, style=style,
            word_count=word_count, ai_provider=ai_provider,
        )

        image_requests: list[ImageRequest] = []

        if article.cover_image:
            image_requests.append(ImageRequest(
                id="cover",
                ai_prompt=article.cover_image.get("ai_prompt", ""),
                search_query=article.cover_image.get("search_query", topic),
                alt_text=article.cover_image.get("alt_text", "封面图"),
                is_cover=True,
            ))

        if article.images:
            for img in article.images:
                image_requests.append(ImageRequest(
                    id=img.get("id", f"IMG{len(image_requests)}"),
                    ai_prompt=img.get("ai_prompt", ""),
                    search_query=img.get("search_query", topic),
                    alt_text=img.get("alt_text", "配图"),
                    position=img.get("position"),
                    is_cover=False,
                ))

        if not image_requests:
            logger.info("LLM 未输出图片描述，跳过图片获取")
            return article

        logger.info(f"开始获取 {len(image_requests)} 张图片...")
        results = await image_service.fetch_all_images(image_requests)

        images_metadata: dict = {"cover": None, "inline": []}
        content = article.content

        for result in results:
            if result.id == "cover":
                images_metadata["cover"] = {
                    "path": result.local_path,
                    "alt_text": result.alt_text,
                    "source": result.source,
                }
            else:
                images_metadata["inline"].append({
                    "id": result.id,
                    "path": result.local_path,
                    "alt_text": result.alt_text,
                    "source": result.source,
                })
                placeholder = f"[{result.id}]"
                markdown_img = f"\n\n![{result.alt_text}](/api/images/{result.local_path})\n\n"
                content = content.replace(placeholder, markdown_img)

        # 清理未替换的占位符
        content = re.sub(r'\[IMG\d+\]', '', content)

        article.content = content
        article.images = images_metadata  # type: ignore
        logger.info(f"图片获取完成: {len(results)}/{len(image_requests)} 张成功")
        return article

    async def fetch_images_for_article(
        self, article: GeneratedArticle
    ) -> GeneratedArticle:
        """为已生成的文章获取图片（用于流式生成完成后）"""
        image_requests: list[ImageRequest] = []

        if article.cover_image:
            image_requests.append(ImageRequest(
                id="cover",
                ai_prompt=article.cover_image.get("ai_prompt", ""),
                search_query=article.cover_image.get("search_query", ""),
                alt_text=article.cover_image.get("alt_text", "封面图"),
                is_cover=True,
            ))

        if article.images:
            for img in article.images:
                image_requests.append(ImageRequest(
                    id=img.get("id", f"IMG{len(image_requests)}"),
                    ai_prompt=img.get("ai_prompt", ""),
                    search_query=img.get("search_query", ""),
                    alt_text=img.get("alt_text", "配图"),
                    is_cover=False,
                ))

        if not image_requests:
            return article

        results = await image_service.fetch_all_images(image_requests)

        images_metadata: dict = {"cover": None, "inline": []}
        content = article.content

        for result in results:
            if result.id == "cover":
                images_metadata["cover"] = {
                    "path": result.local_path,
                    "alt_text": result.alt_text,
                    "source": result.source,
                }
            else:
                images_metadata["inline"].append({
                    "id": result.id,
                    "path": result.local_path,
                    "alt_text": result.alt_text,
                    "source": result.source,
                })
                placeholder = f"[{result.id}]"
                markdown_img = f"\n\n![{result.alt_text}](/api/images/{result.local_path})\n\n"
                content = content.replace(placeholder, markdown_img)

        content = re.sub(r'\[IMG\d+\]', '', content)
        article.content = content
        article.images = images_metadata  # type: ignore
        return article

    async def generate_stream(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "gemini",
    ) -> AsyncIterator[str]:
        """
        流式生成文章，逐 token 返回

        Args:
            topic: 文章主题
            style: 写作风格
            word_count: 目标字数
            ai_provider: AI 提供商名称

        Yields:
            str: 每个 token/chunk 的文本

        Raises:
            ValueError: 当提供商不可用时
            Exception: 当 API 调用失败时
        """
        provider = self._get_provider_or_raise(ai_provider)

        logger.info(
            f"使用 {ai_provider} 流式生成文章: topic={topic}, "
            f"style={style}, word_count={word_count}"
        )

        try:
            async for chunk in provider.generate_article_stream(
                topic=topic, style=style, word_count=word_count
            ):
                yield chunk
        except Exception as e:
            logger.error(f"流式生成异常 ({ai_provider}): {e}")
            raise

    # ==================== JSON 解析工具 ====================

    @staticmethod
    def _parse_json_text(text: str) -> dict:
        """
        从 AI 返回的文本中解析 JSON，处理 markdown 代码块等情况。
        多个方法共用此逻辑，避免重复。
        """
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
            raise ValueError(
                f"无法从 AI 返回内容中解析 JSON: {text[:200]}..."
            )

    # ==================== 系列文章生成 ====================

    async def generate_series_outline(
        self,
        topic: str,
        count: int = 5,
        ai_provider: str = "gemini",
    ) -> dict:
        """
        生成系列文章大纲

        Args:
            topic: 系列主题
            count: 文章篇数
            ai_provider: AI 提供商

        Returns:
            dict: 包含 series_title, description, articles 的字典
        """
        provider = self._get_provider_or_raise(ai_provider)

        logger.info(f"使用 {ai_provider} 生成系列大纲: topic={topic}, count={count}")

        system_prompt = (
            "你是一位资深的知乎专栏策划编辑，擅长设计系列文章的整体框架和内容规划。"
            "请严格按照用户要求的 JSON 格式返回，不要返回任何其他内容。"
        )
        user_prompt = provider._build_series_outline_prompt(topic, count)

        try:
            text = await self._call_provider_chat(provider, system_prompt, user_prompt)
            data = self._parse_json_text(text)
            logger.info(f"系列大纲生成成功: {data.get('series_title', '未知')}")
            return data

        except Exception as e:
            logger.error(f"系列大纲生成失败 ({ai_provider}): {e}")
            raise

    async def generate_series_article(
        self,
        title: str,
        description: str,
        key_points: list[str],
        series_context: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "gemini",
    ) -> GeneratedArticle:
        """
        生成系列中的单篇文章

        Args:
            title: 文章标题
            description: 文章简述
            key_points: 要点列表
            series_context: 系列上下文描述
            style: 写作风格
            word_count: 目标字数
            ai_provider: AI 提供商

        Returns:
            GeneratedArticle: 生成的文章
        """
        provider = self._get_provider_or_raise(ai_provider)

        logger.info(f"使用 {ai_provider} 生成系列文章: {title}")

        style_map = {
            "professional": "专业严谨，数据驱动",
            "casual": "轻松活泼，通俗易懂",
            "humorous": "幽默风趣，善用段子",
            "academic": "学术严谨，逻辑缜密",
            "storytelling": "叙事型，引人入胜",
            "tutorial": "教程型，步骤清晰",
        }
        style_desc = style_map.get(style, style_map["professional"])
        points_text = "\n".join(f"- {p}" for p in key_points)

        system_prompt = provider._build_system_prompt()
        user_prompt = f"""请以「{title}」为标题，写一篇知乎专栏文章。

这是系列文章的一部分：{series_context}

文章描述：{description}

需要覆盖的要点：
{points_text}

要求：
- 写作风格：{style_desc}
- 目标字数：约 {word_count} 字
- 在文章开头或结尾自然地提及这是系列文章的一部分
- 内容要有深度、有独到见解
- 使用 Markdown 格式排版
- 选择 5 个相关话题标签

请严格按照指定的 JSON 格式返回。"""

        try:
            text = await self._call_provider_chat(provider, system_prompt, user_prompt)
            article = provider._parse_response(text)
            logger.info(
                f"系列文章生成成功: {article.title} (字数: {article.word_count})"
            )
            return article
        except Exception as e:
            logger.error(f"系列文章生成失败 ({ai_provider}): {e}")
            raise

    # ==================== 文章改写 ====================

    async def rewrite_article(
        self,
        content: str,
        style: str = "professional",
        instruction: str = "",
        ai_provider: str = "gemini",
    ) -> GeneratedArticle:
        """
        改写文章

        Args:
            content: 原文内容
            style: 改写风格
            instruction: 额外改写指令
            ai_provider: AI 提供商

        Returns:
            GeneratedArticle: 改写后的文章
        """
        provider = self._get_provider_or_raise(ai_provider)

        logger.info(f"使用 {ai_provider} 改写文章, style={style}")

        system_prompt = provider._build_system_prompt()
        user_prompt = provider._build_rewrite_prompt(content, style, instruction)

        try:
            text = await self._call_provider_chat(provider, system_prompt, user_prompt)
            article = provider._parse_response(text)
            logger.info(
                f"文章改写成功: {article.title} (字数: {article.word_count})"
            )
            return article
        except Exception as e:
            logger.error(f"文章改写失败 ({ai_provider}): {e}")
            raise


# 全局单例
ai_generator = AIGenerator()
