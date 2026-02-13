"""
Claude / Anthropic 提供商适配器
使用 Anthropic Messages API 格式
"""

import json
import logging
from typing import AsyncIterator

import httpx

from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle

logger = logging.getLogger(__name__)


class ClaudeProvider(BaseAIProvider):
    """Anthropic Claude API 适配器"""

    @property
    def provider_name(self) -> str:
        return "claude"

    def _build_headers(self) -> dict[str, str]:
        """构建 Anthropic 专用请求头"""
        return {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }

    def _build_chat_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        stream: bool = False,
    ) -> dict:
        """构建 Anthropic Messages API 请求体"""
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": system_prompt,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
        }
        if stream:
            payload["stream"] = True
        return payload

    async def chat(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """
        通用聊天接口（Anthropic Messages API 格式）
        """
        url = f"{self.base_url}/v1/messages"
        headers = self._build_headers()
        payload = self._build_chat_payload(system_prompt, user_prompt)

        try:
            async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            # Anthropic 响应格式：content 是数组
            return data["content"][0]["text"]
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[claude] API 请求失败 "
                f"(HTTP {e.response.status_code}): {e.response.text[:500]}"
            )
            raise
        except Exception as e:
            logger.error(f"[claude] 调用异常: {e}")
            raise

    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> GeneratedArticle:
        """
        调用 Anthropic Messages API 生成文章
        """
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        text = await self.chat(system_prompt, user_prompt)
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
        headers = self._build_headers()
        payload = self._build_chat_payload(
            system_prompt, user_prompt, stream=True
        )

        try:
            async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
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
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[claude] 流式请求失败 "
                f"(HTTP {e.response.status_code}): {e.response.text[:500]}"
            )
            raise
        except Exception as e:
            logger.error(f"[claude] 流式调用异常: {e}")
            raise
