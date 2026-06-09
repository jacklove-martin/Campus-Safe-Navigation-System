"""
/facility-search 路由：设施检索接口。
"""
import logging
from fastapi import APIRouter, Query as QParam

from app.models import (
    Coordinate,
    FacilityItem,
    FacilitySearchRequest,
    FacilitySearchResponse,
    FacilityType,
)
from app.services.facility import (
    get_evacuation_points,
    get_facility_by_id,
    search_facilities,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/facility-search", tags=["设施检索"])


@router.get("", response_model=FacilitySearchResponse, summary="设施检索")
async def facility_search(
    keyword: str | None = QParam(None, description="关键词：名称/别名/标签均参与匹配"),
    facility_type: FacilityType | None = QParam(None, description="设施类型筛选"),
    night_available: bool | None = QParam(None, description="是否夜间可用"),
    is_evacuation_point: bool | None = QParam(None, description="是否为撤离集结点"),
    user_lng: float | None = QParam(None, description="用户当前经度，提供后按距离排序"),
    user_lat: float | None = QParam(None, description="用户当前纬度"),
    limit: int = QParam(20, ge=1, le=100, description="返回数量上限"),
) -> FacilitySearchResponse:
    """
    多条件设施检索。

    支持的查询条件：
    - 是否营业（night_available）
    - 是否为特定类型（facility_type）
    - 是否夜间可用
    - 是否为撤离集结点
    - 距离当前位置最近（提供经纬度后自动排序）
    - 关键词模糊匹配（名称/别名/标签/备注）
    """
    user_location = Coordinate(lng=user_lng, lat=user_lat) if user_lng and user_lat else None

    items = await search_facilities(
        keyword=keyword,
        facility_type=facility_type,
        night_available=night_available,
        is_evacuation_point=is_evacuation_point,
        user_location=user_location,
        limit=limit,
    )

    return FacilitySearchResponse(
        success=True,
        total=len(items),
        items=items,
    )


@router.get("/evacuation-points", response_model=FacilitySearchResponse, summary="获取所有撤离集结点")
async def evacuation_points(
    user_lng: float | None = QParam(None, description="用户当前经度"),
    user_lat: float | None = QParam(None, description="用户当前纬度"),
) -> FacilitySearchResponse:
    """返回所有操场、校门等应急撤离集结点，按距离排序。"""
    user_location = Coordinate(lng=user_lng, lat=user_lat) if user_lng and user_lat else None
    items = await get_evacuation_points(user_location)
    return FacilitySearchResponse(success=True, total=len(items), items=items)


@router.get("/{facility_id}", response_model=FacilityItem, summary="按 ID 获取设施详情")
async def get_facility(facility_id: str) -> FacilityItem:
    """按设施 ID 获取详细信息。"""
    item = await get_facility_by_id(facility_id)
    if not item:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"设施 {facility_id} 不存在")
    return item
