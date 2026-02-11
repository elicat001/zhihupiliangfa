"""
FastAPI 应用主入口
负责应用初始化、CORS 配置、启动/关闭生命周期管理
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database.connection import init_db, close_db
from app.api.router import api_router
from app.core.task_scheduler import task_scheduler
from app.automation.browser_manager import browser_manager

# ========== 日志配置 ==========
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# 静默高频噪音日志
logging.getLogger("aiosqlite").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("apscheduler.scheduler").setLevel(logging.WARNING)
logging.getLogger("apscheduler.executors.default").setLevel(logging.WARNING)


# ========== 生命周期管理 ==========
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    启动时：初始化数据库、启动任务调度器
    关闭时：关闭调度器、关闭浏览器、关闭数据库连接
    """
    # ---- 启动 ----
    logger.info(f"正在启动 {settings.APP_NAME} v{settings.APP_VERSION}...")

    # 确保数据目录存在
    os.makedirs(os.path.dirname(settings.DATABASE_PATH), exist_ok=True)
    os.makedirs(settings.SCREENSHOT_DIR, exist_ok=True)
    os.makedirs(settings.BROWSER_PROFILES_DIR, exist_ok=True)

    # 初始化数据库
    await init_db()
    logger.info("数据库初始化完成")

    # 启动任务调度器
    task_scheduler.start()
    logger.info("任务调度器已启动")

    logger.info(
        f"应用启动完成，监听 http://{settings.HOST}:{settings.PORT}"
    )
    logger.info(f"API 文档: http://127.0.0.1:{settings.PORT}/docs")

    yield

    # ---- 关闭 ----
    logger.info("正在关闭应用...")

    # 关闭任务调度器
    task_scheduler.shutdown()

    # 关闭浏览器管理器
    await browser_manager.close_all()

    # 关闭数据库连接
    await close_db()

    logger.info("应用已关闭")


# ========== 创建 FastAPI 应用 ==========
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="知乎自动发文系统 - AI 生成文章、多账号管理、自动化发布",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# ========== CORS 中间件 ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 挂载静态文件（截图目录） ==========
if os.path.exists(settings.SCREENSHOT_DIR):
    app.mount(
        "/screenshots",
        StaticFiles(directory=settings.SCREENSHOT_DIR),
        name="screenshots",
    )

# ========== 注册路由 ==========
app.include_router(api_router)


# ========== 根路径 ==========
@app.get("/", tags=["系统"])
async def root():
    """系统信息"""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["系统"])
async def health_check():
    """健康检查"""
    return {"status": "ok"}


# ========== 直接运行入口 ==========
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        loop="none",
    )
