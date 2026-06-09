"""
GIS 服务层：封装路径分析逻辑。
当前阶段返回 mock 数据；mdb 就绪后在此替换为 ArcPy Network Analyst 调用。

替换指引（mdb 就绪后）：
1. 将 config.py 中的 MDB_PATH 和 NETWORK_DATASET 填写为实际路径。
2. 在各函数中取消注释 ArcPy 调用代码块，删除 mock 返回语句。
3. arcpy.na 模块的调用示例已以注释形式保留在函数内。
"""
import copy
import logging
import math

from app.config import MDB_PATH, NETWORK_DATASET
from app.mock_data import MOCK_ROUTES
from app.models import (
    Coordinate,
    FacilityItem,
    RouteMode,
    RouteResult,
)

logger = logging.getLogger(__name__)

# ArcPy 导入（可选，不影响 mock 阶段运行）
try:
    import arcpy
    ARCPY_AVAILABLE = True
except ImportError:
    ARCPY_AVAILABLE = False
    logger.warning("arcpy 未找到，GIS 分析将使用 mock 数据")


# ---------------------------------------------------------------------------
# 内部工具函数
# ---------------------------------------------------------------------------

def _haversine(c1: Coordinate, c2: Coordinate) -> float:
    """计算两点间的球面距离（米）"""
    R = 6_371_000
    lat1, lat2 = math.radians(c1.lat), math.radians(c2.lat)
    dlat = math.radians(c2.lat - c1.lat)
    dlng = math.radians(c2.lng - c1.lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _nearest_facility(
    facilities: list[FacilityItem],
    user_loc: Coordinate,
) -> FacilityItem | None:
    """返回距用户位置最近的设施"""
    candidates = [f for f in facilities if f.coordinate]
    if not candidates:
        return None
    return min(candidates, key=lambda f: _haversine(f.coordinate, user_loc))


# ---------------------------------------------------------------------------
# 路径分析接口
# ---------------------------------------------------------------------------

async def calc_night_safe_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """
    夜间安全路径分析。
    cost = a * length + b * (max_score - night_score)
    """
    if ARCPY_AVAILABLE and MDB_PATH:
        # TODO: mdb 就绪后启用
        # arcpy.env.workspace = MDB_PATH
        # na_layer = arcpy.na.MakeRouteAnalysisLayer(NETWORK_DATASET, "NightRoute",
        #     impedance_attribute="night_cost")
        # arcpy.na.AddLocations(na_layer, "Stops", ...)
        # arcpy.na.Solve(na_layer)
        # return _extract_route_result(na_layer, RouteMode.night)
        pass

    result = copy.deepcopy(MOCK_ROUTES[RouteMode.night])
    result.origin = origin
    result.destination = destination
    return result


async def calc_accessible_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """
    无障碍通行路径分析。
    规则：台阶直接禁行，其余按 wheelchair_score 计算成本。
    cost = a * length + b * (max_score - wheelchair_score)
    """
    if ARCPY_AVAILABLE and MDB_PATH:
        # TODO: mdb 就绪后启用
        # arcpy.env.workspace = MDB_PATH
        # na_layer = arcpy.na.MakeRouteAnalysisLayer(NETWORK_DATASET, "AccessibleRoute",
        #     impedance_attribute="accessible_cost",
        #     restriction_attribute_names=["StairsRestriction"])
        # ...
        pass

    result = copy.deepcopy(MOCK_ROUTES[RouteMode.accessible])
    result.origin = origin
    result.destination = destination
    return result


async def calc_evacuation_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """
    应急撤离路径分析。
    两步法：先规则筛除死胡同/封闭/障碍路段，再按 evacuation_cost 最优。
    cost = a * length + b * (max_score - evacuation_score)
    """
    if ARCPY_AVAILABLE and MDB_PATH:
        # TODO: mdb 就绪后启用
        # arcpy.env.workspace = MDB_PATH
        # na_layer = arcpy.na.MakeClosestFacilityAnalysisLayer(
        #     NETWORK_DATASET, "EvacuationRoute",
        #     impedance_attribute="evacuation_cost",
        #     restriction_attribute_names=["ClosedRestriction", "NarrowRestriction"])
        # ...
        pass

    result = copy.deepcopy(MOCK_ROUTES[RouteMode.evacuation])
    result.origin = origin
    result.destination = destination
    return result


async def calc_multistop_route(
    origin: str,
    stops: list[str],
    destination: str,
    time_constraint: str | None = None,
) -> RouteResult:
    """
    多目标串联路径分析。
    步骤：
    1. 筛选满足营业时间和服务条件的候选停靠点
    2. 计算组合路径（TSP 近似）
    3. 返回总成本最优结果
    """
    if ARCPY_AVAILABLE and MDB_PATH:
        # TODO: mdb 就绪后启用
        # arcpy.env.workspace = MDB_PATH
        # na_layer = arcpy.na.MakeRouteAnalysisLayer(NETWORK_DATASET, "MultiStopRoute",
        #     impedance_attribute="night_cost",
        #     reorder_stops_to_find_optimal_route=True)
        # ...
        pass

    result = copy.deepcopy(MOCK_ROUTES[RouteMode.multi])
    result.origin = origin
    result.destination = destination
    # 将 stops 信息注入步骤说明
    if stops:
        result.steps[1].title = "、".join(stops)
    return result
