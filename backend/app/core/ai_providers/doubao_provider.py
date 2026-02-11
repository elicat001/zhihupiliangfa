"""
豆包 提供商适配器
字节跳动豆包使用兼容 OpenAI 的 API 格式
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class DoubaoProvider(OpenAICompatibleProvider):
    """豆包 API 适配器"""

    @property
    def provider_name(self) -> str:
        return "doubao"
