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


def _has_usable_origin(origin: str | None, req: QueryRequest) -> bool:
    return bool(origin) or req.user_location is not None


def _origin_label(origin: str | None, req: QueryRequest) -> str:
    return origin or ("当前位置" if req.user_location else "")


def _route_needs_origin_message(destination: str | None = None) -> str:
    target = f"「{destination}」" if destination else "目的地"
    return f"已识别到目的地{target}，但还缺少明确起点。请补充起点，或开启/传入当前位置后再规划路线。"


def _route_needs_destination_message(origin: str | None = None) -> str:
    start = f"「{origin}」" if origin else "起点"
    return f"已识别到{start}，但还缺少明确目的地。请补充目的地后再规划路线。"


def _facility_search_keyword(req: QueryRequest, task) -> str | None:
    if task.destination:
        return task.destination

    if task.facility_type:
        return None

    return req.text


def _asks_open_now(text: str) -> bool:
    keywords = ["现在", "当前", "此刻", "还开", "开着", "营业中", "正在营业"]
    return any(keyword in text for keyword in keywords)


def _clean_query_text(text: str) -> str:
    cleaned = text.strip()
    if not cleaned:
        raise HTTPException(status_code=422, detail="查询内容不能为空")
    return cleaned


def _response_is_mock(route, facilities: list) -> bool:
    if route:
        return route.is_mock
    return not bool(facilities)


def _format_score(score: float | None) -> str:
    if score is None:
        return "待评估"

    try:
        value = float(score)
    except (TypeError, ValueError):
        return "待评估"

    if value != value:
        return "待评估"

    return f"{value:.0f}"


_GENERIC_GATE_KEYWORDS = ["最近校门", "学校大门", "校园大门", "校门", "大门"]
_SPECIFIC_GATE_KEYWORDS = ["北门", "南门", "东门", "西门", "西北门"]
_GENERIC_DORM_KEYWORDS = ["宿舍楼", "宿舍区", "宿舍", "寝室"]
_ROUTE_REQUEST_KEYWORDS = ["怎么走", "路线", "导航", "去", "到", "回", "疏散", "撤离"]
_NEAREST_KEYWORDS = ["最近", "离我近", "附近", "周边"]
_DEFAULT_FACILITY_NAMES = {
    FacilityType.dormitory: ["一组团四栋", "一组团一栋", "员工宿舍"],
    FacilityType.canteen: ["学二食堂一楼", "学一食堂一楼"],
    FacilityType.library: ["图书馆北门", "图书馆南门"],
}
_FACILITY_TYPE_LABELS = {
    FacilityType.dormitory: "宿舍",
    FacilityType.teaching_building: "教学楼",
    FacilityType.library: "图书馆",
    FacilityType.canteen: "食堂",
    FacilityType.store: "便利店",
    FacilityType.vending_machine: "自动售货机",
    FacilityType.playground: "操场",
    FacilityType.gate: "校门",
    FacilityType.other: "设施",
}


def _contains_any(text: str | None, keywords: list[str]) -> bool:
    return bool(text) and any(keyword in text for keyword in keywords)


def _asks_generic_gate(text: str, destination: str | None = None) -> bool:
    text_has_generic = _contains_any(text, _GENERIC_GATE_KEYWORDS) and not _contains_any(text, _SPECIFIC_GATE_KEYWORDS)
    destination_has_generic = (destination or "").strip() in _GENERIC_GATE_KEYWORDS
    return text_has_generic or destination_has_generic


def _route_facility_type(req: QueryRequest, task) -> FacilityType | None:
    if _asks_generic_gate(req.text, task.destination):
        return FacilityType.gate
    return task.facility_type


def _endpoint_facility_type(name: str | None, req: QueryRequest, fallback: FacilityType | None) -> FacilityType | None:
    if fallback:
        return fallback

    endpoint = (name or "").strip()
    text = req.text or ""
    if endpoint in _SPECIFIC_GATE_KEYWORDS and (
        "学校" in text or "校园" in text or "校门" in text or f"图书馆{endpoint}" not in text
    ):
        return FacilityType.gate

    return None


def _is_generic_dorm(name: str | None) -> bool:
    return (name or "").strip() in _GENERIC_DORM_KEYWORDS


def _facility_type_label(facility_type: FacilityType | None) -> str:
    if facility_type is None:
        return "设施"
    return _FACILITY_TYPE_LABELS.get(facility_type, "设施")


