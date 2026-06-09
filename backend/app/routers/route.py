"""
/route-* 路由：四类路径分析接口。
"""
import logging
from fastapi import APIRouter, Query as QParam

from app.models import (
    Coordinate,
    MultiStopRouteRequest,
    RouteRequest,
    RouteResult,
)
from app.services.gis import (
    calc_accessible_route,
    calc_evacuation_route,
    calc_multistop_route,
    calc_night_safe_route,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["路径分析"])


@router.get("/route-night-safe", response_model=RouteResult, summary="夜间安全路径")
async def route_night_safe(
    origin: str = QParam(..., description="出发地名称"),
    destination: str = QParam(..., description="目的地名称"),
    user_lng: float | None = QParam(None, description="用户当前经度"),
    user_lat: float | None = QParam(None, description="用户当前纬度"),
) -> RouteResult:
    """
    推荐照明更好、障碍更少、开敞度更高的夜间通行路径。
    cost = a × length + b × (max_score − night_score)
    """
    user_location = Coordinate(lng=user_lng, lat=user_lat) if user_lng and user_lat else None
    return await calc_night_safe_route(origin, destination, user_location)


@router.get("/route-accessible", response_model=RouteResult, summary="无障碍通行路径")
async def route_accessible(
    origin: str = QParam(..., description="出发地名称"),
    destination: str = QParam(..., description="目的地名称"),
    user_lng: float | None = QParam(None, description="用户当前经度"),
    user_lat: float | None = QParam(None, description="用户当前纬度"),
) -> RouteResult:
    """
    为轮椅或行动不便用户推荐可通行路线，台阶路段直接禁行。
    cost = a × length + b × (max_score − wheelchair_score)
    """
    user_location = Coordinate(lng=user_lng, lat=user_lat) if user_lng and user_lat else None
    return await calc_accessible_route(origin, destination, user_location)


@router.get("/route-evacuation", response_model=RouteResult, summary="应急撤离路径")
async def route_evacuation(
    origin: str = QParam(..., description="出发地名称"),
    destination: str = QParam("最近安全集结点", description="目的地，默认为最近操场或校门"),
    user_lng: float | None = QParam(None, description="用户当前经度"),
    user_lat: float | None = QParam(None, description="用户当前纬度"),
) -> RouteResult:
    """
    突发情况下快速撤离至操场、校门等安全集结点。
    两步法：规则筛除不可通行路段 → evacuation_cost 最优路径。
    """
    user_location = Coordinate(lng=user_lng, lat=user_lat) if user_lng and user_lat else None
    return await calc_evacuation_route(origin, destination, user_location)


@router.post("/route-multistop", response_model=RouteResult, summary="多目标串联路径")
async def route_multistop(req: MultiStopRouteRequest) -> RouteResult:
    """
    支持多目标串联路径规划，如：
    当前位置 → 食堂 → 便利店 → 宿舍

    系统会先筛选满足营业时间和服务条件的候选点，再计算组合路径最优解。
    """
    return await calc_multistop_route(
        req.origin,
        req.stops,
        req.destination,
        req.time_constraint,
    )
