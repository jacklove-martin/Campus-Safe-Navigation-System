"""
LLM 服务层：调用 DeepSeek API，将自然语言解析为结构化任务。
当 API Key 未配置时自动降级到本地规则解析兜底逻辑。
"""
import json
import re
import logging
from difflib import get_close_matches
from openai import AsyncOpenAI

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
from app.models import FacilityType, IntentType, ParsedTask, RouteMode
from app.services.facility import get_all_poi_names

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# DeepSeek 客户端（DeepSeek 兼容 OpenAI SDK）
# ---------------------------------------------------------------------------

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(
            api_key=DEEPSEEK_API_KEY,
            base_url=DEEPSEEK_BASE_URL,
        )
    return _client


# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """你是一个校园安全导览系统的意图解析助手。
你的任务是将用户的自然语言问题解析为结构化的 JSON 任务对象。

## 可识别的意图类型（intent）
- navigation：位置导航，用户想知道怎么去某个地方
- facility_query：设施查询，用户想查询某类设施的营业状态、位置或服务内容
- night_safe_route：夜间安全路径，用户想走更安全的夜间路线
- accessible_route：无障碍路径，用户需要适合轮椅或行动不便者的路线
- evacuation_route：应急撤离路径，用户遇到紧急情况需要撤离
- multi_stop_service_route：多目标串联路径，用户有多个途经地点
- unknown：无法识别

## 设施类型（facility_type）
dormitory / teaching_building / library / canteen / store / vending_machine / playground / gate / other

## 路径模式（route_mode）
night / accessible / evacuation / multi

## 重要地名规则
- 用户说“大门”“学校大门”“校园大门”“校门”“最近校门”时，含义是学校校门，必须按 gate 类设施理解，不要输出“图书馆北门/图书馆南门”等建筑入口。
- 如果用户没有指明东门/南门/北门/西北门等具体校门，destination 保留为“校门”，facility_type 可设为 "gate"，由后端按起点选择最近校门。
- 用户说“宿舍楼”“宿舍区”“寝室”但没有具体楼栋时，origin 保留为“宿舍”，不要随意猜测非宿舍 POI。
- 用户说“食堂”“餐厅”“吃饭”“夜宵”时，facility_type 应设为 "canteen"；如果无法确定具体食堂，destination 可以为空或保留“食堂”。

## 输出格式（严格 JSON，不要输出其他内容）
{
  "intent": "<意图类型>",
  "origin": "<出发地，无则null>",
  "destination": "<目的地，无则null>",
  "stops": ["<中途点1>", "<中途点2>"],
  "facility_type": "<设施类型，无则null>",
  "time_constraint": "<时间约束如22:00，无则null>",
  "route_mode": "<路径模式，无则null>",
  "priority_rule": "<优先规则如stationery/night_service，无则null>"
}

## 示例
用户：宿舍发生了火灾，请告诉我如何撤离到操场
输出：{"intent":"evacuation_route","origin":null,"destination":"操场","stops":[],"facility_type":"playground","time_constraint":null,"route_mode":"evacuation","priority_rule":null}

