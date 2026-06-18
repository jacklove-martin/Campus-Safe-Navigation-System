"""
GIS 服务层：基于 networkx 的路径规划。
从 PostgreSQL nav.road_segment + nav.road_node 读取路网，
在内存中构建加权有向图，用 Dijkstra 算法求最优路径。

成本函数：
  夜间安全：cost = length_m + (10 - lighting_score) * 30
  无障碍：  cost = length_m + (10 - barrier_free_score) * 40  （台阶路段权重极大）
  应急撤离：cost = length_m + (10 - emergency_evacuation_score) * 25
"""
import logging
import math
import re
import time
from itertools import permutations
from typing import Any

import networkx as nx

from app.db import get_pool
from app.models import Coordinate, RouteMode, RouteResult, RouteStep

logger = logging.getLogger(__name__)

# 路网图缓存（进程内，首次请求时加载）
_graph_cache: dict[str, nx.DiGraph] = {}
_ROUTE_CACHE_TTL_SECONDS = 300
_ROUTE_CACHE_MAX_SIZE = 200
_route_cache: dict[tuple, tuple[float, RouteResult]] = {}


def _user_location_cache_key(user_location: Coordinate | None) -> tuple[float, float] | None:
    if not user_location:
        return None
    return (round(user_location.lng, 7), round(user_location.lat, 7))


def _route_cache_key(
    mode: RouteMode,
    origin: str,
    destination: str,
    user_location: Coordinate | None,
) -> tuple:
    return (mode.value, origin, destination, _user_location_cache_key(user_location))


def _get_cached_route(key: tuple) -> RouteResult | None:
    cached = _route_cache.get(key)
    if not cached:
        return None

    expires_at, result = cached
    if expires_at <= time.monotonic():
        _route_cache.pop(key, None)
        return None

    return result.model_copy(deep=True)


def _set_cached_route(key: tuple, result: RouteResult) -> None:
    if len(_route_cache) >= _ROUTE_CACHE_MAX_SIZE:
        _route_cache.pop(next(iter(_route_cache)))

    _route_cache[key] = (
        time.monotonic() + _ROUTE_CACHE_TTL_SECONDS,
        result.model_copy(deep=True),
    )


async def reload_graph_cache() -> dict[str, dict[str, int]]:
    """Clear route graph cache and eagerly reload supported routing modes."""
    _graph_cache.clear()
    _route_cache.clear()
    loaded: dict[str, dict[str, int]] = {}

    for mode in (RouteMode.night, RouteMode.accessible, RouteMode.evacuation):
        graph = await _load_graph(mode)
        loaded[mode.value] = {
            "nodes": graph.number_of_nodes(),
            "edges": graph.number_of_edges(),
        }

    return loaded


def graph_cache_status() -> dict[str, bool]:
    return {
        mode.value: mode.value in _graph_cache
        for mode in (RouteMode.night, RouteMode.accessible, RouteMode.evacuation)
    }


# ---------------------------------------------------------------------------
# 路网加载
# ---------------------------------------------------------------------------

