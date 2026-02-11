"""
智谱 GLM 提供商适配器
智谱 AI 使用兼容 OpenAI 的 API 格式
"""

from app.core.ai_providers.openai_compatible_provider import OpenAICompatibleProvider


class ZhipuProvider(OpenAICompatibleProvider):
    """智谱 GLM API 适配器"""

    @property
    def provider_name(self) -> str:
        return "zhipu"
