"""
OpenAI 兼容 API 通用提供商适配器
适用于所有兼容 OpenAI Chat Completions API 格式的大模型服务
包括：OpenAI、DeepSeek、通义千问、智谱GLM、月之暗面Kimi、豆包 等
"""

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码（服务端临时故障）
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}
_MAX_RETRIES = 5
_BASE_DELAY = 2  # 秒，指数退避基数


class OpenAICompatibleProvider(BaseAIProvider):
    """
    OpenAI 兼容 API 通用适配器
    所有使用 /chat/completions 端点的提供商都可以继承此类，
    只需覆盖 provider_name 属性即可。
    """

    @property
    def provider_name(self) -> str:
        raise NotImplementedError

    def _build_headers(self) -> dict[str, str]:
        """构建 OpenAI 兼容的请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_chat_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        stream: bool = False,
    ) -> dict:
        """构建 OpenAI 兼容的请求体"""
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 4096,
        }
        if stream:
            payload["stream"] = True
        return payload

    async def chat(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """
        通用聊天接口（OpenAI 兼容格式），内置指数退避重试
        """
        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        payload = self._build_chat_payload(system_prompt, user_prompt)

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
                    response = await client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    data = response.json()
                return data["choices"][0]["message"]["content"]
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                if status in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"[{self.provider_name}] 第{attempt}次请求失败 "
                        f"(HTTP {status})，{delay}s 后重试..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    f"[{self.provider_name}] API 请求失败 "
                    f"(HTTP {status}): {e.response.text[:500]}"
                )
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"[{self.provider_name}] 第{attempt}次连接/超时异常 "
                        f"({type(e).__name__})，{delay}s 后重试..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"[{self.provider_name}] 调用异常: {e}")
                raise
            except Exception as e:
                logger.error(f"[{self.provider_name}] 调用异常: {e}")
                raise
        raise last_exc  # type: ignore[misc]

    async def generate_article(
        self,
        topic: str,
        style: str = "professional",
        word_count: int = 1500,
    ) -> GeneratedArticle:
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
        system_prompt = self._build_system_prompt()
        user_prompt = self._build_user_prompt(topic, style, word_count)

        url = f"{self.base_url}/chat/completions"
        headers = self._build_headers()
        payload = self._build_chat_payload(
            system_prompt, user_prompt, stream=True
        )

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=180.0, trust_env=False) as client:
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
                return  # 流式成功完成，退出重试循环
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                # 流式响应需要先 read 才能访问 text
                try:
                    await e.response.aread()
                    error_text = e.response.text[:500]
                except Exception:
                    error_text = "(无法读取响应体)"
                if status in _RETRYABLE_STATUS_CODES and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"[{self.provider_name}] 流式第{attempt}次请求失败 "
                        f"(HTTP {status})，{delay}s 后重试..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(
                    f"[{self.provider_name}] 流式请求失败 "
                    f"(HTTP {status}): {error_text}"
                )
                raise
            except (httpx.ConnectError, httpx.ReadTimeout) as e:
                last_exc = e
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"[{self.provider_name}] 流式第{attempt}次连接/超时异常 "
                        f"({type(e).__name__})，{delay}s 后重试..."
                    )
                    await asyncio.sleep(delay)
                    continue
                logger.error(f"[{self.provider_name}] 流式调用异常: {e}")
                raise
            except Exception as e:
                logger.error(f"[{self.provider_name}] 流式调用异常: {e}")
                raise
        raise last_exc  # type: ignore[misc]
