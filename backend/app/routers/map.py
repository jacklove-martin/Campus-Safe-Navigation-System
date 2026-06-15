"""Map layer endpoints for frontend GeoJSON rendering."""
from __future__ import annotations

import json

from fastapi import APIRouter

from app.db import get_pool

router = APIRouter(prefix="/map", tags=["地图图层"])


def feature_collection(features: list[dict]) -> dict:
    return {
        "type": "FeatureCollection",
        "features": features,
    }


def geometry_from_row(row: dict) -> dict | None:
    geometry = row["geometry"]
    if isinstance(geometry, str):
        return json.loads(geometry)
    return geometry


@router.get("/roads", summary="道路网 GeoJSON")
async def roads_layer() -> dict:
    pool = get_pool()
    sql = """
        SELECT
            road_id,
            road_name,
            length_m,
            lighting_score,
            barrier_free_score,
            flatness_score,
            emergency_evacuation_score,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM nav.road_segment
        WHERE geom IS NOT NULL
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    return feature_collection([
        {
            "type": "Feature",
            "geometry": geometry_from_row(row),
            "properties": {
                "road_id": row["road_id"],
                "road_name": row["road_name"],
                "length_m": row["length_m"],
                "lighting_score": row["lighting_score"],
                "barrier_free_score": row["barrier_free_score"],
                "flatness_score": row["flatness_score"],
                "emergency_evacuation_score": row["emergency_evacuation_score"],
            },
        }
        for row in rows
    ])


@router.get("/hazards", summary="风险点 GeoJSON")
async def hazards_layer() -> dict:
    pool = get_pool()
    sql = """
        SELECT
            road_id,
            road_name,
            lighting_score,
            barrier_free_score,
            flatness_score,
            emergency_evacuation_score,
            remark,
            ST_AsGeoJSON(ST_LineInterpolatePoint(geom, 0.5))::json AS geometry
        FROM nav.road_segment
        WHERE geom IS NOT NULL
          AND (
            COALESCE(lighting_score, 10) < 5
            OR COALESCE(barrier_free_score, 10) < 5
            OR COALESCE(flatness_score, 10) < 5
            OR COALESCE(emergency_evacuation_score, 10) < 5
            OR remark IS NOT NULL
          )
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    return feature_collection([
        {
            "type": "Feature",
            "geometry": geometry_from_row(row),
            "properties": {
                "road_id": row["road_id"],
                "road_name": row["road_name"],
                "lighting_score": row["lighting_score"],
                "barrier_free_score": row["barrier_free_score"],
                "flatness_score": row["flatness_score"],
                "emergency_evacuation_score": row["emergency_evacuation_score"],
                "remark": row["remark"],
            },
        }
        for row in rows
    ])


@router.get("/assembly-points", summary="疏散点 GeoJSON")
async def assembly_points_layer() -> dict:
    pool = get_pool()
    sql = """
        SELECT
            poi_id,
            name,
            category,
            night_available,
            open_time,
            close_time,
            remark,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM nav.poi
        WHERE geom IS NOT NULL
          AND category IN ('gate', 'playground')
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    return feature_collection([
        {
            "type": "Feature",
            "geometry": geometry_from_row(row),
            "properties": {
                "poi_id": row["poi_id"],
                "name": row["name"],
                "category": row["category"],
                "night_available": row["night_available"],
                "open_time": str(row["open_time"]) if row["open_time"] else None,
                "close_time": str(row["close_time"]) if row["close_time"] else None,
                "remark": row["remark"],
            },
        }
        for row in rows
    ])


@router.get("/facilities", summary="服务设施 GeoJSON")
async def facilities_layer() -> dict:
    pool = get_pool()
    sql = """
        SELECT
            poi_id,
            name,
            category,
            night_available,
            open_time,
            close_time,
            remark,
            ST_AsGeoJSON(geom)::json AS geometry
        FROM nav.poi
        WHERE geom IS NOT NULL
          AND category NOT IN ('gate', 'playground')
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(sql)

    return feature_collection([
        {
            "type": "Feature",
            "geometry": geometry_from_row(row),
            "properties": {
                "poi_id": row["poi_id"],
                "name": row["name"],
                "category": row["category"],
                "night_available": row["night_available"],
                "open_time": str(row["open_time"]) if row["open_time"] else None,
                "close_time": str(row["close_time"]) if row["close_time"] else None,
                "remark": row["remark"],
            },
        }
        for row in rows
    ])
