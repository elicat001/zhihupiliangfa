"""
OpenAI 兼容 API 通用提供商适配器
适用于所有兼容 OpenAI Chat Completions API 格式的大模型服务
包括：OpenAI、DeepSeek、通义千问、智谱GLM、月之暗面Kimi、豆包 等
"""

import json
from typing import AsyncIterator

import httpx

from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle


class OpenAICompatibleProvider(BaseAIProvider):
    """
    OpenAI 兼容 API 通用适配器
    所有使用 /chat/completions 端点的提供商都可以继承此类，
    只需覆盖 provider_name 属性即可。
    """

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> GeneratedArticle:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
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

        text = data["choices"][0]["message"]["content"]
        return self._parse_response(text)

    async def generate_article_stream(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> AsyncIterator[str]:
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 4096,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        continue
