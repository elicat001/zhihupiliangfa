"""
OpenAI 提供商适配器
兼容所有 OpenAI API 格式的服务（如 OpenAI 官方、Azure OpenAI 等）
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class OpenAIProvider(OpenAICompatibleProvider):
    """OpenAI 兼容 API 适配器"""

    @property
    def provider_name(self) -> str:
        return "openai"
