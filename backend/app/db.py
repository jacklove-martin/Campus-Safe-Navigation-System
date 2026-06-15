"""
数据库连接池管理。
使用 asyncpg 异步连接 PostgreSQL，在 FastAPI 生命周期中创建和关闭连接池。
"""
import logging
import asyncpg

from app.config import DB_DSN

logger = logging.getLogger(__name__)

# 全局连接池
_pool: asyncpg.Pool | None = None


async def init_pool() -> None:
    """创建数据库连接池，在应用启动时调用。"""
    global _pool
    try:
        _pool = await asyncpg.create_pool(
            dsn=DB_DSN,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
        logger.info("数据库连接池初始化成功")
    except Exception as e:
        logger.error(f"数据库连接池初始化失败：{e}")
        raise


async def close_pool() -> None:
    """关闭数据库连接池，在应用关闭时调用。"""
    global _pool
    if _pool:
        await _pool.close()
        logger.info("数据库连接池已关闭")


def get_pool() -> asyncpg.Pool:
    """获取连接池，供 service 层调用。"""
    if _pool is None:
        raise RuntimeError("数据库连接池未初始化，请检查数据库配置")
    return _pool
