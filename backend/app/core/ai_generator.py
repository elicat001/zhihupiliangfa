"""
AI 文章生成器
统一管理多个 AI 提供商，根据用户选择调用对应的 API
"""

import json
import logging
from typing import AsyncIterator, Optional

import httpx

from app.config import settings
from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle
from app.core.ai_providers.openai_provider import OpenAIProvider
from app.core.ai_providers.deepseek_provider import DeepSeekProvider
from app.core.ai_providers.claude_provider import ClaudeProvider
from app.core.ai_providers.qwen_provider import QwenProvider
from app.core.ai_providers.zhipu_provider import ZhipuProvider
from app.core.ai_providers.moonshot_provider import MoonshotProvider
from app.core.ai_providers.doubao_provider import DoubaoProvider

logger = logging.getLogger(__name__)


class AIGenerator:
    """AI 文章生成器"""

    def __init__(self):
        self._providers: dict[str, BaseAIProvider] = {}
        self._init_providers()

    def _init_providers(self):
        """根据配置初始化可用的 AI 提供商"""

        # 初始化 OpenAI
        if settings.OPENAI_API_KEY:
            self._providers["openai"] = OpenAIProvider(
                api_key=settings.OPENAI_API_KEY,
                base_url=settings.OPENAI_BASE_URL,
                model=settings.OPENAI_MODEL,
            )
            logger.info("OpenAI 提供商已初始化")

        # 初始化 DeepSeek
        if settings.DEEPSEEK_API_KEY:
            self._providers["deepseek"] = DeepSeekProvider(
                api_key=settings.DEEPSEEK_API_KEY,
                base_url=settings.DEEPSEEK_BASE_URL,
                model=settings.DEEPSEEK_MODEL,
            )
            logger.info("DeepSeek 提供商已初始化")

        # 初始化 Claude
        if settings.CLAUDE_API_KEY:
            self._providers["claude"] = ClaudeProvider(
                api_key=settings.CLAUDE_API_KEY,
                base_url=settings.CLAUDE_BASE_URL,
                model=settings.CLAUDE_MODEL,
            )
            logger.info("Claude 提供商已初始化")

        # 初始化通义千问
        if settings.QWEN_API_KEY:
            self._providers["qwen"] = QwenProvider(
                api_key=settings.QWEN_API_KEY,
                base_url=settings.QWEN_BASE_URL,
                model=settings.QWEN_MODEL,
            )
            logger.info("通义千问 提供商已初始化")

        # 初始化智谱 GLM
        if settings.ZHIPU_API_KEY:
            self._providers["zhipu"] = ZhipuProvider(
                api_key=settings.ZHIPU_API_KEY,
                base_url=settings.ZHIPU_BASE_URL,
                model=settings.ZHIPU_MODEL,
            )
            logger.info("智谱 GLM 提供商已初始化")

        # 初始化月之暗面 Kimi
        if settings.MOONSHOT_API_KEY:
            self._providers["moonshot"] = MoonshotProvider(
                api_key=settings.MOONSHOT_API_KEY,
                base_url=settings.MOONSHOT_BASE_URL,
                model=settings.MOONSHOT_MODEL,
            )
            logger.info("月之暗面 Kimi 提供商已初始化")

        # 初始化豆包
        if settings.DOUBAO_API_KEY:
            self._providers["doubao"] = DoubaoProvider(
                api_key=settings.DOUBAO_API_KEY,
                base_url=settings.DOUBAO_BASE_URL,
                model=settings.DOUBAO_MODEL,
            )
            logger.info("豆包 提供商已初始化")

        if not self._providers:
            logger.warning(
                "没有配置任何 AI API Key，请在 .env 文件或环境变量中设置"
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
        所有提供商都使用兼容 OpenAI 的 API 格式。
        """
        url = f"{provider.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": provider.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 4096,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        return data["choices"][0]["message"]["content"]

    async def generate(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "deepseek",
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
        provider = self._providers.get(ai_provider)
        if not provider:
            available = self.get_available_providers()
            if not available:
                raise ValueError(
                    "没有可用的 AI 提供商，请先配置 API Key"
                )
            raise ValueError(
                f"AI 提供商 '{ai_provider}' 不可用。"
                f"可用的提供商: {', '.join(available)}"
            )

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

    async def generate_stream(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
        ai_provider: str = "deepseek",
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
        provider = self._providers.get(ai_provider)
        if not provider:
            available = self.get_available_providers()
            if not available:
                raise ValueError(
                    "没有可用的 AI 提供商，请先配置 API Key"
                )
            raise ValueError(
                f"AI 提供商 '{ai_provider}' 不可用。"
                f"可用的提供商: {', '.join(available)}"
            )

        logger.info(
            f"使用 {ai_provider} 流式生成文章: topic={topic}, "
            f"style={style}, word_count={word_count}"
        )

        async for chunk in provider.generate_article_stream(
            topic=topic, style=style, word_count=word_count
        ):
            yield chunk

    # ==================== 系列文章生成 ====================

    async def generate_series_outline(
        self,
        topic: str,
        count: int = 5,
        ai_provider: str = "deepseek",
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

            # 解析 JSON
            text = text.strip()
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()

            try:
                data = json.loads(text)
            except json.JSONDecodeError:
                start = text.find("{")
                end = text.rfind("}") + 1
                if start != -1 and end > start:
                    data = json.loads(text[start:end])
                else:
                    raise ValueError(
                        f"无法从 AI 返回内容中解析系列大纲 JSON: {text[:200]}..."
                    )

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
        ai_provider: str = "deepseek",
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
        ai_provider: str = "deepseek",
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
