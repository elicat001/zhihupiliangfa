"""
应用配置管理
使用 pydantic-settings 从环境变量和 .env 文件加载配置
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """全局配置"""

    # ========== 基础配置 ==========
    APP_NAME: str = "知乎自动发文系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    HOST: str = "0.0.0.0"
    PORT: int = 18900

    # ========== 数据库配置 ==========
    # SQLite 数据库文件路径
    DATABASE_PATH: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "data",
        "zhihu_publisher.db",
    )

    @property
    def DATABASE_URL(self) -> str:
        """异步 SQLite 连接字符串"""
        return f"sqlite+aiosqlite:///{self.DATABASE_PATH}"

    # ========== AI 提供商配置 ==========
    # OpenAI
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-5.2"

    # DeepSeek
    DEEPSEEK_API_KEY: Optional[str] = None
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com/v1"
    DEEPSEEK_MODEL: str = "deepseek-chat"

    # Claude / Anthropic
    CLAUDE_API_KEY: Optional[str] = None
    CLAUDE_BASE_URL: str = "https://api.anthropic.com"
    CLAUDE_MODEL: str = "claude-opus-4-6"

    # 通义千问 (Qwen)
    QWEN_API_KEY: Optional[str] = None
    QWEN_BASE_URL: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    QWEN_MODEL: str = "qwen3-max"

    # 智谱 GLM
    ZHIPU_API_KEY: Optional[str] = None
    ZHIPU_BASE_URL: str = "https://open.bigmodel.cn/api/paas/v4"
    ZHIPU_MODEL: str = "glm-5"

    # 月之暗面 Kimi (Moonshot)
    MOONSHOT_API_KEY: Optional[str] = None
    MOONSHOT_BASE_URL: str = "https://api.moonshot.cn/v1"
    MOONSHOT_MODEL: str = "kimi-k2.5"

    # 豆包 (Doubao / ByteDance)
    DOUBAO_API_KEY: Optional[str] = None
    DOUBAO_BASE_URL: str = "https://ark.cn-beijing.volces.com/api/v3"
    DOUBAO_MODEL: str = "doubao-seed-1-8-251215"

    # Google Gemini
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_BASE_URL: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    GEMINI_MODEL: str = "gemini-3-flash-preview"

    # ========== 图片服务配置 ==========
    # Unsplash API (https://unsplash.com/developers)
    UNSPLASH_ACCESS_KEY: Optional[str] = None
    # 图片存储路径
    IMAGES_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "images",
    )

    # ========== Playwright 浏览器配置 ==========
    BROWSER_HEADLESS: bool = False  # 是否无头模式
    BROWSER_PROFILES_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "browser_profiles",
    )
    BROWSER_SLOW_MO: int = 50  # 浏览器操作延迟 (ms)
    BROWSER_TIMEOUT: int = 60000  # 浏览器超时 (ms)

    # ========== 发布控制配置 ==========
    DAILY_PUBLISH_LIMIT: int = 5  # 单账号每日发文上限
    MIN_PUBLISH_INTERVAL: int = 300  # 最小发布间隔（秒）
    ACTIVE_TIME_START: int = 8  # 活跃时间窗口开始（小时）
    ACTIVE_TIME_END: int = 23  # 活跃时间窗口结束（小时）
    MAX_RETRY_COUNT: int = 3  # 最大重试次数

    # ========== 截图保存路径 ==========
    SCREENSHOT_DIR: str = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "screenshots",
    )

    # ========== CORS 配置 ==========
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:5175",
        "http://localhost:5176",
        "http://localhost:5177",
        "http://localhost:5178",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:5175",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
        "http://127.0.0.1:5178",
    ]

    model_config = {
        "env_file": os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            ".env",
        ),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


# 全局配置单例
settings = Settings()
