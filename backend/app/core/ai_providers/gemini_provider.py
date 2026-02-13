"""
Google Gemini 提供商适配器
Gemini 使用兼容 OpenAI 的 API 格式（通过 generativelanguage 端点）
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class GeminiProvider(OpenAICompatibleProvider):
    """Google Gemini API 适配器（支持 Thinking 模型）"""

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
        需要更大的 max_tokens 预算以确保输出内容完整。"""
        payload = super()._build_chat_payload(
            system_prompt, user_prompt, stream=stream
        )
        payload["max_tokens"] = 16384
        return payload
