"""
请求与响应的 Pydantic 数据模型。
所有接口均使用这里定义的模型做入参校验和出参序列化。
"""
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# 枚举
# ---------------------------------------------------------------------------

class RouteMode(str, Enum):
    night = "night"            # 夜间安全
    accessible = "accessible"  # 无障碍
    evacuation = "evacuation"  # 应急撤离
    multi = "multi"            # 多目标串联


class FacilityType(str, Enum):
    dormitory = "dormitory"           # 宿舍
    teaching_building = "teaching_building"  # 教学楼
    library = "library"               # 图书馆
    canteen = "canteen"               # 食堂
    store = "store"                   # 便利店
    vending_machine = "vending_machine"  # 自动售货机
    playground = "playground"         # 操场
    gate = "gate"                     # 校门
    other = "other"                   # 其他地标


class IntentType(str, Enum):
    navigation = "navigation"                   # 位置导航
    facility_query = "facility_query"           # 营业/服务查询
    night_safe_route = "night_safe_route"       # 夜间安全路径
    accessible_route = "accessible_route"       # 无障碍路径
    evacuation_route = "evacuation_route"       # 应急撤离路径
    multi_stop_route = "multi_stop_service_route"  # 多目标路径
    unknown = "unknown"


# ---------------------------------------------------------------------------
# 通用坐标
# ---------------------------------------------------------------------------

class Coordinate(BaseModel):
    lng: float = Field(..., description="经度")
    lat: float = Field(..., description="纬度")


# ---------------------------------------------------------------------------
# 请求模型
# ---------------------------------------------------------------------------

class QueryRequest(BaseModel):
    """自然语言问答入口请求体"""
    text: str = Field(..., min_length=1, max_length=500, description="用户输入的自然语言问题")
    user_location: Optional[Coordinate] = Field(None, description="用户当前位置（可选）")


class RouteRequest(BaseModel):
    """路径规划通用请求体"""
    origin: str = Field(..., min_length=1, max_length=100, description="出发地名称或设施ID")
    destination: str = Field(..., min_length=1, max_length=100, description="目的地名称或设施ID")
    mode: RouteMode = Field(RouteMode.night, description="路径模式")
    user_location: Optional[Coordinate] = Field(None, description="用户当前坐标（可选，用于就近计算）")


class MultiStopRouteRequest(BaseModel):
    """多目标串联路径请求体"""
    origin: str = Field(..., min_length=1, max_length=100, description="出发地")
    stops: list[str] = Field(..., min_length=1, description="中途停靠点列表，按顺序排列")
    destination: str = Field(..., min_length=1, max_length=100, description="最终目的地")
    time_constraint: Optional[str] = Field(None, description="时间约束，如 '22:00'")


class FacilitySearchRequest(BaseModel):
    """设施检索请求体"""
    keyword: Optional[str] = Field(None, description="关键词（名称/别名/标签）")
    facility_type: Optional[FacilityType] = Field(None, description="设施类型筛选")
    night_available: Optional[bool] = Field(None, description="是否夜间可用")
    open_now: Optional[bool] = Field(None, description="是否当前营业中")
    is_evacuation_point: Optional[bool] = Field(None, description="是否为撤离点")
    user_location: Optional[Coordinate] = Field(None, description="用于计算最近距离")


# ---------------------------------------------------------------------------
# GIS 分析任务结构（LLM 解析结果）
# ---------------------------------------------------------------------------

class ParsedTask(BaseModel):
    """DeepSeek 将自然语言解析后输出的结构化任务"""
    intent: IntentType = Field(..., description="识别出的意图类型")
    origin: Optional[str] = Field(None, description="出发地")
    destination: Optional[str] = Field(None, description="目的地")
    stops: list[str] = Field(default_factory=list, description="中途停靠点")
    facility_type: Optional[FacilityType] = Field(None, description="涉及的设施类型")
    time_constraint: Optional[str] = Field(None, description="时间约束")
    route_mode: Optional[RouteMode] = Field(None, description="路径模式")
    priority_rule: Optional[str] = Field(None, description="优先规则，如 stationery/night_service")
    raw_text: str = Field("", description="原始输入文本")


# ---------------------------------------------------------------------------
# 响应模型
# ---------------------------------------------------------------------------

class FacilityItem(BaseModel):
    """单个设施信息"""
    facility_id: str
    facility_name: str
    facility_type: FacilityType
    alias_names: Optional[str] = None
    open_time: Optional[str] = None
    close_time: Optional[str] = None
    is_open_now: Optional[bool] = Field(None, description="是否当前营业中")
    night_available: bool = False
    is_evacuation_point: bool = False
    remark: Optional[str] = None
    keyword_tags: Optional[str] = None
    coordinate: Optional[Coordinate] = None
    distance_m: Optional[float] = Field(None, description="距用户位置距离（米）")


class RouteStep(BaseModel):
    """路径中的一个步骤节点"""
    seq: int = Field(..., description="顺序编号，从1开始")
    title: str = Field(..., description="节点名称")
    detail: str = Field(..., description="步骤说明")
    state: str = Field("normal", description="节点状态: start/normal/safe/warning/end")


class RouteResult(BaseModel):
    """路径分析结果"""
    mode: RouteMode
    origin: str
    destination: str
    distance_m: float = Field(..., description="路径总长度（米）")
    eta_min: float = Field(..., description="预计步行时间（分钟）")
    safety_score: Optional[float] = Field(None, description="安全评分 0-100")
    route_geojson: dict[str, Any] = Field(..., description="路径 GeoJSON LineString")
    steps: list[RouteStep] = Field(default_factory=list, description="路径步骤列表")
    reason: list[str] = Field(default_factory=list, description="推荐理由列表")
    optimized_stops: list[str] = Field(default_factory=list, description="多目标路径最终采用的停靠顺序")
    is_mock: bool = Field(True, description="是否为 mock 数据，mdb 接入后置为 False")


class QueryResponse(BaseModel):
    """自然语言查询统一响应体"""
    success: bool = True
    message: str = Field("", description="面向用户的文字说明")
    parsed_task: Optional[ParsedTask] = Field(None, description="LLM 解析结果")
    route: Optional[RouteResult] = Field(None, description="路径结果（如适用）")
    facilities: list[FacilityItem] = Field(default_factory=list, description="相关设施列表")
    is_mock: bool = True


class FacilitySearchResponse(BaseModel):
    """设施检索响应"""
    success: bool = True
    total: int = 0
    items: list[FacilityItem] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    error_code: str
    message: str
