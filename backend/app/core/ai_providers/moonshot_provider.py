"""
月之暗面 Kimi 提供商适配器
Moonshot AI 使用兼容 OpenAI 的 API 格式
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class MoonshotProvider(OpenAICompatibleProvider):
    """月之暗面 Kimi API 适配器"""

    @property
    def provider_name(self) -> str:
        return "moonshot"