async def _default_facility_name(facility_type: FacilityType) -> str | None:
    items = await search_facilities(facility_type=facility_type, limit=100)
    if not items:
        return None

    preferred_names = _DEFAULT_FACILITY_NAMES.get(facility_type, [])
    for preferred in preferred_names:
        for item in items:
            if item.facility_name == preferred:
                return item.facility_name

    return items[0].facility_name


async def _facility_coordinate(name: str | None):
    if not name or name == "当前位置":
        return None

    items = await search_facilities(keyword=name, limit=20)
    for item in items:
        if item.coordinate and item.facility_name == name:
            return item.coordinate

    for item in items:
        if item.coordinate and (name in item.facility_name or item.facility_name in name):
            return item.coordinate

    return items[0].coordinate if items and items[0].coordinate else None


async def _route_related_facilities(
    origin: str | None,
    destination: str | None,
    req: QueryRequest,
    facility_type: FacilityType | None = None,
) -> list:
    facilities = []
    seen_ids = set()

    for endpoint in (origin, destination):
        if not endpoint or endpoint == "当前位置":
            continue

        endpoint_type = _endpoint_facility_type(endpoint, req, facility_type)
        matches = await search_facilities(
            keyword=endpoint,
            facility_type=endpoint_type,
            user_location=req.user_location,
            limit=20,
        )
        exact_matches = [item for item in matches if item.facility_name == endpoint]
        for item in (exact_matches or matches[:1]):
            if item.facility_id in seen_ids:
                continue
            seen_ids.add(item.facility_id)
            facilities.append(item)

    return facilities


async def _nearest_facility_name(
    facility_type: FacilityType,
    origin: str | None,
    req: QueryRequest,
) -> str | None:
    location = req.user_location or await _facility_coordinate(origin)
    items = await search_facilities(
        facility_type=facility_type,
        user_location=location,
        limit=20,
    )
    return items[0].facility_name if items else None


async def _infer_route_origin(origin: str | None, req: QueryRequest) -> str | None:
    if origin and not _is_generic_dorm(origin):
        return origin

    if req.user_location is not None and not origin:
        return "当前位置"

    if _is_generic_dorm(origin) or _contains_any(req.text, _GENERIC_DORM_KEYWORDS):
        return await _default_facility_name(FacilityType.dormitory) or origin

    if _contains_any(req.text, _ROUTE_REQUEST_KEYWORDS):
        return await _default_facility_name(FacilityType.dormitory)

    return origin


async def _resolve_route_destination(
    destination: str | None,
    origin: str | None,
    req: QueryRequest,
) -> str | None:
    if _asks_generic_gate(req.text, destination):
        return await _nearest_facility_name(FacilityType.gate, origin, req) or destination

    return destination


async def _facility_query_location(req: QueryRequest):
    if req.user_location is not None:
        return req.user_location

    if not _contains_any(req.text, _NEAREST_KEYWORDS):
        return None

    default_origin = await _default_facility_name(FacilityType.dormitory)
    return await _facility_coordinate(default_origin)


