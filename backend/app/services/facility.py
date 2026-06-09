"""
设施查询服务层。
当前阶段基于 mock_data 内存查询；mdb 就绪后替换为 ArcPy / SQLite 查询。
"""
import math
import logging

from app.mock_data import MOCK_FACILITIES
from app.models import Coordinate, FacilityItem, FacilityType

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 内部工具
# ---------------------------------------------------------------------------

def _haversine(c1: Coordinate, c2: Coordinate) -> float:
    """球面距离（米）"""
    R = 6_371_000
    lat1, lat2 = math.radians(c1.lat), math.radians(c2.lat)
    dlat = math.radians(c2.lat - c1.lat)
    dlng = math.radians(c2.lng - c1.lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _matches_keyword(facility: FacilityItem, keyword: str) -> bool:
    """判断设施是否匹配关键词（名称/别名/标签均参与匹配）"""
    keyword = keyword.strip().lower()
    fields = [
        facility.facility_name,
        facility.alias_names or "",
        facility.keyword_tags or "",
        facility.remark or "",
    ]
    return any(keyword in (f or "").lower() for f in fields)


# ---------------------------------------------------------------------------
# 查询接口
# ---------------------------------------------------------------------------

async def search_facilities(
    keyword: str | None = None,
    facility_type: FacilityType | None = None,
    night_available: bool | None = None,
    is_evacuation_point: bool | None = None,
    user_location: Coordinate | None = None,
    limit: int = 20,
) -> list[FacilityItem]:
    """
    多条件设施检索，返回结果按距离升序排列（有用户位置时）。

    mdb 就绪后替换说明：
    - 将 MOCK_FACILITIES 替换为 arcpy.SearchCursor 或 SQLite 查询结果
    - 字段名对应 campus_facilities 主表字段
    """
    results: list[FacilityItem] = []

    for f in MOCK_FACILITIES:
        # 类型筛选
        if facility_type and f.facility_type != facility_type:
            continue
        # 夜间可用筛选
        if night_available is not None and f.night_available != night_available:
            continue
        # 撤离点筛选
        if is_evacuation_point is not None and f.is_evacuation_point != is_evacuation_point:
            continue
        # 关键词筛选
        if keyword and not _matches_keyword(f, keyword):
            continue

        # 计算距离
        item = f.model_copy()
        if user_location and f.coordinate:
            item.distance_m = round(_haversine(user_location, f.coordinate), 1)

        results.append(item)

    # 有用户位置时按距离排序，否则按名称排序
    if user_location:
        results.sort(key=lambda x: x.distance_m if x.distance_m is not None else float("inf"))
    else:
        results.sort(key=lambda x: x.facility_name)

    return results[:limit]


async def get_facility_by_id(facility_id: str) -> FacilityItem | None:
    """按 ID 获取单个设施"""
    return next((f for f in MOCK_FACILITIES if f.facility_id == facility_id), None)


async def get_nearest_facility(
    facility_type: FacilityType,
    user_location: Coordinate,
    night_only: bool = False,
) -> FacilityItem | None:
    """
    获取距用户最近的指定类型设施。
    night_only=True 时仅考虑夜间可用的设施。
    """
    candidates = [
        f for f in MOCK_FACILITIES
        if f.facility_type == facility_type
        and f.coordinate
        and (not night_only or f.night_available)
    ]
    if not candidates:
        return None

    nearest = min(candidates, key=lambda f: _haversine(user_location, f.coordinate))
    nearest = nearest.model_copy()
    nearest.distance_m = round(_haversine(user_location, nearest.coordinate), 1)
    return nearest


async def get_evacuation_points(
    user_location: Coordinate | None = None,
) -> list[FacilityItem]:
    """获取所有撤离集结点，按距离排序"""
    return await search_facilities(
        is_evacuation_point=True,
        user_location=user_location,
    )
