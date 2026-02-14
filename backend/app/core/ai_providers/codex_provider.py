"""
OpenAI Codex (GPT-5) 提供商适配器
使用 OpenAI Responses API 格式（/responses 端点），而非 Chat Completions API。
此代理要求 stream=true，input 为消息列表。
"""

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.core.ai_providers.base import BaseAIProvider, GeneratedArticle

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}
_MAX_RETRIES = 5
_BASE_DELAY = 2


class CodexProvider(BaseAIProvider):
    """OpenAI Codex (GPT-5) Responses API 适配器"""

    @property
    def provider_name(self) -> str:
        return "codex"

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    def _build_responses_payload(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> dict:
        """构建 Responses API 请求体"""
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "stream": True,
        }
        return payload

    async def _collect_stream_text(
        self, response: httpx.Response
    ) -> str:
        """从 Responses API SSE 流中收集完整文本"""
        collected = []
        async for line in response.aiter_lines():
            if not line.startswith("data: "):
                continue
            data_str = line[6:]
            try:
                data = json.loads(data_str)
            except json.JSONDecodeError:
                continue
            event_type = data.get("type", "")
            if event_type == "response.output_text.delta":
                delta = data.get("delta", "")
                if delta:
                    collected.append(delta)
            elif event_type == "response.completed":
                break
        return "".join(collected)

    async def chat(
        self, system_prompt: str, user_prompt: str
    ) -> str:
        """通过 Responses API 流式收集完整响应"""
        url = f"{self.base_url}/responses"
        headers = self._build_headers()
        payload = self._build_responses_payload(system_prompt, user_prompt)

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
                    async with client.stream(
                        "POST", url, json=payload, headers=headers
                    ) as response:
                        response.raise_for_status()
                        text = await self._collect_stream_text(response)
                if text:
                    return text
                raise ValueError("Codex 返回空响应")
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
                try:
                    await e.response.aread()
                    error_text = e.response.text[:500]
                except Exception:
                    error_text = "(无法读取响应体)"
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
                    f"(HTTP {status}): {error_text}"
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

        url = f"{self.base_url}/responses"
        headers = self._build_headers()
        payload = self._build_responses_payload(system_prompt, user_prompt)

        last_exc: Exception | None = None
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=300.0, trust_env=False) as client:
                    async with client.stream(
                        "POST", url, json=payload, headers=headers
                    ) as response:
                        response.raise_for_status()
                        async for line in response.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            data_str = line[6:]
                            try:
                                data = json.loads(data_str)
                            except json.JSONDecodeError:
                                continue
                            event_type = data.get("type", "")
                            if event_type == "response.output_text.delta":
                                delta = data.get("delta", "")
                                if delta:
                                    yield delta
                            elif event_type == "response.completed":
                                break
                return
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
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
