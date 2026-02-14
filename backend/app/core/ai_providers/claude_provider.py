"""
Claude / Anthropic 提供商适配器
支持 Anthropic 原生 Messages API 和 OpenAI 兼容代理两种模式：
- base_url 含 anthropic.com → 使用 Anthropic 原生格式
- 其他地址 → 自动切换为 OpenAI 兼容格式（适配统一代理）
"""

import json
import logging
from typing import AsyncIterator

import httpx

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider
from app.core.ai_providers.base import GeneratedArticle

logger = logging.getLogger(__name__)


class ClaudeProvider(OpenAICompatibleProvider):
    """Anthropic Claude API 适配器（自动检测代理模式）"""

    @property
    def provider_name(self) -> str:
        return "claude"

    @property
    def _use_native_api(self) -> bool:
        """是否使用 Anthropic 原生 API 格式"""
        return "anthropic.com" in self.base_url

    # ---------- OpenAI 兼容模式 ----------
    # 当 _use_native_api 为 False 时，直接继承 OpenAICompatibleProvider
    # 的 _build_headers / _build_chat_payload / chat / generate_article /
    # generate_article_stream 等方法，无需额外代码。

    # ---------- Anthropic 原生模式 ----------

    def _build_headers(self) -> dict[str, str]:
        if not self._use_native_api:
            return super()._build_headers()
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
        if not self._use_native_api:
            return super()._build_chat_payload(
                system_prompt, user_prompt, stream=stream
            )
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
        if not self._use_native_api:
            return await super().chat(system_prompt, user_prompt)

        # Anthropic 原生 Messages API
        url = f"{self.base_url}/v1/messages"
        headers = self._build_headers()
        payload = self._build_chat_payload(system_prompt, user_prompt)

        try:
            async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
                response = await client.post(url, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()
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
        if not self._use_native_api:
            return await super().generate_article(topic, style, word_count)

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
        if not self._use_native_api:
            async for chunk in super().generate_article_stream(
                topic, style, word_count
            ):
                yield chunk
            return

        # Anthropic 原生流式格式
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
            try:
                await e.response.aread()
                error_text = e.response.text[:500]
            except Exception:
                error_text = "(无法读取响应体)"
            logger.error(
                f"[claude] 流式请求失败 "
                f"(HTTP {e.response.status_code}): {error_text}"
            )
            raise
        except Exception as e:
            logger.error(f"[claude] 流式调用异常: {e}")
            raise
