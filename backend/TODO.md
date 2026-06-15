# 后端待办清单

基于当前已完成的工作（FastAPI 骨架、PostgreSQL 接入、networkx 路径规划、DeepSeek API 接入），第二位后端同学可以在此基础上继续推进以下工作。

**建议执行顺序：** 1 → 6 → 4 → 5 → 2 → 3 → 7 → 其余

---

## 🔴 高优先级（影响系统可用性）

### 1. LLM 地名解析优化

**问题描述**

DeepSeek 解析出的 `origin` / `destination` 是自然语言描述（如"宿舍"、"教学楼旁边"），但 GIS 服务需要精确匹配 `nav.poi.name`（如"学生公寓A栋"），两者不一致时系统会降级返回 mock 数据，`is_mock: true`。

**任务**

- 服务启动时从 `nav.poi` 读取所有 `name` 字段，存入内存列表
- 修改 `services/llm.py` 中的 `SYSTEM_PROMPT`，将 POI 名称列表注入 Prompt，引导模型从已知地名中选择输出
- 对模型输出的地名做二次校验：若不在 POI 列表中，用字符串相似度（`difflib.get_close_matches`）做模糊纠正

**涉及文件**

- `app/services/llm.py`
- `app/services/facility.py`（新增 `get_all_poi_names()` 函数）

---

### 2. 路网缓存刷新机制

**问题描述**

`services/gis.py` 中的 `_graph_cache` 在进程内永久缓存，数据库路网数据更新后不会自动刷新，需要重启服务才能生效。

**任务**

- 新增管理接口 `POST /admin/reload-graph`，清空 `_graph_cache` 并重新加载所有模式的路网图
- 或在缓存 key 中加时间戳，超过 30 分钟自动失效重载

**涉及文件**

- `app/services/gis.py`
- `app/routers/`（新增 `admin.py` 路由）

---

### 3. 输入参数清洗与校验

**问题描述**

`/route-*` 接口的 `origin` / `destination` 参数直接传入字符串，没有长度限制和非法字符过滤，存在超长输入和注入风险。

**任务**

- 在 `routers/route.py` 的 Query 参数上增加长度限制（`max_length=100`）
- 对 `origin` / `destination` 过滤特殊字符，防止 SQL 注入
- 对空字符串、纯空格输入返回 422 错误而不是直接进入业务逻辑

**涉及文件**

- `app/routers/route.py`
- `app/routers/query.py`

---

## 🟡 中优先级（提升系统质量）

### 4. 统一错误处理

**问题描述**

当前各接口错误响应格式不统一，部分异常直接抛出 500，前端无法区分错误类型。

**任务**

在 `main.py` 注册全局异常处理器，所有错误统一返回以下格式：

```json
{
  "success": false,
  "error_code": "ROUTE_NOT_FOUND",
  "message": "无法在路网中找到从教学楼到宿舍的路径，请检查地名是否正确。"
}
```

常用 error_code 建议：

| error_code | 说明 |
|------------|------|
| `ROUTE_NOT_FOUND` | 路径规划失败，路网不连通 |
| `POI_NOT_FOUND` | 地名无法解析为坐标 |
| `DB_ERROR` | 数据库查询异常 |
| `LLM_ERROR` | DeepSeek API 调用失败 |
| `INVALID_PARAMS` | 参数格式错误 |

**涉及文件**

- `app/main.py`
- `app/models.py`（`ErrorResponse` 已定义，直接使用）

---

### 5. 请求日志中间件

**问题描述**

当前没有统一的请求日志，联调时难以排查问题，不知道是哪个接口、哪个参数出了问题。

**任务**

在 `main.py` 添加 Starlette 中间件，记录每次请求的：

- 请求方法、路径、查询参数
- 响应状态码
- 耗时（毫秒）

输出格式示例：

```
INFO: POST /query 200 312ms
INFO: GET /facility-search?keyword=食堂 200 45ms
INFO: GET /route-night-safe?origin=教学楼&destination=宿舍 200 128ms
```

**涉及文件**

- `app/main.py`

---

### 6. 营业时间实时判断

**问题描述**

当前 `/facility-search?night_available=true` 只查询数据库的布尔字段，没有根据当前实际时间判断是否营业，用户问"现在还开门的食堂"时结果不准确。

**任务**

- 在 `services/facility.py` 新增 `is_open_now(open_time, close_time)` 函数，根据系统当前时间判断是否在营业时间内
- 在 `FacilityItem` 响应中新增 `is_open_now: bool` 字段
- 新增查询参数 `open_now=true`，仅返回当前营业中的设施

注意：`close_time` 为次日凌晨（如 `02:00`）的情况需要特殊处理，避免跨零点判断错误。

**涉及文件**

- `app/models.py`（`FacilityItem` 新增字段）
- `app/services/facility.py`
- `app/routers/facility.py`（新增 `open_now` 查询参数）

---

### 7. 多目标路径停靠顺序优化

**问题描述**

`/route-multistop` 当前按用户输入的 stops 顺序串联，没有对停靠顺序做全排列优化，可能不是最短路径组合。

**任务**

- 当 `stops` 数量 ≤ 4 时，对停靠顺序做全排列（`itertools.permutations`），计算所有组合的总距离，返回最优顺序
- 当 `stops` 数量 > 4 时，保持原有顺序（全排列组合数过多）
- 在响应中增加 `optimized_stops` 字段，告知前端最终采用的停靠顺序

**涉及文件**

- `app/services/gis.py`
- `app/models.py`（`RouteResult` 新增 `optimized_stops` 字段）

---

## 🟢 低优先级（锦上添花）

### 8. 高频查询响应缓存

对相同 origin / destination / mode 的路径规划请求加内存缓存，减少重复计算。

使用 `cachetools.TTLCache`，TTL 设为 5 分钟：

```python
from cachetools import TTLCache
_route_cache = TTLCache(maxsize=200, ttl=300)
```

**涉及文件**：`app/services/gis.py`

---

### 9. 批量设施查询接口

前端地图初始化时需要一次性获取所有设施坐标用于打点，当前 `/facility-search` 每次最多返回 100 条且字段较多。

新增 `GET /facility-search/all-points`，返回精简字段：

```json
[
  {
    "facility_id": "129",
    "facility_name": "第一食堂",
    "facility_type": "canteen",
    "coordinate": {"lng": 114.6132, "lat": 30.4579}
  }
]
```

**涉及文件**：`app/routers/facility.py`

---

### 10. 健康检查接口扩展

扩展 `GET /health`，增加路网和数据状态信息，方便部署后快速确认系统状态：

```json
{
  "status": "ok",
  "version": "0.1.0",
  "db": "connected",
  "poi_count": 131,
  "road_segment_count": 86,
  "graph_loaded": {
    "night": true,
    "accessible": false,
    "evacuation": false
  }
}
```

**涉及文件**：`app/main.py`、`app/services/gis.py`

---

### 11. `.env.example` 补全注释

当前 `.env.example` 中 `DB_PASSWORD` 为空，其他同学拿到项目时不清楚如何配置数据库密码。

补充说明：
- 如何在 pgAdmin 中修改 PostgreSQL 用户密码
- DeepSeek API Key 的申请地址
- CORS_ORIGINS 在前端使用非默认端口时如何修改

**涉及文件**：`.env.example`

---

## 完成标准

每项任务完成后，建议：

1. 在 Swagger（`http://127.0.0.1:8000/docs`）上验证接口正常响应
2. 对应修改 `README.md` 中的接口文档
3. 将该条目从"待办"移入"已完成"并注明完成日期