用户：我想吃夜宵，吃完再去便利店买一本笔记本，最后回一组团四栋
输出：{"intent":"multi_stop_service_route","origin":null,"destination":"一组团四栋","stops":["食堂","便利店"],"facility_type":null,"time_constraint":null,"route_mode":"multi","priority_rule":"stationery"}
"""


# ---------------------------------------------------------------------------
# 主解析函数
# ---------------------------------------------------------------------------

_POI_PROMPT_LIMIT = 200
_ROUTE_INTENTS = {
    IntentType.navigation,
    IntentType.night_safe_route,
    IntentType.accessible_route,
    IntentType.evacuation_route,
    IntentType.multi_stop_route,
}
_GENERIC_GATE_ALIASES = {"校门", "大门", "学校大门", "校园大门", "最近校门"}
_SPECIFIC_GATE_NAMES = {"北门", "南门", "东门", "西门", "西北门"}
_GENERIC_DORM_ALIASES = {"宿舍", "宿舍楼", "宿舍区", "寝室"}


def _raw_text_asks_generic_gate(text: str | None) -> bool:
    return bool(text) and any(alias in text for alias in _GENERIC_GATE_ALIASES) and not any(
        gate in text for gate in _SPECIFIC_GATE_NAMES
    )


async def _safe_get_poi_names() -> list[str]:
    try:
        return await get_all_poi_names()
    except Exception as exc:
        logger.warning("POI names unavailable for LLM prompt: %s", exc)
        return []


def _build_system_prompt(poi_names: list[str]) -> str:
    if not poi_names:
        return SYSTEM_PROMPT

    names = "\n".join(f"- {name}" for name in poi_names[:_POI_PROMPT_LIMIT])
    return (
        f"{SYSTEM_PROMPT}\n\n"
        "## 已知校园 POI 名称\n"
        "当 origin、destination 或 stops 指向具体地点时，优先从以下名称中选择完全一致的名称输出；"
        "如果用户只说设施类别（如食堂、宿舍、便利店）且无法确定具体地点，可以保留原词。\n"
        f"{names}"
    )


def _correct_place_name(name: str | None, poi_names: list[str]) -> str | None:
    if not name or not poi_names:
        return name

    cleaned = name.strip()
    if not cleaned:
        return None

    if any(alias in cleaned for alias in _GENERIC_GATE_ALIASES) and not any(
        gate in cleaned for gate in _SPECIFIC_GATE_NAMES
    ):
        return "校门"

    if cleaned in _GENERIC_DORM_ALIASES:
        return "宿舍"

    if cleaned in poi_names:
        return cleaned

    embedded = [poi for poi in poi_names if poi in cleaned]
    if embedded:
        return max(embedded, key=len)

    contained = [poi for poi in poi_names if cleaned in poi]
    if len(contained) == 1:
        return contained[0]

    matches = get_close_matches(cleaned, poi_names, n=1, cutoff=0.72)
    return matches[0] if matches else cleaned


def _validate_route_place_names(task: ParsedTask, poi_names: list[str]) -> ParsedTask:
    if not poi_names or task.intent not in _ROUTE_INTENTS:
        return task

    updates = {}

    raw_asks_generic_gate = _raw_text_asks_generic_gate(task.raw_text)
    for field in ("origin", "destination"):
        current = getattr(task, field)
        if field == "destination" and raw_asks_generic_gate:
            corrected = "校门"
        else:
            corrected = _correct_place_name(current, poi_names)
        if corrected != current:
            updates[field] = corrected

    corrected_stops = [_correct_place_name(stop, poi_names) or stop for stop in task.stops]
    if corrected_stops != task.stops:
        updates["stops"] = corrected_stops

    if updates:
        logger.info("Corrected route place names from POI list: %s", updates)
        return task.model_copy(update=updates)

    return task


async def parse_user_query(text: str) -> ParsedTask:
    """
    调用 DeepSeek API 解析用户自然语言。
    API 不可用时降级到本地规则解析。
    """
    poi_names = await _safe_get_poi_names()

    if not DEEPSEEK_API_KEY:
        logger.warning("DEEPSEEK_API_KEY 未配置，使用本地规则解析兜底")
        return _validate_route_place_names(_fallback_parse(text), poi_names)

    try:
        client = _get_client()
        response = await client.chat.completions.create(
            model=DEEPSEEK_MODEL,
            messages=[
                {"role": "system", "content": _build_system_prompt(poi_names)},
                {"role": "user", "content": text},
            ],
            temperature=0.0,
            max_tokens=512,
        )
        raw = response.choices[0].message.content.strip()
        # 提取 JSON（防止模型在 JSON 外输出多余文字）
        json_match = re.search(r'\{.*\}', raw, re.DOTALL)
        if not json_match:
            raise ValueError(f"模型输出不含有效 JSON：{raw}")
        data = json.loads(json_match.group())
        return _validate_route_place_names(ParsedTask(raw_text=text, **data), poi_names)

    except Exception as e:
        logger.error(f"DeepSeek 解析失败：{e}，降级到本地规则解析")
        return _validate_route_place_names(_fallback_parse(text), poi_names)


# ---------------------------------------------------------------------------
# 本地规则解析兜底
# ---------------------------------------------------------------------------

_FACILITY_QUERY_KEYWORDS = ["在哪", "哪里", "开门", "营业", "几点", "有没有", "卖", "最近"]

_KEYWORD_INTENT: list[tuple[list[str], IntentType, RouteMode | None]] = [
    (["火灾", "撤离", "逃跑", "疏散", "紧急", "应急"], IntentType.evacuation_route, RouteMode.evacuation),
    (["无障碍", "轮椅", "坡道", "行动不便"],           IntentType.accessible_route,  RouteMode.accessible),
    (["多目标", "顺路", "吃完", "最后"],                IntentType.multi_stop_route,   RouteMode.multi),
    (["夜间", "晚上", "夜晚", "安全路", "黑暗"],       IntentType.night_safe_route,   RouteMode.night),
    (["怎么走", "导航", "路线", "去"],                  IntentType.navigation,         RouteMode.night),
    (_FACILITY_QUERY_KEYWORDS,                            IntentType.facility_query,     None),
]

_FACILITY_KEYWORDS: list[tuple[list[str], FacilityType]] = [
    (["食堂", "吃饭", "夜宵", "餐厅"],                 FacilityType.canteen),
    (["便利店", "超市", "文具", "笔记本", "买东西"],    FacilityType.store),
    (["宿舍", "寝室", "组团"],                          FacilityType.dormitory),
    (["教学楼", "上课", "课室"],                        FacilityType.teaching_building),
    (["图书馆", "自习"],                                FacilityType.library),
    (["操场", "运动场", "集结"],                        FacilityType.playground),
    (["校门", "东门", "西门", "南门", "北门"],          FacilityType.gate),
    (["售货机", "自动"],                                FacilityType.vending_machine),
]


def _strip_mode_hint(text: str) -> str:
    return re.sub(r"^(夜间安全|无障碍|应急疏散|多目标)[:：]\s*", "", text.strip())


def _clean_place_name(value: str | None) -> str | None:
    if not value:
        return None

    cleaned = re.split(r"[，,。！？?]", value.strip(), maxsplit=1)[0]
    cleaned = re.sub(r"^(晚上|夜间|夜晚|现在|当前|请问|帮我|带我|我要|我想)\s*", "", cleaned)
    cleaned = re.sub(
        r"(哪条路.*|哪个路.*|怎么走.*|路线.*|更安全.*|最安全.*|在哪里.*|在哪.*)$",
        "",
        cleaned,
    )
    cleaned = cleaned.strip(" ：:，,。！？? 的")
    return cleaned or None


def _extract_route_points(text: str) -> tuple[str | None, str | None]:
    clean_text = _strip_mode_hint(text)

    patterns = [
        r"从(?P<origin>.+?)(?:到|去|回)(?P<destination>.+)",
        r"(?P<origin>.+?)回(?P<destination>.+)",
        r"(?P<origin>.+?)(?:到|去)(?P<destination>.+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, clean_text)
        if match:
            return (
                _clean_place_name(match.group("origin")),
                _clean_place_name(match.group("destination")),
            )

    return None, None


def _extract_facility_destination(text: str, facility_type: FacilityType | None) -> str | None:
    clean_text = _strip_mode_hint(text)

    for keywords, _ftype in _FACILITY_KEYWORDS:
        if facility_type == _ftype:
            for keyword in keywords:
                if keyword in clean_text:
                    return keyword

    return None


def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def _fallback_parse(text: str) -> ParsedTask:
    """基于关键词的简单规则解析，作为 LLM 不可用时的兜底。"""
    clean_text = _strip_mode_hint(text)
    intent = IntentType.unknown
    route_mode = None
    facility_type = None
    priority_rule = None
    origin, destination = _extract_route_points(text)

    for keywords, _ftype in _FACILITY_KEYWORDS:
        if any(kw in clean_text for kw in keywords):
            facility_type = _ftype
            break

    has_facility_query = _contains_any(clean_text, _FACILITY_QUERY_KEYWORDS)
    has_route_points = bool(origin and destination)

    if has_facility_query and not has_route_points:
        intent = IntentType.facility_query
        route_mode = None
        destination = _extract_facility_destination(clean_text, facility_type)
    else:
        for keywords, _intent, _mode in _KEYWORD_INTENT:
            if any(kw in clean_text for kw in keywords):
                intent = _intent
                route_mode = _mode
                break

    if has_route_points:
        if intent == IntentType.navigation and _contains_any(clean_text, ["晚上", "夜间", "安全"]):
            intent = IntentType.night_safe_route
            route_mode = RouteMode.night
        elif intent == IntentType.unknown:
            intent = IntentType.navigation
            route_mode = RouteMode.night

    if "文具" in clean_text or "笔记本" in clean_text:
        priority_rule = "stationery"
    elif _contains_any(clean_text, ["夜宵", "夜间", "晚上", "开门", "营业"]):
        priority_rule = "night_service"

    return ParsedTask(
        raw_text=text,
        intent=intent,
        origin=origin,
        destination=destination,
        route_mode=route_mode,
        facility_type=facility_type,
        priority_rule=priority_rule,
    )
