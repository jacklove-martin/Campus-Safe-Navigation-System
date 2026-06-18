"""
Admin routes for operational maintenance tasks.
"""
import logging

from fastapi import APIRouter

from app.services.gis import reload_graph_cache

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["系统管理"])


@router.post("/reload-graph", summary="刷新路网缓存")
async def reload_graph():
    loaded = await reload_graph_cache()
    logger.info("Graph cache reloaded: %s", loaded)
    return {
        "success": True,
        "loaded": loaded,
    }
