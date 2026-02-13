"""
Google Gemini 提供商适配器
支持 Gemini 原生 API 返回格式和 OpenAI 兼容格式的自动检测
"""

import asyncio
import json
import logging
from typing import AsyncIterator

import httpx

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider
from app.core.ai_providers.base import GeneratedArticle

logger = logging.getLogger(__name__)

# 可重试的 HTTP 状态码（服务端临时故障）
_RETRYABLE_STATUS_CODES = {500, 502, 503, 504, 429}
_MAX_RETRIES = 3
_BASE_DELAY = 2  # 秒，指数退避基数


class GeminiProvider(OpenAICompatibleProvider):
    """Google Gemini API 适配器（支持 Thinking 模型 + 原生返回格式）"""

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _build_chat_payload(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        stream: bool = False,
    ) -> dict:
        """Gemini 2.5+ 系列为 Thinking 模型，内部推理会消耗 token，
        需要更大的 max_tokens 预算以确保输出内容完整。

        注意：部分 API 代理不支持 Gemini 的 system 角色消息，
        因此将 system prompt 合并到 user 消息中以保证兼容性。
        """
        combined_user_prompt = (
            f"{system_prompt}\n\n---\n\n{user_prompt}"
            if system_prompt
            else user_prompt
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "user", "content": combined_user_prompt},
            ],
            "temperature": 0.8,
            "max_tokens": 16384,
        }
        if stream:
            payload["stream"] = True
        return payload

    @staticmethod
    def _extract_content(data: dict) -> str:
        """从响应中提取文本内容，兼容 OpenAI 格式和 Gemini 原生格式"""
        # OpenAI 兼容格式: choices[0].message.content
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        # Gemini 原生格式: response.candidates[0].content.parts[0].text
        resp = data.get("response", data)
        candidates = resp.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            texts = [p["text"] for p in parts if "text" in p]
            if texts:
                return "".join(texts)
        raise ValueError(f"无法从 Gemini 响应中提取内容: {json.dumps(data, ensure_ascii=False)[:500]}")

    async def chat(
        self, system_prompt: str, user_prompt: str
    ) -> str:
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
                return self._extract_content(data)
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
        # 理论上不会走到这里，但保险起见
        raise last_exc  # type: ignore[misc]

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
                        buffer = ""
                        async for line in response.aiter_lines():
                            # OpenAI SSE 格式
                            if line.startswith("data: "):
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
                            else:
                                # 可能是 Gemini 原生非流式返回（一次性）
                                buffer += line
                        # 如果没有 SSE 格式数据，尝试解析整个 buffer
                        if buffer.strip():
                            try:
                                data = json.loads(buffer)
                                content = self._extract_content(data)
                                if content:
                                    yield content
                            except (json.JSONDecodeError, ValueError):
                                pass
                return  # 流式成功完成，退出重试循环
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code
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
                    f"(HTTP {status}): {e.response.text[:500]}"
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
