"""
FastAPI 应用入口。
启动命令：uvicorn app.main:app --reload
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import APP_TITLE, APP_VERSION, CORS_ORIGINS
from app.routers import query, route, facility

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)

app = FastAPI(
    title=APP_TITLE,
    version=APP_VERSION,
    description="""
校园安全服务一体化智能导览系统后端 API。

## 功能模块
- **自然语言问答** `/query` — 输入自然语言，自动解析意图并返回路径或设施结果
- **路径分析** `/route-*` — 夜间安全 / 无障碍 / 应急撤离 / 多目标串联四类路径
- **设施检索** `/facility-search` — 多条件校园设施查询

## 当前状态
路径分析接口当前返回 mock 数据，mdb 数据库就绪后替换为 ArcPy 真实计算。
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


# ---------------------------------------------------------------------------
# 健康检查
# ---------------------------------------------------------------------------
@app.get("/health", tags=["系统"], summary="健康检查")
async def health():
    return {"status": "ok", "version": APP_VERSION}
