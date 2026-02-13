"""
Windows 兼容启动脚本

uvicorn --reload 在 Windows 上默认使用 SelectorEventLoop，
而 SelectorEventLoop 不支持 asyncio.create_subprocess_exec，
导致 Playwright 无法启动浏览器进程。

使用 loop="none" 让 uvicorn 跳过自定义事件循环工厂，
改用 Python 默认的 ProactorEventLoop（Windows 默认），
该循环支持子进程操作。
"""

import sys
import asyncio

# Windows 上确保使用 ProactorEventLoop（支持子进程）
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

import uvicorn  # noqa: E402

from app.config import settings  # noqa: E402

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        loop="none",
    )
