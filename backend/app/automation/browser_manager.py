"""
Playwright 浏览器管理器
管理浏览器实例池，支持持久化上下文和反检测配置
"""

import os
import asyncio
import logging
from typing import Optional

from playwright.async_api import (
    async_playwright,
    Playwright,
    Browser,
    BrowserContext,
    Page,
)

from app.config import settings
from app.automation.anti_detect import get_stealth_script

logger = logging.getLogger(__name__)


class BrowserManager:
    """
    浏览器管理器
    - 管理 Playwright 浏览器实例的生命周期
    - 支持持久化上下文（保存登录态）
    - 注入反检测脚本
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        # 持久化上下文缓存 {profile_name: BrowserContext}
        self._contexts: dict[str, BrowserContext] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def initialize(self):
        """
        初始化 Playwright 和浏览器实例
        只在第一次调用时创建
        """
        if self._initialized:
            return

        async with self._lock:
            if self._initialized:
                return

            logger.info("正在初始化 Playwright...")
            try:
                self._playwright = await async_playwright().start()

                # 启动 Chromium 浏览器
                self._browser = await self._playwright.chromium.launch(
                    headless=settings.BROWSER_HEADLESS,
                    slow_mo=settings.BROWSER_SLOW_MO,
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-web-security",
                        "--lang=zh-CN,zh",
                    ],
                )

                self._initialized = True
                logger.info("Playwright 初始化完成")
            except Exception:
                logger.error("Playwright 初始化失败，正在清理...")
                if self._browser:
                    try:
                        await self._browser.close()
                    except Exception:
                        pass
                    self._browser = None
                if self._playwright:
                    try:
                        await self._playwright.stop()
                    except Exception:
                        pass
                    self._playwright = None
                raise

    async def get_persistent_context(
        self, profile_name: str
    ) -> BrowserContext:
        """
        获取持久化浏览器上下文
        持久化上下文会保存 Cookie、localStorage 等状态

        Args:
            profile_name: 浏览器配置文件名称（目录名）

        Returns:
            BrowserContext: 浏览器上下文
        """
        if profile_name in self._contexts:
            return self._contexts[profile_name]

        await self.initialize()

        profile_dir = os.path.join(settings.BROWSER_PROFILES_DIR, profile_name)
        os.makedirs(profile_dir, exist_ok=True)

        logger.info(f"创建持久化上下文: {profile_name}")

        context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=settings.BROWSER_HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
                "--no-sandbox",
                "--lang=zh-CN,zh",
            ],
        )

        # 注入反检测脚本到每个新页面
        await context.add_init_script(get_stealth_script())

        self._contexts[profile_name] = context
        return context

    async def create_temp_context(self) -> BrowserContext:
        """
        创建临时浏览器上下文（不持久化）
        用于一次性操作，如扫码登录获取二维码

        Returns:
            BrowserContext: 临时浏览器上下文
        """
        await self.initialize()

        context = await self._browser.new_context(
            viewport={"width": 1280, "height": 720},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            locale="zh-CN",
            timezone_id="Asia/Shanghai",
        )

        # 注入反检测脚本
        await context.add_init_script(get_stealth_script())

        return context

    async def new_page(self, context: BrowserContext) -> Page:
        """
        在指定上下文中打开新页面

        Args:
            context: 浏览器上下文

        Returns:
            Page: 新页面
        """
        page = await context.new_page()
        page.set_default_timeout(settings.BROWSER_TIMEOUT)
        return page

    async def close_context(self, profile_name: str):
        """
        关闭并移除指定的持久化上下文

        Args:
            profile_name: 配置文件名称
        """
        context = self._contexts.pop(profile_name, None)
        if context:
            logger.info(f"关闭持久化上下文: {profile_name}")
            await context.close()

    async def close_all(self):
        """关闭所有浏览器实例和上下文"""
        logger.info("正在关闭所有浏览器资源...")

        # 关闭所有持久化上下文
        for name, ctx in list(self._contexts.items()):
            try:
                await ctx.close()
                logger.info(f"已关闭上下文: {name}")
            except Exception as e:
                logger.error(f"关闭上下文 {name} 失败: {e}")
        self._contexts.clear()

        # 关闭浏览器
        if self._browser:
            try:
                await self._browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器失败: {e}")
            self._browser = None

        # 关闭 Playwright
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.error(f"关闭 Playwright 失败: {e}")
            self._playwright = None

        self._initialized = False
        logger.info("所有浏览器资源已关闭")


# 全局浏览器管理器单例
browser_manager = BrowserManager()
