"""
/query 路由：自然语言问答统一入口。
接收用户文本 → LLM 解析意图 → 分发到对应 GIS/设施服务 → 返回统一响应。
"""
import logging
from fastapi import APIRouter, HTTPException

from app.models import (
    FacilityType,
    IntentType,
    QueryRequest,
    QueryResponse,
    RouteMode,
)
from app.services.llm import parse_user_query
from app.services.gis import (
    calc_night_safe_route,
    calc_accessible_route,
    calc_evacuation_route,
    calc_multistop_route,
)
from app.services.facility import search_facilities, get_evacuation_points

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/query", tags=["自然语言问答"])


@router.post("", response_model=QueryResponse, summary="自然语言问答入口")
async def query(req: QueryRequest) -> QueryResponse:
    """
    接收用户自然语言问题，返回：
    - 解析后的任务结构（parsed_task）
    - 路径结果（route，如适用）
    - 相关设施列表（facilities）
    - 面向用户的文字说明（message）
    """
    try:
        task = await parse_user_query(req.text)
    except Exception as e:
        logger.error(f"LLM 解析异常: {e}")
        raise HTTPException(status_code=500, detail="意图解析失败，请稍后重试")

    route = None
    facilities = []
    message = ""

    # -----------------------------------------------------------------------
    # 根据意图分发
    # -----------------------------------------------------------------------
    try:
        if task.intent == IntentType.night_safe_route:
            origin = task.origin or "当前位置"
            destination = task.destination or "目的地"
            route = await calc_night_safe_route(origin, destination, req.user_location)
            message = f"已为您规划从「{origin}」到「{destination}」的夜间安全路径，全程约 {route.distance_m:.0f} 米，预计步行 {route.eta_min:.0f} 分钟，安全评分 {route.safety_score}。"

        elif task.intent == IntentType.accessible_route:
            origin = task.origin or "当前位置"
            destination = task.destination or "目的地"
            route = await calc_accessible_route(origin, destination, req.user_location)
            message = f"已为您规划从「{origin}」到「{destination}」的无障碍路径，全程避开台阶，约 {route.distance_m:.0f} 米。"

        elif task.intent == IntentType.evacuation_route:
            origin = task.origin or "当前位置"
            destination = task.destination or "最近安全集结点"
            route = await calc_evacuation_route(origin, destination, req.user_location)
            facilities = await get_evacuation_points(req.user_location)
            message = f"⚠️ 应急撤离路径已规划！请立即沿推荐路线前往「{destination}」，预计 {route.eta_min:.0f} 分钟可达。"

        elif task.intent == IntentType.multi_stop_route:
            origin = task.origin or "当前位置"
            destination = task.destination or "宿舍"
            stops = task.stops or []
            route = await calc_multistop_route(origin, stops, destination, task.time_constraint)
            stops_str = "→".join(stops) if stops else "各途经点"
            message = f"已为您规划多目标路径：{origin} → {stops_str} → {destination}，全程约 {route.distance_m:.0f} 米。"

        elif task.intent == IntentType.facility_query:
            facilities = await search_facilities(
                keyword=req.text,
                facility_type=task.facility_type,
                night_available=True if task.priority_rule == "night_service" else None,
                user_location=req.user_location,
            )
            if facilities:
                names = "、".join(f.facility_name for f in facilities[:3])
                message = f"为您找到以下相关设施：{names}等，共 {len(facilities)} 处。"
            else:
                message = "未找到符合条件的设施，请尝试更换关键词。"

        elif task.intent == IntentType.navigation:
            destination = task.destination or req.text
            facilities = await search_facilities(
                keyword=destination,
                user_location=req.user_location,
            )
            if facilities:
                route = await calc_night_safe_route(
                    task.origin or "当前位置",
                    facilities[0].facility_name,
                    req.user_location,
                )
                message = f"已找到「{facilities[0].facility_name}」，为您规划前往路线，约 {route.distance_m:.0f} 米。"
            else:
                message = f"未能识别目的地「{destination}」，请尝试更准确的名称。"

        else:
            # unknown 意图：尝试关键词设施检索兜底
            facilities = await search_facilities(
                keyword=req.text,
                user_location=req.user_location,
                limit=5,
            )
            message = "已根据您的问题检索到相关信息，如需路径导航请描述出发地和目的地。"

    except Exception as e:
        logger.error(f"服务调用异常: {e}")
        raise HTTPException(status_code=500, detail="服务处理失败，请稍后重试")

    return QueryResponse(
        success=True,
        message=message,
        parsed_task=task,
        route=route,
        facilities=facilities,
        is_mock=route.is_mock if route else True,
    )
