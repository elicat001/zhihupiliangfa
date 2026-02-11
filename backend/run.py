"""
Windows 兼容启动脚本

uvicorn --reload 在 Windows 上默认使用 SelectorEventLoop，
而 SelectorEventLoop 不支持 asyncio.create_subprocess_exec，
导致 Playwright 无法启动浏览器进程。

使用 loop="none" 让 uvicorn 跳过自定义事件循环工厂，
改用 Python 默认的 ProactorEventLoop（Windows 3.14 默认），
该循环支持子进程操作。
"""

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        reload=True,
        port=18900,
        loop="none",
    )
