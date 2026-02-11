"""
通义千问 提供商适配器
阿里云通义千问使用兼容 OpenAI 的 API 格式
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class QwenProvider(OpenAICompatibleProvider):
    """通义千问 API 适配器"""

    @property
    def provider_name(self) -> str:
        return "qwen"
