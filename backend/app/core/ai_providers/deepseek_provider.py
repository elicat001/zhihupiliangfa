"""
DeepSeek 提供商适配器
DeepSeek 使用兼容 OpenAI 的 API 格式
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    """DeepSeek API 适配器"""

    @property
    def provider_name(self) -> str:
        return "deepseek"