async def _load_graph(mode: RouteMode) -> nx.DiGraph:
    """从数据库加载路网并构建加权有向图，结果缓存在内存中。"""
    cache_key = mode.value
    if cache_key in _graph_cache:
        return _graph_cache[cache_key]

    pool = get_pool()
    sql = """
        SELECT
            road_id,
            source_node,
            target_node,
            length_m,
            lighting_score,
            barrier_free_score,
            flatness_score,
            emergency_evacuation_score,
            width_score,
            ST_AsText(geom) AS geom
        FROM nav.road_segment
        WHERE source_node IS NOT NULL AND target_node IS NOT NULL
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    G = nx.DiGraph()

    for row in rows:
        r = dict(row)
        src = r["source_node"]
        tgt = r["target_node"]
        length = float(r["length_m"] or 10)
        lighting = float(r["lighting_score"] or 5)
        barrier_free = float(r["barrier_free_score"] or 5)
        flatness = float(r["flatness_score"] or 5)
        evacuation = float(r["emergency_evacuation_score"] or 5)
        width = float(r["width_score"] or 5)

        # 根据模式计算边权重
        if mode == RouteMode.night:
            weight = length + (10 - lighting) * 30
        elif mode == RouteMode.accessible:
            # 无障碍评分过低的路段设极大权重（相当于禁行）
            if barrier_free < 2:
                weight = 999_999
            else:
                weight = length + (10 - barrier_free) * 40
        elif mode == RouteMode.evacuation:
            weight = length + (10 - evacuation) * 25
        else:
            weight = length

        edge_data = {
            "weight": weight,
            "length_m": length,
            "road_id": r["road_id"],
            "geom": r.get("geom"),
            "lighting_score": lighting,
            "barrier_free_score": barrier_free,
            "flatness_score": flatness,
            "emergency_evacuation_score": evacuation,
            "width_score": width,
        }
        # 双向路段
        G.add_edge(src, tgt, **edge_data)
        G.add_edge(tgt, src, **edge_data)

    _graph_cache[cache_key] = G
    logger.info(f"路网图加载完成 [{mode.value}]：{G.number_of_nodes()} 节点，{G.number_of_edges()} 边")
    return G


async def _load_nodes() -> dict[int, Coordinate]:
    """加载路网节点坐标。"""
    pool = get_pool()
    sql = "SELECT node_id, ST_AsText(geom) AS geom FROM nav.road_node"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    nodes: dict[int, Coordinate] = {}
    for row in rows:
        geom = row["geom"]
        if geom and geom.startswith("POINT"):
            parts = geom.replace("POINT(", "").replace(")", "").split()
            nodes[row["node_id"]] = Coordinate(lng=float(parts[0]), lat=float(parts[1]))
    return nodes


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def _haversine(c1: Coordinate, c2: Coordinate) -> float:
    R = 6_371_000
    lat1, lat2 = math.radians(c1.lat), math.radians(c2.lat)
    dlat = math.radians(c2.lat - c1.lat)
    dlng = math.radians(c2.lng - c1.lng)
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _nearest_node(
    nodes: dict[int, Coordinate],
    target: Coordinate,
) -> int:
    """找到距目标坐标最近的路网节点 ID。"""
    return min(nodes.keys(), key=lambda nid: _haversine(nodes[nid], target))


def _find_poi_coord(name: str, pois: list[dict]) -> Coordinate | None:
    """按名称匹配 POI 坐标，优先精确匹配，避免“南门”误命中“图书馆南门”。"""
    target = (name or "").strip()
    if not target:
        return None

    for poi in pois:
        if (poi.get("name") or "").strip() == target:
            geom = poi.get("geom", "")
            if geom and geom.startswith("POINT"):
                parts = geom.replace("POINT(", "").replace(")", "").split()
                return Coordinate(lng=float(parts[0]), lat=float(parts[1]))

    for poi in pois:
        if target in (poi.get("name") or ""):
            geom = poi.get("geom", "")
            if geom and geom.startswith("POINT"):
                parts = geom.replace("POINT(", "").replace(")", "").split()
                return Coordinate(lng=float(parts[0]), lat=float(parts[1]))
    return None


async def _load_pois() -> list[dict]:
    """加载全部 POI 供名称解析使用。"""
    pool = get_pool()
    sql = "SELECT poi_id, name, category, ST_AsText(geom) AS geom FROM nav.poi"
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)
    return [dict(r) for r in rows]


def _parse_wkt_line_coords(geom: str | None) -> list[list[float]]:
    """从 PostGIS WKT 中提取 LineString 坐标，忽略 Z/M 维度。"""
    if not geom:
        return []

    wkt = geom.strip()
    if not wkt:
        return []

    if wkt.upper().startswith("SRID=") and ";" in wkt:
        wkt = wkt.split(";", 1)[1].strip()

    def parse_line_body(body: str) -> list[list[float]]:
        coords = []
        for pair in body.split(","):
            parts = pair.strip().split()
            if len(parts) < 2:
                continue
            try:
                coords.append([float(parts[0]), float(parts[1])])
            except ValueError:
                continue
        return coords

    upper = wkt.upper()
    if upper.startswith("LINESTRING"):
        body = wkt[wkt.find("(") + 1:wkt.rfind(")")]
        return parse_line_body(body)

    if upper.startswith("MULTILINESTRING"):
        inner = wkt[wkt.find("(") + 1:wkt.rfind(")")]
        coords: list[list[float]] = []
        for line_body in re.findall(r"\(([^()]+)\)", inner):
            _append_line_coords(coords, parse_line_body(line_body))
        return coords

    return []


def _coord_distance(point: list[float], coord: Coordinate) -> float:
    return math.hypot(point[0] - coord.lng, point[1] - coord.lat)


def _same_coord(a: list[float], b: list[float], tolerance: float = 1e-9) -> bool:
    return abs(a[0] - b[0]) <= tolerance and abs(a[1] - b[1]) <= tolerance


def _append_line_coords(target: list[list[float]], coords: list[list[float]]) -> None:
    if not coords:
        return

    if target and _same_coord(target[-1], coords[0]):
        target.extend(coords[1:])
        return

    target.extend(coords)


def _orient_edge_coords(
    coords: list[list[float]],
    source_coord: Coordinate,
    target_coord: Coordinate,
) -> list[list[float]]:
    """按当前行进方向排列路段折线。"""
    if len(coords) < 2:
        return coords

    forward_cost = _coord_distance(coords[0], source_coord) + _coord_distance(coords[-1], target_coord)
    backward_cost = _coord_distance(coords[-1], source_coord) + _coord_distance(coords[0], target_coord)

    if backward_cost < forward_cost:
        return list(reversed(coords))

    return coords


def _edge_geometry_coords(
    G: nx.DiGraph,
    nodes: dict[int, Coordinate],
    source_node: int,
    target_node: int,
) -> list[list[float]]:
    """优先使用 road_segment.geom，缺失时才退回节点直连。"""
    source_coord = nodes.get(source_node)
    target_coord = nodes.get(target_node)
    data = G.get_edge_data(source_node, target_node) or {}

    coords = _parse_wkt_line_coords(data.get("geom"))
    if coords and source_coord and target_coord:
        return _orient_edge_coords(coords, source_coord, target_coord)

    if source_coord and target_coord:
        return [[source_coord.lng, source_coord.lat], [target_coord.lng, target_coord.lat]]

    return []


def _path_coordinates(path_nodes: list[int], nodes: dict[int, Coordinate], G: nx.DiGraph) -> list[list[float]]:
    """将路径节点序列拼接为贴合路段几何的坐标序列。"""
    coords: list[list[float]] = []

    for i in range(len(path_nodes) - 1):
        segment_coords = _edge_geometry_coords(G, nodes, path_nodes[i], path_nodes[i + 1])
        _append_line_coords(coords, segment_coords)

    if not coords and len(path_nodes) == 1 and path_nodes[0] in nodes:
        c = nodes[path_nodes[0]]
        coords.append([c.lng, c.lat])

    return coords


def _path_to_geojson(path_nodes: list[int], nodes: dict[int, Coordinate], G: nx.DiGraph) -> dict[str, Any]:
    """将节点 ID 序列转换为 GeoJSON LineString。"""
    coords = _path_coordinates(path_nodes, nodes, G)
    return {
        "type": "Feature",
        "geometry": {"type": "LineString", "coordinates": coords},
        "properties": {},
    }


def _path_length(path_nodes: list[int], G: nx.DiGraph) -> float:
    """计算路径总长度（米）。"""
    total = 0.0
    for i in range(len(path_nodes) - 1):
        data = G.get_edge_data(path_nodes[i], path_nodes[i + 1]) or {}
        total += float(data.get("length_m", 0))
    return round(total, 1)


def _score_fields_for_mode(mode: RouteMode) -> tuple[str, ...]:
    if mode == RouteMode.accessible:
        return ("barrier_free_score", "flatness_score")
    if mode == RouteMode.evacuation:
        return ("emergency_evacuation_score", "width_score")
    return ("lighting_score", "width_score")


def _normalize_score_to_100(value: float) -> float:
    if value <= 1.5:
        score = value * 100
    elif value <= 10:
        score = value * 10
    else:
        score = value

    return max(0.0, min(100.0, score))


def _edge_score(data: dict[str, Any], mode: RouteMode) -> float:
    values: list[float] = []
    for field in _score_fields_for_mode(mode):
        try:
            values.append(_normalize_score_to_100(float(data.get(field, 5) or 5)))
        except (TypeError, ValueError):
            values.append(50.0)

    return sum(values) / len(values)


def _path_score(path_nodes: list[int], G: nx.DiGraph, mode: RouteMode) -> float | None:
    weighted_score = 0.0
    total_length = 0.0

    for i in range(len(path_nodes) - 1):
        data = G.get_edge_data(path_nodes[i], path_nodes[i + 1]) or {}
        length = float(data.get("length_m", 0) or 0)
        if length <= 0:
            continue
        weighted_score += _edge_score(data, mode) * length
        total_length += length

    if total_length <= 0:
        return None

    return round(weighted_score / total_length, 1)


# ---------------------------------------------------------------------------
# 路径规划核心
# ---------------------------------------------------------------------------

async def _calc_route(
    origin: str,
    destination: str,
    mode: RouteMode,
    user_location: Coordinate | None,
    reason: list[str],
    steps_template: list[RouteStep],
) -> RouteResult:
    """通用路径规划入口。"""
    cache_key = _route_cache_key(mode, origin, destination, user_location)
    cached = _get_cached_route(cache_key)
    if cached:
        return cached

    try:
        G = await _load_graph(mode)
        nodes = await _load_nodes()
        pois = await _load_pois()

        # 解析起终点坐标
        origin_coord = (
            user_location
            or _find_poi_coord(origin, pois)
        )
        dest_coord = _find_poi_coord(destination, pois)

        if not origin_coord or not dest_coord:
            logger.warning(f"无法解析坐标：origin={origin}, destination={destination}，返回 mock")
            raise ValueError("坐标解析失败")

        # 找最近路网节点
        src_node = _nearest_node(nodes, origin_coord)
        tgt_node = _nearest_node(nodes, dest_coord)

        if src_node == tgt_node:
            raise ValueError("起终点过近")

        # Dijkstra 最短路径
        path = nx.dijkstra_path(G, src_node, tgt_node, weight="weight")
        length_m = _path_length(path, G)
        eta_min = round(length_m / 80, 1)  # 步行速度约 80 m/min

        geojson = _path_to_geojson(path, nodes, G)
        safety_score = _path_score(path, G, mode)

        result = RouteResult(
            mode=mode,
            origin=origin,
            destination=destination,
            distance_m=length_m,
            eta_min=eta_min,
            safety_score=safety_score,
            route_geojson=geojson,
            steps=steps_template,
            reason=reason,
            is_mock=False,
        )
        _set_cached_route(cache_key, result)
        return result

    except Exception as e:
        logger.error(f"路径规划失败 [{mode.value}] {origin}->{destination}：{e}")
        raise


# ---------------------------------------------------------------------------
# 对外接口
# ---------------------------------------------------------------------------

async def calc_night_safe_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """夜间安全路径：优先照明好、开敞度高的路段。"""
    return await _calc_route(
        origin, destination, RouteMode.night, user_location,
        reason=[
            "优先通过照明评分高的主步道，降低夜间盲区风险。",
            "自动规避照明不足路段，沿连续路灯区域前行。",
            "路径安全评分综合考虑照明、宽度和开敞度。",
        ],
        steps_template=[
            RouteStep(seq=1, title=f"从{origin}出发", detail="沿系统推荐路线前行。", state="start"),
            RouteStep(seq=2, title="途经主步道", detail="照明覆盖良好，通行宽度较好。", state="safe"),
            RouteStep(seq=3, title=f"到达{destination}", detail="路径结束。", state="end"),
        ],
    )


async def calc_accessible_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """无障碍路径：避开台阶，优先无障碍评分高的路段。"""
    return await _calc_route(
        origin, destination, RouteMode.accessible, user_location,
        reason=[
            "全程避开无障碍评分过低路段，采用坡道替代方案。",
            "路面平整度综合评分较高，适合轮椅通行。",
        ],
        steps_template=[
            RouteStep(seq=1, title=f"从{origin}出发", detail="选择无障碍出口，避开台阶。", state="start"),
            RouteStep(seq=2, title="途经无障碍路段", detail="全程平整，无台阶。", state="safe"),
            RouteStep(seq=3, title=f"到达{destination}", detail="路径结束。", state="end"),
        ],
    )


async def calc_evacuation_route(
    origin: str,
    destination: str,
    user_location: Coordinate | None = None,
) -> RouteResult:
    """应急撤离路径：快速撤离至操场、校门等安全集结点。"""
    return await _calc_route(
        origin, destination, RouteMode.evacuation, user_location,
        reason=[
            "路径全程开敞，撤离适宜度评分高。",
            "已排除封闭路段和障碍严重路段。",
            f"{destination}为最近安全集结点。",
        ],
        steps_template=[
            RouteStep(seq=1, title=f"从{origin}紧急撤离", detail="沿推荐路线快速移动。", state="start"),
            RouteStep(seq=2, title="途经主干道", detail="宽阔开敞，无封闭路段。", state="normal"),
            RouteStep(seq=3, title=f"到达{destination}", detail="安全集结点，请等待进一步指示。", state="end"),
        ],
    )


async def calc_multistop_route(
    origin: str,
    stops: list[str],
    destination: str,
    time_constraint: str | None = None,
) -> RouteResult:
    """多目标串联路径：依次经过各停靠点，返回总成本最优路径。"""
    try:
        G = await _load_graph(RouteMode.night)
        nodes = await _load_nodes()
        pois = await _load_pois()

        # 构建完整路径点序列：origin -> stops -> destination
        if 1 < len(stops) <= 4:
            best_order: tuple[str, ...] | None = None
            best_length: float | None = None
            last_error: Exception | None = None

            for order in permutations(stops):
                try:
                    candidate_waypoints = [origin] + list(order) + [destination]
                    candidate_length = 0.0

                    for i in range(len(candidate_waypoints) - 1):
                        src_coord = _find_poi_coord(candidate_waypoints[i], pois)
                        tgt_coord = _find_poi_coord(candidate_waypoints[i + 1], pois)

                        if not src_coord or not tgt_coord:
                            raise ValueError(
                                f"Unable to resolve coordinates: {candidate_waypoints[i]} or {candidate_waypoints[i + 1]}"
                            )

                        src_node = _nearest_node(nodes, src_coord)
                        tgt_node = _nearest_node(nodes, tgt_coord)
                        path = nx.dijkstra_path(G, src_node, tgt_node, weight="weight")
                        candidate_length += _path_length(path, G)

                    if best_length is None or candidate_length < best_length:
                        best_order = order
                        best_length = candidate_length
                except Exception as exc:
                    last_error = exc

            if best_order is not None:
                stops = list(best_order)
            elif last_error:
                raise last_error

        waypoints = [origin] + stops + [destination]
        total_length = 0.0
        weighted_score = 0.0
        score_length = 0.0
        all_coords: list[list[float]] = []

        for i in range(len(waypoints) - 1):
            src_name = waypoints[i]
            tgt_name = waypoints[i + 1]

            src_coord = _find_poi_coord(src_name, pois)
            tgt_coord = _find_poi_coord(tgt_name, pois)

            if not src_coord or not tgt_coord:
                raise ValueError(f"无法解析坐标：{src_name} 或 {tgt_name}")

            src_node = _nearest_node(nodes, src_coord)
            tgt_node = _nearest_node(nodes, tgt_coord)

            path = nx.dijkstra_path(G, src_node, tgt_node, weight="weight")
            seg_length = _path_length(path, G)
            total_length += seg_length
            seg_score = _path_score(path, G, RouteMode.night)
            if seg_score is not None and seg_length > 0:
                weighted_score += seg_score * seg_length
                score_length += seg_length

            _append_line_coords(all_coords, _path_coordinates(path, nodes, G))

        eta_min = round(total_length / 80, 1)
        safety_score = round(weighted_score / score_length, 1) if score_length > 0 else None

        # 构建步骤
        steps = [RouteStep(seq=1, title=f"从{origin}出发", detail="前往第一个目的地。", state="start")]
        for idx, stop in enumerate(stops, start=2):
            steps.append(RouteStep(seq=idx, title=stop, detail=f"途经{stop}。", state="normal"))
        steps.append(RouteStep(seq=len(steps) + 1, title=f"到达{destination}", detail="路径结束。", state="end"))

        return RouteResult(
            mode=RouteMode.multi,
            origin=origin,
            destination=destination,
            distance_m=round(total_length, 1),
            eta_min=eta_min,
            safety_score=safety_score,
            route_geojson={
                "type": "Feature",
                "geometry": {"type": "LineString", "coordinates": all_coords},
                "properties": {},
            },
            steps=steps,
            reason=[
                f"串联路径总长 {total_length:.0f} 米，为满足所有停靠条件的最优组合。",
                "各停靠点均满足营业时间约束。",
            ],
            optimized_stops=stops,
            is_mock=False,
        )

    except Exception as e:
        logger.error(f"多目标路径规划失败：{e}")
        raise
