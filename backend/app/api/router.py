"""
API 路由聚合
将所有子路由挂载到统一的 /api 前缀下
"""

from fastapi import APIRouter

from app.api.articles import router as articles_router
from app.api.accounts import router as accounts_router
from app.api.tasks import router as tasks_router
from app.api.publish import router as publish_router
from app.api.stats import router as stats_router
from app.api.settings import router as settings_router
from app.api.templates import router as templates_router
from app.api.events import router as events_router
from app.api.notifications import router as notifications_router

# 主路由器，统一 /api 前缀
api_router = APIRouter(prefix="/api")

# 挂载各子路由（子路由自身已带 prefix，此处不再重复）
api_router.include_router(articles_router)
api_router.include_router(accounts_router)
api_router.include_router(tasks_router)
api_router.include_router(publish_router)
api_router.include_router(stats_router)
api_router.include_router(settings_router)
api_router.include_router(templates_router)
api_router.include_router(events_router)
api_router.include_router(notifications_router)
