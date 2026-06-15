"""
FastAPI 应用入口。
启动命令：uvicorn app.main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGINS
from app.db import close_pool, init_pool
from app.routers import facility, map, query, route

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 生命周期：启动时初始化数据库连接池，关闭时释放
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        await init_pool()
        logger.info("数据库连接池启动成功")
    except Exception as e:
        logger.error(f"数据库连接池启动失败：{e}，部分功能将降级到 mock 数据")
    yield
    await close_pool()


app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    lifespan=lifespan,
    description="""
校园安全服务一体化智能导览系统后端 API。

## 功能模块
- **自然语言问答** `/query` — 输入自然语言，自动解析意图并返回路径或设施结果
- **路径分析** `/route-*` — 夜间安全 / 无障碍 / 应急撤离 / 多目标串联四类路径
- **设施检索** `/facility-search` — 多条件校园设施查询
""",
)

# ---------------------------------------------------------------------------
# CORS 配置（允许前端 Vite 开发服务器跨域访问）
# ---------------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------
app.include_router(query.router)
app.include_router(route.router)
app.include_router(facility.router)
app.include_router(map.router)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------
@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    from app.db import _pool
    db_status = "connected" if _pool else "disconnected"
    return {"status": "ok", "version": APP_VERSION, "db": db_status}
