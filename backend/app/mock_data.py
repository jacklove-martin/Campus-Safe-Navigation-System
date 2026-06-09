"""
Mock 数据层。
mdb 数据库就绪后，将 services/gis.py 和 services/facility.py 中的
调用替换为真实 ArcPy 查询，此文件可保留用于单元测试。
"""
from app.models import (
    Coordinate,
    FacilityItem,
    FacilityType,
    RouteMode,
    RouteResult,
    RouteStep,
)

# ---------------------------------------------------------------------------
# 设施列表 Mock
# ---------------------------------------------------------------------------

MOCK_FACILITIES: list[FacilityItem] = [
    FacilityItem(
        facility_id="f001",
        facility_name="第一食堂",
        facility_type=FacilityType.canteen,
        alias_names="一食堂",
        open_time="07:00",
        close_time="21:30",
        night_available=True,
        is_evacuation_point=False,
        remark="提供早餐、午餐、晚餐及夜宵窗口",
        keyword_tags="食堂,夜宵,早餐,午餐",
        coordinate=Coordinate(lng=114.3571, lat=30.5321),
    ),
    FacilityItem(
        facility_id="f002",
        facility_name="第二食堂",
        facility_type=FacilityType.canteen,
        alias_names="二食堂",
        open_time="07:30",
        close_time="20:00",
        night_available=False,
        is_evacuation_point=False,
        remark="提供早餐、午餐、晚餐",
        keyword_tags="食堂,午餐,晚餐",
        coordinate=Coordinate(lng=114.3590, lat=30.5308),
    ),
    FacilityItem(
        facility_id="f003",
        facility_name="图书馆",
        facility_type=FacilityType.library,
        alias_names="图书馆,自习室",
        open_time="08:00",
        close_time="22:00",
        night_available=True,
        is_evacuation_point=False,
        remark="晚间至22:00开放自习",
        keyword_tags="图书馆,自习,借书",
        coordinate=Coordinate(lng=114.3560, lat=30.5340),
    ),
    FacilityItem(
        facility_id="f004",
        facility_name="图书馆东侧便利店",
        facility_type=FacilityType.store,
        alias_names="便利店",
        open_time="08:00",
        close_time="22:30",
        night_available=True,
        is_evacuation_point=False,
        remark="经营饮料、零食、日用品及文具",
        keyword_tags="便利店,文具,饮料,零食,日用品",
        coordinate=Coordinate(lng=114.3564, lat=30.5338),
    ),
    FacilityItem(
        facility_id="f005",
        facility_name="一组团四栋",
        facility_type=FacilityType.dormitory,
        alias_names="一组团4栋,1组团4栋",
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=False,
        remark="学生宿舍楼",
        keyword_tags="宿舍,一组团,四栋",
        coordinate=Coordinate(lng=114.3600, lat=30.5295),
    ),
    FacilityItem(
        facility_id="f006",
        facility_name="教学楼A栋",
        facility_type=FacilityType.teaching_building,
        alias_names="A栋,教学楼A",
        open_time="07:00",
        close_time="22:00",
        night_available=True,
        is_evacuation_point=False,
        remark="含北门出入口",
        keyword_tags="教学楼,A栋,上课",
        coordinate=Coordinate(lng=114.3548, lat=30.5355),
    ),
    FacilityItem(
        facility_id="f007",
        facility_name="东门",
        facility_type=FacilityType.gate,
        alias_names="东校门",
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=True,
        remark="24小时开放，应急撤离主要出口",
        keyword_tags="校门,东门,撤离,出口",
        coordinate=Coordinate(lng=114.3625, lat=30.5320),
    ),
    FacilityItem(
        facility_id="f008",
        facility_name="西门",
        facility_type=FacilityType.gate,
        alias_names="西校门",
        open_time="06:00",
        close_time="23:00",
        night_available=True,
        is_evacuation_point=True,
        remark="应急撤离备用出口",
        keyword_tags="校门,西门,撤离,出口",
        coordinate=Coordinate(lng=114.3520, lat=30.5320),
    ),
    FacilityItem(
        facility_id="f009",
        facility_name="操场",
        facility_type=FacilityType.playground,
        alias_names="运动场,田径场",
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=True,
        remark="应急集结点，可容纳大量人员",
        keyword_tags="操场,集结点,撤离,运动",
        coordinate=Coordinate(lng=114.3578, lat=30.5280),
    ),
    FacilityItem(
        facility_id="f010",
        facility_name="自动售货机（图书馆旁）",
        facility_type=FacilityType.vending_machine,
        alias_names=None,
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=False,
        remark="饮料及零食，24小时",
        keyword_tags="售货机,饮料,零食",
        coordinate=Coordinate(lng=114.3558, lat=30.5342),
    ),
    FacilityItem(
        facility_id="f011",
        facility_name="人工湖",
        facility_type=FacilityType.other,
        alias_names="小湖,湖边",
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=False,
        remark="校园景观地标",
        keyword_tags="人工湖,湖,地标,景观",
        coordinate=Coordinate(lng=114.3555, lat=30.5310),
    ),
    FacilityItem(
        facility_id="f012",
        facility_name="喷泉广场",
        facility_type=FacilityType.other,
        alias_names="喷泉,中心广场",
        open_time=None,
        close_time=None,
        night_available=True,
        is_evacuation_point=False,
        remark="校园中心地标，夜间有灯光",
        keyword_tags="喷泉,广场,地标,中心",
        coordinate=Coordinate(lng=114.3570, lat=30.5330),
    ),
]