@router.post("", response_model=QueryResponse, summary="自然语言问答入口")
async def query(req: QueryRequest) -> QueryResponse:
    """
    接收用户自然语言问题，返回：
    - 解析后的任务结构（parsed_task）
    - 路径结果（route，如适用）
    - 相关设施列表（facilities）
    - 面向用户的文字说明（message）
    """
    req = req.model_copy(update={"text": _clean_query_text(req.text)})

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
            origin = await _infer_route_origin(task.origin, req)
            destination = await _resolve_route_destination(task.destination, origin, req)
            facility_type = _route_facility_type(req, task)
            task = task.model_copy(update={"origin": origin, "destination": destination, "facility_type": facility_type})
            if not destination:
                message = _route_needs_destination_message(origin)
            elif not _has_usable_origin(origin, req):
                message = _route_needs_origin_message(destination)
            else:
                route = await calc_night_safe_route(origin, destination, req.user_location)
                facilities = await _route_related_facilities(origin, destination, req, facility_type)
                score_text = _format_score(route.safety_score)
                message = f"已为您规划从「{origin}」到「{destination}」的夜间安全路径，全程约 {route.distance_m:.0f} 米，预计步行 {route.eta_min:.0f} 分钟，安全评分 {score_text}。"

        elif task.intent == IntentType.accessible_route:
            origin = await _infer_route_origin(task.origin, req)
            destination = await _resolve_route_destination(task.destination, origin, req)
            facility_type = _route_facility_type(req, task)
            task = task.model_copy(update={"origin": origin, "destination": destination, "facility_type": facility_type})
            if not destination:
                message = _route_needs_destination_message(origin)
            elif not _has_usable_origin(origin, req):
                message = _route_needs_origin_message(destination)
            else:
                route = await calc_accessible_route(origin, destination, req.user_location)
                facilities = await _route_related_facilities(origin, destination, req, facility_type)
                message = f"已为您规划从「{origin}」到「{destination}」的无障碍路径，全程避开台阶，约 {route.distance_m:.0f} 米。"

        elif task.intent == IntentType.evacuation_route:
            facilities = await get_evacuation_points(req.user_location)
            origin = await _infer_route_origin(task.origin, req)
            destination = await _resolve_route_destination(task.destination, origin, req)
            destination = destination or (facilities[0].facility_name if facilities else None)
            facility_type = _route_facility_type(req, task)
            task = task.model_copy(update={"origin": origin, "destination": destination, "facility_type": facility_type})
            if not destination:
                message = "暂未找到可用的安全集结点，请补充目的地或检查疏散点数据。"
            elif not _has_usable_origin(origin, req):
                message = _route_needs_origin_message(destination)
            else:
                route = await calc_evacuation_route(origin, destination, req.user_location)
                facilities = await _route_related_facilities(origin, destination, req, facility_type)
                message = f"⚠️ 应急撤离路径已规划！请立即沿推荐路线前往「{destination}」，预计 {route.eta_min:.0f} 分钟可达。"

        elif task.intent == IntentType.multi_stop_route:
            origin = task.origin
            destination = task.destination
            stops = task.stops or []
            if not origin:
                message = _route_needs_origin_message(destination)
            elif not destination:
                message = _route_needs_destination_message(origin)
            elif not stops:
                message = "已识别到多目标导航需求，但还缺少中途停靠点。请补充要途经的地点。"
            else:
                route = await calc_multistop_route(origin, stops, destination, task.time_constraint)
                facilities = await _route_related_facilities(origin, destination, req)
                stops_str = "→".join(stops)
                message = f"已为您规划多目标路径：{origin} → {stops_str} → {destination}，全程约 {route.distance_m:.0f} 米。"

        elif task.intent == IntentType.facility_query:
            open_now_requested = _asks_open_now(req.text)
            facility_location = await _facility_query_location(req)
            facilities = await search_facilities(
                keyword=_facility_search_keyword(req, task),
                facility_type=task.facility_type,
                night_available=True if task.priority_rule == "night_service" else None,
                open_now=True if open_now_requested else None,
                user_location=facility_location,
            )
            if facilities:
                names = "、".join(f.facility_name for f in facilities[:3])
                message = f"为您找到以下相关设施：{names}等，共 {len(facilities)} 处。"
            elif open_now_requested:
                facilities = await search_facilities(
                    keyword=_facility_search_keyword(req, task),
                    facility_type=task.facility_type,
                    night_available=True if task.priority_rule == "night_service" else None,
                    user_location=facility_location,
                )
                if facilities:
                    names = "、".join(f.facility_name for f in facilities[:3])
                    facility_label = _facility_type_label(task.facility_type)
                    message = f"当前没有正在营业的{facility_label}，先为您列出可选地点：{names}等，共 {len(facilities)} 处。"
                else:
                    message = "未找到符合条件的设施，请尝试更换关键词。"
            else:
                message = "未找到符合条件的设施，请尝试更换关键词。"

        elif task.intent == IntentType.navigation:
            origin = await _infer_route_origin(task.origin, req)
            destination = await _resolve_route_destination(task.destination or req.text, origin, req)
            facility_type = _route_facility_type(req, task)
            task = task.model_copy(update={"origin": origin, "destination": destination, "facility_type": facility_type})
            facilities = await search_facilities(
                keyword=destination,
                facility_type=facility_type,
                user_location=req.user_location,
            )
            if facilities:
                if not _has_usable_origin(origin, req):
                    message = f"已找到「{facilities[0].facility_name}」。如果需要导航，请补充起点或开启/传入当前位置。"
                else:
                    route = await calc_night_safe_route(
                        origin,
                        facilities[0].facility_name,
                        req.user_location,
                    )
                    message = f"已找到「{facilities[0].facility_name}」，为您规划从「{origin}」前往路线，约 {route.distance_m:.0f} 米。"
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
        route = None
        facilities = []
        message = "暂时无法生成路线，请检查起点和目的地是否在校园数据中，或稍后重试。"

    return QueryResponse(
        success=True,
        message=message,
        parsed_task=task,
        route=route,
        facilities=facilities,
        is_mock=_response_is_mock(route, facilities),
    )
