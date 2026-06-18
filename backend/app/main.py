"""
FastAPI 应用入口。
启动命令：uvicorn app.main:app --reload
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGINS
from app.db import close_pool, init_pool
from app.models import ErrorResponse
from app.routers import admin, facility, map, query, route

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


def _error_content(error_code: str, message: str) -> dict:
    return ErrorResponse(error_code=error_code, message=message).model_dump()


def _http_error_code(status_code: int) -> str:
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 422:
        return "INVALID_PARAMS"
    return "HTTP_ERROR"


@app.middleware("http")
async def request_log_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = None
    try:
        response = await call_next(request)
        return response
    finally:
        elapsed_ms = round((time.perf_counter() - start) * 1000)
        query = f"?{request.url.query}" if request.url.query else ""
        status_code = response.status_code if response else 500
        logger.info("%s %s%s %s %sms", request.method, request.url.path, query, status_code, elapsed_ms)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    detail = exc.detail if isinstance(exc.detail, str) else str(exc.detail)
    return JSONResponse(
        status_code=exc.status_code,
        content=_error_content(_http_error_code(exc.status_code), detail),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning("Request validation failed: %s", exc)
    return JSONResponse(
        status_code=422,
        content=_error_content("INVALID_PARAMS", "参数格式错误，请检查输入内容。"),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    message = str(exc) or "请求无法处理，请检查输入内容。"
    error_code = "POI_NOT_FOUND" if "坐标" in message or "地名" in message else "ROUTE_NOT_FOUND"
    return JSONResponse(
        status_code=400,
        content=_error_content(error_code, message),
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled request error: %s", exc)
    return JSONResponse(
        status_code=500,
        content=_error_content("INTERNAL_ERROR", "服务暂时不可用，请稍后重试。"),
    )

# ---------------------------------------------------------------------------
# 注册路由
# ---------------------------------------------------------------------------
app.include_router(query.router)
app.include_router(route.router)
app.include_router(facility.router)
app.include_router(map.router)
app.include_router(admin.router)


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------
@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    from app.db import _pool
    from app.services.gis import graph_cache_status

    db_status = "connected" if _pool else "disconnected"
    poi_count = None
    road_segment_count = None

    if _pool:
        try:
            async with _pool.acquire() as conn:
                poi_count = await conn.fetchval("SELECT COUNT(*) FROM nav.poi")
                road_segment_count = await conn.fetchval("SELECT COUNT(*) FROM nav.road_segment")
        except Exception as exc:
            db_status = "error"
            logger.warning("Health check DB query failed: %s", exc)

    return {
        "status": "ok",
        "version": APP_VERSION,
        "db": db_status,
        "poi_count": poi_count,
        "road_segment_count": road_segment_count,
        "graph_loaded": graph_cache_status(),
    }
