"""
设施查询服务层。
直接查询 PostgreSQL nav.poi 表，支持关键词、类型、夜间可用、撤离点、距离等多条件筛选。
"""
import math
import logging

from app.db import get_pool
from app.models import Coordinate, FacilityItem, FacilityType

logger = logging.getLogger(__name__)

# 数据库 category 值与枚举的映射（数据库用 landmark，模型用 other）
_CATEGORY_MAP = {
    "dormitory": FacilityType.dormitory,
    "teaching_building": FacilityType.teaching_building,
    "library": FacilityType.library,
    "canteen": FacilityType.canteen,
    "store": FacilityType.store,
    "vending_machine": FacilityType.vending_machine,
    "playground": FacilityType.playground,
    "gate": FacilityType.gate,
    "landmark": FacilityType.other,
    "other": FacilityType.other,
}

# 撤离集结点类型
_EVACUATION_CATEGORIES = {"playground", "gate"}


def _haversine(c1: Coordinate, c2: Coordinate) -> float:
    """球面距离（米）"""
    R = 6_371_000
    lat1, lat2 = math.radians(c1.lat), math.radians(c2.lat)
    dlat = math.radians(c2.lat - c1.lat)
    dlng = math.radians(c2.lng - c1.lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _row_to_facility(row: dict) -> FacilityItem:
    """将数据库行转换为 FacilityItem。"""
    category = row.get("category", "other")
    facility_type = _CATEGORY_MAP.get(category, FacilityType.other)
    is_evacuation = category in _EVACUATION_CATEGORIES

    # 坐标从 WKB 十六进制解析（asyncpg 返回 Point 对象）
    coord = None
    geom = row.get("geom")
    if geom:
        try:
            # asyncpg + PostGIS 返回字符串形式 "POINT(lng lat)"
            if isinstance(geom, str) and geom.startswith("POINT"):
                parts = geom.replace("POINT(", "").replace(")", "").split()
                coord = Coordinate(lng=float(parts[0]), lat=float(parts[1]))
        except Exception:
            pass

    # keywords 是 PostgreSQL text[] 数组
    keywords = row.get("keywords") or []
    keyword_tags = ",".join(keywords) if keywords else None

    return FacilityItem(
        facility_id=str(row["poi_id"]),
        facility_name=row.get("name") or "",
        facility_type=facility_type,
        alias_names=None,
        open_time=str(row["open_time"]) if row.get("open_time") else None,
        close_time=str(row["close_time"]) if row.get("close_time") else None,
        night_available=bool(row.get("night_available", False)),
        is_evacuation_point=is_evacuation,
        remark=row.get("remark"),
        keyword_tags=keyword_tags,
        coordinate=coord,
        distance_m=None,
    )


async def search_facilities(
    keyword: str | None = None,
    facility_type: FacilityType | None = None,
    night_available: bool | None = None,
    is_evacuation_point: bool | None = None,
    user_location: Coordinate | None = None,
    limit: int = 20,
) -> list[FacilityItem]:
    """多条件设施检索，结果按距离排序（有用户位置时）。"""
    pool = get_pool()

    # 动态构建 WHERE 子句
    conditions = []
    params: list = []
    idx = 1

    if facility_type:
        # other 对应数据库中的 landmark
        db_category = "landmark" if facility_type == FacilityType.other else facility_type.value
        conditions.append(f"category = ${idx}")
        params.append(db_category)
        idx += 1

    if night_available is not None:
        conditions.append(f"night_available = ${idx}")
        params.append(night_available)
        idx += 1

    if is_evacuation_point is True:
        conditions.append("category = ANY($" + str(idx) + ")")
        params.append(["playground", "gate"])
        idx += 1
    elif is_evacuation_point is False:
        conditions.append("category != ALL($" + str(idx) + ")")
        params.append(["playground", "gate"])
        idx += 1

    if keyword:
        kw = f"%{keyword.strip()}%"
        conditions.append(
            f"(name ILIKE ${idx} OR service_content ILIKE ${idx} "
            f"OR remark ILIKE ${idx} OR ${idx} ILIKE ANY(keywords::text[]))"
        )
        params.append(kw)
        idx += 1

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

    sql = f"""
        SELECT
            poi_id, name, category, type,
            night_available, open_time, close_time,
            service_content, remark, keywords,
            ST_AsText(geom) AS geom
        FROM nav.poi
        {where}
        LIMIT {limit * 3}
    """

    async with pool.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    items = [_row_to_facility(dict(row)) for row in rows]

    # 计算距离并排序
    if user_location:
        for item in items:
            if item.coordinate:
                item.distance_m = round(_haversine(user_location, item.coordinate), 1)
        items.sort(key=lambda x: x.distance_m if x.distance_m is not None else float("inf"))
    else:
        items.sort(key=lambda x: x.facility_name)

    return items[:limit]


async def get_facility_by_id(facility_id: str) -> FacilityItem | None:
    """按 ID 获取单个设施。"""
    pool = get_pool()
    sql = """
        SELECT
            poi_id, name, category, type,
            night_available, open_time, close_time,
            service_content, remark, keywords,
            ST_AsText(geom) AS geom
        FROM nav.poi
        WHERE poi_id = $1
    """
    async with pool.acquire() as conn:
        row = await conn.fetchrow(sql, int(facility_id))
    if not row:
        return None
    return _row_to_facility(dict(row))


async def get_nearest_facility(
    facility_type: FacilityType,
    user_location: Coordinate,
    night_only: bool = False,
) -> FacilityItem | None:
    """获取距用户最近的指定类型设施。"""
    items = await search_facilities(
        facility_type=facility_type,
        night_available=True if night_only else None,
        user_location=user_location,
        limit=1,
    )
    return items[0] if items else None


async def get_evacuation_points(
    user_location: Coordinate | None = None,
) -> list[FacilityItem]:
    """获取所有撤离集结点，按距离排序。"""
    return await search_facilities(
        is_evacuation_point=True,
        user_location=user_location,
    )
