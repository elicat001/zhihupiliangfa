"""
数据库连接管理
使用 aiosqlite + SQLAlchemy async 引擎
"""

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import settings

# 创建异步引擎（关闭 SQL echo，避免日志刷屏）
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,
    # SQLite 特有参数
    connect_args={"check_same_thread": False},
)

# 创建异步会话工厂
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncSession:
    """
    FastAPI 依赖注入：获取数据库会话
    使用 async with 确保会话正确关闭
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """
    初始化数据库：创建所有表
    在应用启动时调用
    """
    from app.models.base import Base  # noqa: F811

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """
    关闭数据库连接
    在应用关闭时调用
    """
    await engine.dispose()
