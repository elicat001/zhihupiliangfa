"""
设置相关 API 路由
提供系统配置的读取和更新，并持久化到 .env 文件
"""

import logging
import os
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/settings", tags=["系统设置"])

# .env 文件路径（与 config.py 中一致）
_ENV_FILE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    ".env",
)


# ==================== 响应/请求模型 ====================

class AIConfigResponse(BaseModel):
    provider: str = "deepseek"
    api_key: str = ""
    base_url: str = ""
    model: str = ""
    temperature: float = 0.7
    max_tokens: int = 4096


class PublishStrategyResponse(BaseModel):
    default_mode: str = "immediate"
    interval_minutes: int = 5
    max_retries: int = 3
    retry_delay_seconds: int = 60
    daily_limit: int = 5


class BrowserConfigResponse(BaseModel):
    headless: bool = False
    launch_timeout: int = 60000
    action_timeout: int = 60000
    user_agent: str = ""
    proxy: str = ""


class SettingsResponse(BaseModel):
    ai_config: AIConfigResponse
    publish_strategy: PublishStrategyResponse
    browser_config: BrowserConfigResponse


class SettingsUpdateRequest(BaseModel):
    ai_config: Optional[AIConfigResponse] = None
    publish_strategy: Optional[PublishStrategyResponse] = None
    browser_config: Optional[BrowserConfigResponse] = None


# ==================== API 端点 ====================

def _mask_key(key: Optional[str]) -> str:
    """遮蔽 API Key，只显示前 4 位和后 4 位"""
    if not key:
        return ""
    if len(key) <= 8:
        return "***"
    return key[:4] + "***" + key[-4:]


@router.get("", response_model=SettingsResponse, summary="获取当前设置")
async def get_settings():
    """获取系统设置（API Key 部分遮蔽）"""
    # 判断当前激活的 AI 提供商
    if settings.DEEPSEEK_API_KEY:
        provider = "deepseek"
        api_key = _mask_key(settings.DEEPSEEK_API_KEY)
        base_url = settings.DEEPSEEK_BASE_URL
        model = settings.DEEPSEEK_MODEL
    elif settings.OPENAI_API_KEY:
        provider = "openai"
        api_key = _mask_key(settings.OPENAI_API_KEY)
        base_url = settings.OPENAI_BASE_URL
        model = settings.OPENAI_MODEL
    elif settings.CLAUDE_API_KEY:
        provider = "claude"
        api_key = _mask_key(settings.CLAUDE_API_KEY)
        base_url = settings.CLAUDE_BASE_URL
        model = settings.CLAUDE_MODEL
    else:
        provider = "deepseek"
        api_key = ""
        base_url = settings.DEEPSEEK_BASE_URL
        model = settings.DEEPSEEK_MODEL

    return SettingsResponse(
        ai_config=AIConfigResponse(
            provider=provider,
            api_key=api_key,
            base_url=base_url,
            model=model,
        ),
        publish_strategy=PublishStrategyResponse(
            daily_limit=settings.DAILY_PUBLISH_LIMIT,
            interval_minutes=settings.MIN_PUBLISH_INTERVAL // 60,
            max_retries=settings.MAX_RETRY_COUNT,
        ),
        browser_config=BrowserConfigResponse(
            headless=settings.BROWSER_HEADLESS,
            launch_timeout=settings.BROWSER_TIMEOUT,
            action_timeout=settings.BROWSER_TIMEOUT,
        ),
    )


def _persist_to_env(updates: dict[str, str]) -> None:
    """
    将键值对持久化到 .env 文件。
    已有的键会被更新，不存在的键会追加到末尾。
    """
    lines: list[str] = []
    updated_keys: set[str] = set()

    # 读取现有 .env
    if os.path.exists(_ENV_FILE_PATH):
        with open(_ENV_FILE_PATH, "r", encoding="utf-8") as f:
            lines = f.readlines()

    # 更新已有行
    new_lines: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}\n")
                updated_keys.add(key)
                continue
        new_lines.append(line if line.endswith("\n") else line + "\n")

    # 追加新键
    for key, value in updates.items():
        if key not in updated_keys:
            new_lines.append(f"{key}={value}\n")

    with open(_ENV_FILE_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)

    logger.info(f"已持久化设置到 .env: {list(updates.keys())}")


@router.put("", response_model=SettingsResponse, summary="更新设置")
async def update_settings(request: SettingsUpdateRequest):
    """
    更新系统设置并持久化到 .env 文件
    """
    env_updates: dict[str, str] = {}

    # AI 配置
    if request.ai_config:
        ai = request.ai_config
        provider = ai.provider or "deepseek"

        # 如果 api_key 包含 *** 则说明是遮蔽后的值，不更新
        real_key = ai.api_key if "***" not in ai.api_key else None

        if provider == "deepseek":
            if real_key:
                settings.DEEPSEEK_API_KEY = real_key
                env_updates["DEEPSEEK_API_KEY"] = real_key
            if ai.base_url:
                settings.DEEPSEEK_BASE_URL = ai.base_url
                env_updates["DEEPSEEK_BASE_URL"] = ai.base_url
            if ai.model:
                settings.DEEPSEEK_MODEL = ai.model
                env_updates["DEEPSEEK_MODEL"] = ai.model
        elif provider == "openai":
            if real_key:
                settings.OPENAI_API_KEY = real_key
                env_updates["OPENAI_API_KEY"] = real_key
            if ai.base_url:
                settings.OPENAI_BASE_URL = ai.base_url
                env_updates["OPENAI_BASE_URL"] = ai.base_url
            if ai.model:
                settings.OPENAI_MODEL = ai.model
                env_updates["OPENAI_MODEL"] = ai.model
        elif provider == "claude":
            if real_key:
                settings.CLAUDE_API_KEY = real_key
                env_updates["CLAUDE_API_KEY"] = real_key
            if ai.base_url:
                settings.CLAUDE_BASE_URL = ai.base_url
                env_updates["CLAUDE_BASE_URL"] = ai.base_url
            if ai.model:
                settings.CLAUDE_MODEL = ai.model
                env_updates["CLAUDE_MODEL"] = ai.model

        logger.info(f"更新 AI 配置: provider={provider}")

    # 发布策略
    if request.publish_strategy:
        ps = request.publish_strategy
        settings.DAILY_PUBLISH_LIMIT = ps.daily_limit
        settings.MIN_PUBLISH_INTERVAL = ps.interval_minutes * 60
        settings.MAX_RETRY_COUNT = ps.max_retries
        env_updates["DAILY_PUBLISH_LIMIT"] = str(ps.daily_limit)
        env_updates["MIN_PUBLISH_INTERVAL"] = str(ps.interval_minutes * 60)
        env_updates["MAX_RETRY_COUNT"] = str(ps.max_retries)
        logger.info(f"更新发布策略: daily_limit={ps.daily_limit}")

    # 浏览器配置
    if request.browser_config:
        bc = request.browser_config
        settings.BROWSER_HEADLESS = bc.headless
        settings.BROWSER_TIMEOUT = bc.launch_timeout
        env_updates["BROWSER_HEADLESS"] = str(bc.headless).lower()
        env_updates["BROWSER_TIMEOUT"] = str(bc.launch_timeout)
        logger.info(f"更新浏览器配置: headless={bc.headless}")

    # 持久化到 .env
    if env_updates:
        _persist_to_env(env_updates)

    # 返回更新后的设置
    return await get_settings()