# 建立快速查找索引
FACILITY_INDEX: dict[str, FacilityItem] = {f.facility_id: f for f in MOCK_FACILITIES}


# ---------------------------------------------------------------------------
# 路径 Mock 工厂
# ---------------------------------------------------------------------------

def _make_line_geojson(coords: list[list[float]]) -> dict:
    """构造 GeoJSON LineString"""
    return {
        "type": "Feature",
        "geometry": {
            "type": "LineString",
            "coordinates": coords,
        },
        "properties": {},
    }


MOCK_ROUTES: dict[RouteMode, RouteResult] = {
    RouteMode.night: RouteResult(
        mode=RouteMode.night,
        origin="教学楼A栋北门",
        destination="一组团四栋",
        distance_m=640,
        eta_min=8.0,
        safety_score=92.0,
        route_geojson=_make_line_geojson([
            [114.3548, 30.5355],
            [114.3558, 30.5348],
            [114.3570, 30.5338],
            [114.3582, 30.5318],
            [114.3600, 30.5295],
        ]),
        steps=[
            RouteStep(seq=1, title="教学楼A栋北门出发", detail="进入主步道，照明完整，通行宽度较好。", state="start"),
            RouteStep(seq=2, title="图书馆前广场", detail="系统规避西侧围挡，转入中心广场路线。", state="normal"),
            RouteStep(seq=3, title="喷泉广场路口", detail="沿中轴路灯覆盖区域继续前行。", state="safe"),
            RouteStep(seq=4, title="宿舍区主路", detail="沿连续路灯区域前行，安全评分提升。", state="safe"),
            RouteStep(seq=5, title="到达一组团四栋", detail="路径结束，可切换返程或周边设施推荐。", state="end"),
        ],
        reason=[
            "优先通过主照明步道与开敞广场，降低夜间盲区风险。",
            "自动避开施工围挡、狭窄路口和照度偏低支路。",
            "沿线经过图书馆广场与宿舍值班区域，整体可视与求助条件更优。",
        ],
        is_mock=True,
    ),
    RouteMode.accessible: RouteResult(
        mode=RouteMode.accessible,
        origin="教学楼A栋北门",
        destination="图书馆",
        distance_m=480,
        eta_min=7.0,
        safety_score=88.0,
        route_geojson=_make_line_geojson([
            [114.3548, 30.5355],
            [114.3550, 30.5350],
            [114.3555, 30.5345],
            [114.3560, 30.5340],
        ]),
        steps=[
            RouteStep(seq=1, title="教学楼A栋北门出发", detail="选择东侧坡道出口，避开主楼台阶。", state="start"),
            RouteStep(seq=2, title="中央广场平整路段", detail="全程平整，无台阶，适合轮椅通行。", state="safe"),
            RouteStep(seq=3, title="图书馆无障碍入口", detail="到达图书馆东侧无障碍坡道入口。", state="end"),
        ],
        reason=[
            "全程避开台阶节点，采用坡道替代方案。",
            "路面平整度评分高于 8 分的路段占比 95%。",
        ],
        is_mock=True,
    ),
    RouteMode.evacuation: RouteResult(
        mode=RouteMode.evacuation,
        origin="一组团四栋",
        destination="操场",
        distance_m=380,
        eta_min=5.0,
        safety_score=95.0,
        route_geojson=_make_line_geojson([
            [114.3600, 30.5295],
            [114.3592, 30.5288],
            [114.3585, 30.5282],
            [114.3578, 30.5280],
        ]),
        steps=[
            RouteStep(seq=1, title="一组团四栋紧急出口", detail="从宿舍楼紧急出口快速撤出。", state="start"),
            RouteStep(seq=2, title="宿舍区主干道", detail="沿宽阔主干道向操场方向快速移动，避开围挡区域。", state="normal"),
            RouteStep(seq=3, title="到达操场集结点", detail="操场为最近安全集结点，可容纳大量人员。", state="end"),
        ],
        reason=[
            "操场为距宿舍区最近的应急集结点，距离约 380 米。",
            "路径全程开敞，无封闭路段，撤离适宜度评分 9.2/10。",
            "已排除死胡同、施工封闭和障碍严重路段。",
        ],
        is_mock=True,
    ),
    RouteMode.multi: RouteResult(
        mode=RouteMode.multi,
        origin="教学楼A栋",
        destination="一组团四栋",
        distance_m=920,
        eta_min=12.0,
        safety_score=89.0,
        route_geojson=_make_line_geojson([
            [114.3548, 30.5355],
            [114.3565, 30.5345],
            [114.3571, 30.5321],
            [114.3564, 30.5338],
            [114.3582, 30.5318],
            [114.3600, 30.5295],
        ]),
        steps=[
            RouteStep(seq=1, title="教学楼A栋出发", detail="前往第一食堂用餐。", state="start"),
            RouteStep(seq=2, title="第一食堂", detail="夜宵窗口营业中，预计停留 20 分钟。", state="normal"),
            RouteStep(seq=3, title="图书馆东侧便利店", detail="购买文具或日用品，22:30 前关门。", state="normal"),
            RouteStep(seq=4, title="到达一组团四栋", detail="返回宿舍，路径结束。", state="end"),
        ],
        reason=[
            "第一食堂夜宵窗口当前营业，满足夜间用餐需求。",
            "图书馆东侧便利店支持文具购买，22:30 前可到达。",
            "综合路径总长 920 米，为满足所有停靠条件的最优组合。",
        ],
        is_mock=True,
    ),
}
