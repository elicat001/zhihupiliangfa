"""
Claude / Anthropic 提供商适配器
使用 Anthropic Messages API 格式
"""

import json
from typing import AsyncIterator

import httpx

from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude API 适配器"""

    @property
    def provider_name(self) -> str:
        return "claude"

    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> GeneratedArticle:
        """
        调用 Anthropic Messages API 生成文章
        Anthropic 使用不同于 OpenAI 的 API 格式

        Args:
            topic: 文章主题
            style: 写作风格
            word_count: 目标字数

        Returns:
            GeneratedArticle: 生成的文章
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()

        # Anthropic 响应格式：content 是数组
        text = data["content"][0]["text"]
        return self._parse_response(text)

    async def generate_article_stream(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> AsyncIterator[str]:
        """
        流式调用 Anthropic Messages API，逐 token 返回

        Anthropic 流式格式：
        event: content_block_delta
        data: {"type":"content_block_delta","delta":{"type":"text_delta","text":"..."}}
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        url = f"{self.base_url}/v1/messages"
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                event_type = ""
                async for line in response.aiter_lines():
                    if line.startswith("event: "):
                        event_type = line[7:].strip()
                        continue
                    if not line.startswith("data: "):
                        continue
                    if event_type != "content_block_delta":
                        continue
                    data_str = line[6:]
                    try:
                        data = json.loads(data_str)
                        delta = data.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            yield text
                    except (json.JSONDecodeError, KeyError):
                        continue
