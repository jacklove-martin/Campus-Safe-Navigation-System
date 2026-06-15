# 后端开发文档

校园安全服务一体化智能导览系统 — 后端服务

## 目录

- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境准备](#环境准备)
- [启动服务](#启动服务)
- [接口文档](#接口文档)
- [前端对接说明](#前端对接说明)
- [常见问题与坑点](#常见问题与坑点)
- [模块说明](#模块说明)
- [当前状态](#当前状态)

---

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.12 | 运行环境，必须使用系统独立安装版本 |
| FastAPI | 0.115.5 | Web 框架 |
| Uvicorn | 0.32.1 | ASGI 服务器 |
| Pydantic | 2.10.3 | 数据校验与序列化 |
| asyncpg | 0.30.0 | PostgreSQL 异步驱动 |
| networkx | 3.4.2 | 路网图构建与 Dijkstra 路径规划 |
| OpenAI SDK | 1.57.0 | DeepSeek API 调用（兼容 OpenAI 协议） |
| python-dotenv | 1.0.1 | 环境变量管理 |

---

## 项目结构

```
backend/
├── .env.example              # 环境变量模板，复制为 .env 后填写实际值
├── .env                      # 本地环境变量（已加入 .gitignore，禁止提交）
├── requirements.txt          # Python 依赖列表
├── README.md                 # 本文档
└── app/
    ├── main.py               # FastAPI 入口，注册路由、CORS、数据库生命周期
    ├── config.py             # 从 .env 读取全局配置
    ├── db.py                 # asyncpg 连接池初始化与获取
    ├── models.py             # 所有请求/响应 Pydantic 模型及枚举定义
    ├── mock_data.py          # 异常降级用 mock 数据
    ├── routers/
    │   ├── query.py          # POST /query          自然语言问答统一入口
    │   ├── route.py          # GET  /route-*        四类路径分析接口
    │   └── facility.py       # GET  /facility-search 设施检索接口
    └── services/
        ├── llm.py            # DeepSeek API 调用 + 关键词规则兜底解析
        ├── gis.py            # networkx 路径规划，从 PostgreSQL 读取路网
        └── facility.py       # 设施查询，从 PostgreSQL nav.poi 表检索
```

---

## 环境准备

### 第一步：确认 Python 版本

本项目要求使用**系统独立安装的 Python 3.12**。

> 坑点：如果你的机器安装了 QGIS 或 ArcGIS，`python` 命令可能指向它们内置的 Python，这个版本缺少标准库，无法创建虚拟环境。

确认系统 Python 路径：

```powershell
where python
```

正确的路径应该是 `C:\Users\<用户名>\AppData\Local\Programs\Python\Python312\python.exe`，而不是 `D:\qgis-devenv\...` 或 `C:\Program Files\ArcGIS\...`。

### 第二步：创建虚拟环境

> 坑点：如果项目路径包含中文（如"综合实习"），直接在项目目录里创建虚拟环境会失败，报 `Could not find platform independent libraries` 错误。必须将虚拟环境创建在纯英文路径下。

```powershell
# 创建虚拟环境目录
New-Item -ItemType Directory -Path C:\venv -Force

# 用系统 Python 创建虚拟环境（替换 <用户名> 为你自己的）
C:\Users\<用户名>\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\venv\hiq
```

验证是否创建成功：

```powershell
Test-Path C:\venv\hiq\Scripts\python.exe
# 输出 True 表示成功
```

### 第三步：安装依赖

```powershell
C:\venv\hiq\Scripts\python.exe -m pip install -r requirements.txt
```

> 坑点：不要直接用 `pip install`，这会安装到系统 Python 而不是虚拟环境，导致后续启动报 `ModuleNotFoundError`。

### 第四步：配置环境变量

复制模板文件：

```powershell
cd backend
copy .env.example .env
```

用任意文本编辑器打开 `.env`，填写以下内容：

```env
# DeepSeek API Key（在 https://platform.deepseek.com/ 申请）
DEEPSEEK_API_KEY=你的API Key

DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# 前端开发地址，Vite 默认是 5173 端口
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# PostgreSQL 数据库（默认端口 5432）
DB_HOST=127.0.0.1
DB_PORT=5432
DB_NAME=campus_nav_db
DB_USER=postgres
DB_PASSWORD=你的数据库密码
```

> 坑点：`.env` 文件已加入 `.gitignore`，不会被提交到 GitHub。**禁止将含有真实 API Key 或数据库密码的 `.env` 文件提交至仓库**。

### 第五步：确认 PostgreSQL 服务正在运行

打开 pgAdmin 4，确认 `campus_nav_db` 数据库可以正常连接，`nav` schema 下有 `poi`、`road_segment`、`road_node` 三张表。

---

## 启动服务

每次开发时在 PowerShell 中执行：

```powershell
# 进入 backend 目录（替换为你的实际路径）
cd "C:\Users\<用户名>\Desktop\3S综合实习\Campus-Safe-Navigation-System-main\backend"

# 启动服务（--reload 开启热重载，修改代码后自动重启）
C:\venv\hiq\Scripts\python.exe -m uvicorn app.main:app --reload
```

启动成功后终端输出：

```
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000
```

访问地址：

| 地址 | 说明 |
|------|------|
| `http://127.0.0.1:8000/health` | 健康检查，确认数据库是否连通 |
| `http://127.0.0.1:8000/docs` | Swagger 交互文档，可直接在页面测试所有接口 |
| `http://127.0.0.1:8000/redoc` | ReDoc 格式文档 |

健康检查正常响应：

```json
{"status": "ok", "version": "0.1.0", "db": "connected"}
```

> 坑点：如果 `db` 字段显示 `disconnected`，说明数据库连接失败，检查 `.env` 中的密码是否正确，以及 PostgreSQL 服务是否启动。

---

## 接口文档

### POST /query — 自然语言问答（核心接口）

接收用户自然语言输入，由 DeepSeek 解析意图后自动分发到路径规划或设施查询服务。

**请求体**

```json
{
  "text": "晚上从教学楼回宿舍哪条路更安全？",
  "user_location": {
    "lng": 114.6132,
    "lat": 30.4580
  }
}
```

> `user_location` 为可选字段，提供后用于计算最近设施距离和路径起点定位。

**响应体**

```json
{
  "success": true,
  "message": "已为您规划夜间安全路径，全程约 407 米，预计步行 5 分钟。",
  "parsed_task": {
    "intent": "night_safe_route",
    "origin": "教学楼",
    "destination": "宿舍",
    "stops": [],
    "facility_type": "dormitory",
    "time_constraint": null,
    "route_mode": "night",
    "priority_rule": null,
    "raw_text": "晚上从教学楼回宿舍哪条路更安全？"
  },
  "route": {
    "mode": "night",
    "origin": "教学楼",
    "destination": "宿舍",
    "distance_m": 407.7,
    "eta_min": 5.1,
    "safety_score": null,
    "route_geojson": {
      "type": "Feature",
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [114.6130, 30.4599],
          [114.6132, 30.4594],
          [114.6131, 30.4586]
        ]
      },
      "properties": {}
    },
    "steps": [
      {"seq": 1, "title": "从教学楼出发", "detail": "沿系统推荐路线前行。", "state": "start"},
      {"seq": 2, "title": "途经主步道", "detail": "照明覆盖良好。", "state": "safe"},
      {"seq": 3, "title": "到达宿舍", "detail": "路径结束。", "state": "end"}
    ],
    "reason": ["优先通过照明评分高的主步道。"],
    "is_mock": false
  },
  "facilities": [],
  "is_mock": false
}
```

**支持的问题类型**

| 问题示例 | 识别意图 | 触发服务 |
|----------|----------|----------|
| 晚上从教学楼回宿舍哪条路更安全？ | `night_safe_route` | 夜间路径规划 |
| 从图书馆去操场的无障碍路线怎么走？ | `accessible_route` | 无障碍路径规划 |
| 宿舍发生火灾，如何撤离到操场？ | `evacuation_route` | 应急撤离规划 |
| 吃完饭去便利店买笔记本再回宿舍 | `multi_stop_service_route` | 多目标路径规划 |
| 现在最近还开门的食堂在哪？ | `facility_query` | 设施检索 |
| 图书馆在哪里 | `navigation` | 设施检索 + 路径规划 |

---

### GET /route-night-safe — 夜间安全路径

优先照明评分高、开敞度好的路段。

```
GET /route-night-safe?origin=食堂&destination=图书馆
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin | string | ✅ | 出发地名称（需与数据库 poi.name 匹配） |
| destination | string | ✅ | 目的地名称 |
| user_lng | float | ❌ | 用户当前经度，提供后优先用作起点坐标 |
| user_lat | float | ❌ | 用户当前纬度 |

**响应字段说明**

| 字段 | 类型 | 说明 |
|------|------|------|
| distance_m | float | 路径总长度（米） |
| eta_min | float | 预计步行时间（分钟，按 80 m/min 计算） |
| route_geojson | object | 标准 GeoJSON Feature，geometry 为 LineString |
| steps | array | 路径步骤节点列表 |
| is_mock | bool | false 表示真实路网计算，true 表示降级 mock |

---

### GET /route-accessible — 无障碍路径

避开台阶（`barrier_free_score < 2` 的路段直接禁行），优先无障碍评分高的路段。

```
GET /route-accessible?origin=教学楼&destination=图书馆
```

参数同 `/route-night-safe`。

---

### GET /route-evacuation — 应急撤离路径

快速撤离至操场、校门等安全集结点，优先开敞、无障碍路段。

```
GET /route-evacuation?origin=宿舍&destination=操场
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin | string | ✅ | 出发地名称 |
| destination | string | ❌ | 目的地，不填时系统取最近撤离集结点 |
| user_lng | float | ❌ | 用户当前经度 |
| user_lat | float | ❌ | 用户当前纬度 |

---

### POST /route-multistop — 多目标串联路径

依次经过多个停靠点，返回总距离最优的串联路径。

**请求体**

```json
{
  "origin": "教学楼",
  "stops": ["第一食堂", "便利店"],
  "destination": "宿舍",
  "time_constraint": "22:00"
}
```

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin | string | ✅ | 出发地 |
| stops | array | ✅ | 中途停靠点，按顺序排列，至少 1 个 |
| destination | string | ✅ | 最终目的地 |
| time_constraint | string | ❌ | 时间约束，如 `"22:00"` |

---

### GET /facility-search — 设施检索

多条件设施查询，支持关键词、类型、夜间可用、撤离点、距离排序。

```
GET /facility-search?keyword=食堂&night_available=true&limit=5
```

| 参数 | 类型 | 说明 |
|------|------|------|
| keyword | string | 关键词，同时匹配 name / service_content / remark / keywords 字段 |
| facility_type | string | 类型筛选，见下方枚举 |
| night_available | bool | `true` 仅返回夜间可用设施 |
| is_evacuation_point | bool | `true` 仅返回撤离集结点（操场、校门） |
| user_lng / user_lat | float | 提供后返回结果按距离升序排列 |
| limit | int | 返回数量上限，默认 20，最大 100 |

**facility_type 枚举值**

| 值 | 说明 |
|----|------|
| `dormitory` | 宿舍 |
| `teaching_building` | 教学楼 |
| `library` | 图书馆 |
| `canteen` | 食堂 |
| `store` | 便利店 |
| `vending_machine` | 自动售货机 |
| `playground` | 操场（同时也是撤离集结点） |
| `gate` | 校门（同时也是撤离集结点） |
| `other` | 其他地标（对应数据库中的 landmark） |

**响应示例**

```json
{
  "success": true,
  "total": 3,
  "items": [
    {
      "facility_id": "129",
      "facility_name": "第一食堂",
      "facility_type": "canteen",
      "open_time": "06:30:00",
      "close_time": "22:00:00",
      "night_available": true,
      "is_evacuation_point": false,
      "coordinate": {"lng": 114.6132, "lat": 30.4579},
      "distance_m": 85.3
    }
  ]
}
```

---

### GET /facility-search/evacuation-points — 撤离集结点列表

返回所有操场和校门，按距离排序。

```
GET /facility-search/evacuation-points?user_lng=114.6132&user_lat=30.4580
```

---

### GET /facility-search/{facility_id} — 设施详情

按数据库 `poi_id` 获取单个设施完整信息。

```
GET /facility-search/129
```

---

## 前端对接说明

### 跨域配置

后端已配置 CORS，允许以下来源：

```
http://localhost:5173
http://127.0.0.1:5173
```

前端用 Vite 开发时默认运行在 5173 端口，直接 `fetch` 不会跨域报错。如果前端使用其他端口，需要修改 `.env` 中的 `CORS_ORIGINS` 并重启后端。

### 路径在地图上绘制

`route_geojson` 是标准 GeoJSON Feature，geometry 为 LineString，坐标系为 WGS84（EPSG:4326）。

Leaflet 绘制方式：

```javascript
// 接口返回的 route.route_geojson 直接传入
L.geoJSON(route.route_geojson, {
  style: { color: '#00b4d8', weight: 4, opacity: 0.8 }
}).addTo(map)
```

### 判断是否为真实数据

响应体中的 `is_mock` 字段：

- `false`：真实路网计算结果
- `true`：数据库异常或地名无法解析时的降级 mock 数据

前端可据此显示提示文字，例如"当前为演示数据"。

### 推荐调用流程

```
用户输入文字
  → POST /query  （自然语言入口，优先使用此接口）
    → 返回 parsed_task.intent 判断类型
    → 返回 route（如有）直接绘图
    → 返回 facilities（如有）显示设施卡片
```

直接调用具体路径接口适合场景：用户手动选择了出发地和目的地，不经过 LLM 解析。

---

## 常见问题与坑点

### 环境配置类

**Q：创建虚拟环境报 `Could not find platform independent libraries`**

原因：使用了 QGIS 或 ArcGIS 内置的 Python，`sys.prefix` 被设置为当前工作目录，标准库找不到。

解决：找到系统独立安装的 Python 路径，用完整路径创建虚拟环境：

```powershell
C:\Users\<用户名>\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\venv\hiq
```

---

**Q：`pip install` 成功，但启动时报 `ModuleNotFoundError: No module named 'fastapi'`**

原因：`pip install` 安装到了系统 Python，而启动时用的是虚拟环境的 Python。

解决：用虚拟环境的完整路径启动：

```powershell
C:\venv\hiq\Scripts\python.exe -m uvicorn app.main:app --reload
```

---

**Q：虚拟环境创建在中文路径下，`Scripts\python.exe` 不存在**

原因：Windows 对中文路径支持不完整，venv 创建流程中途失败。

解决：将虚拟环境创建在 `C:\venv\hiq` 等纯英文路径下，项目代码路径不受影响。

---

**Q：`.env` 文件修改后接口仍返回旧值**

原因：`python-dotenv` 在进程启动时读取一次 `.env`，修改后需要重启服务。

解决：`Ctrl + C` 停止服务，重新执行 uvicorn 启动命令。

---

### 数据库类

**Q：启动时日志显示 `数据库连接池启动失败`，健康检查返回 `db: disconnected`**

排查步骤：
1. 确认 PostgreSQL 服务正在运行（pgAdmin 4 能否正常连接）
2. 确认 `.env` 中 `DB_PASSWORD` 填写正确
3. 确认 `DB_NAME=campus_nav_db`，数据库名大小写敏感
4. 在 pgAdmin Query Tool 执行 `SELECT 1` 验证连接

---

**Q：设施检索返回空列表，但数据库里有数据**

原因：关键词大小写或全角/半角不匹配。数据库查询使用 `ILIKE` 忽略大小写，但全角字符（如中文括号）不会自动转换。

解决：检查数据库中 `nav.poi` 表的 `name` 字段，确认字段内容与搜索关键词一致。

---

**Q：路径规划接口返回 `is_mock: true`，并在日志中显示 `坐标解析失败`**

原因：`origin` 或 `destination` 参数传入的地名在数据库 `nav.poi` 表中找不到匹配记录，系统降级返回 mock 数据。

解决：
1. 先调用 `/facility-search?keyword=<地名>` 确认该地名是否存在于数据库
2. 使用数据库中 `poi.name` 字段的精确名称，或包含该名称的子串
3. 也可以通过 `user_lng` / `user_lat` 传入坐标，系统会就近匹配路网节点

---

**Q：路径接口报 500 错误，日志显示 `NetworkXNoPath`**

原因：起点和终点之间路网不连通，Dijkstra 找不到路径。通常是路网数据中部分路段的 `source_node` 或 `target_node` 为空，导致图不连通。

解决：在 pgAdmin 中执行以下 SQL 检查孤立节点：

```sql
SELECT COUNT(*) FROM nav.road_segment 
WHERE source_node IS NULL OR target_node IS NULL;
```

如果有空值，需要数据库同学补全拓扑关系。

---

### 接口调用类

**Q：调用 `/query` 接口，意图识别错误，路径规划结果不符合预期**

原因：DeepSeek 对模糊问题的理解不一定准确，尤其是口语化地名（如"喷泉那边"）。

解决：
1. 查看响应中的 `parsed_task` 字段，确认 `intent`、`origin`、`destination` 解析是否正确
2. 如果 `intent` 识别错误，可以直接调用对应的具体路径接口（如 `/route-night-safe`）绕过 LLM 解析
3. 持续优化 `services/llm.py` 中的 `SYSTEM_PROMPT`，补充更多地名示例

---

**Q：前端 `fetch` 请求报 CORS 错误**

原因：前端运行端口不在后端 CORS 白名单中。

解决：修改 `.env` 中的 `CORS_ORIGINS`，加入前端实际运行的地址：

```env
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000
```

修改后重启后端服务。

---

**Q：GET 接口传中文参数返回 422 错误**

原因：URL 中的中文需要进行 URL 编码（percent encoding）。

解决：前端使用 `encodeURIComponent()` 编码参数：

```javascript
const origin = encodeURIComponent('第一食堂')
const destination = encodeURIComponent('图书馆')
fetch(`http://127.0.0.1:8000/route-night-safe?origin=${origin}&destination=${destination}`)
```

---

## 模块说明

### db.py — 数据库连接池

使用 asyncpg 管理 PostgreSQL 连接池，在 FastAPI 应用启动时初始化，关闭时释放。

路由层通过 `get_pool()` 获取连接池，`services` 层通过 `async with pool.acquire() as conn` 执行 SQL。

### services/llm.py — 自然语言解析

调用 DeepSeek API 将用户问题解析为结构化的 `ParsedTask` 对象。

- `DEEPSEEK_API_KEY` 未配置时自动降级到本地关键词规则解析
- 模型调用 `temperature=0.0` 保证输出稳定性
- 正则提取 JSON 块，防止模型在 JSON 前后输出多余文字

### services/gis.py — 路径规划

从 `nav.road_segment` 和 `nav.road_node` 读取路网，在内存中构建 networkx 有向图。

路网图按模式缓存（进程内），首次请求时加载，后续请求直接复用。

成本函数：

| 模式 | 公式 |
|------|------|
| 夜间安全 | `length_m + (10 - lighting_score) × 30` |
| 无障碍 | `length_m + (10 - barrier_free_score) × 40`，评分 < 2 时权重 999999 |
| 应急撤离 | `length_m + (10 - emergency_evacuation_score) × 25` |
| 多目标 | 各段使用夜间安全成本，串联求和 |

地名解析流程：`poi.name` 模糊匹配 → 获取坐标 → 映射到最近路网节点 → Dijkstra 求最短路径。

任何步骤失败时自动降级返回 `mock_data.py` 中的 mock 路径，`is_mock` 字段置为 `true`。

### services/facility.py — 设施查询

直接查询 `nav.poi` 表，支持关键词（ILIKE 模糊匹配）、类型、夜间可用、撤离点等多条件组合筛选。

提供用户位置时，使用 Haversine 公式计算球面距离并按距离排序。

---

## 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| FastAPI 骨架 | ✅ 完成 | 所有接口可调用 |
| PostgreSQL 连接 | ✅ 完成 | asyncpg 连接池，启动/关闭正常 |
| 自然语言解析 | ✅ 完成 | DeepSeek API 已接入，有关键词规则兜底 |
| 设施检索 | ✅ 完成 | 真实数据，131 条 POI |
| 夜间安全路径 | ✅ 完成 | networkx 真实路网计算 |
| 无障碍路径 | ✅ 完成 | networkx 真实路网计算 |
| 应急撤离路径 | ✅ 完成 | networkx 真实路网计算 |
| 多目标路径 | ✅ 完成 | networkx 真实路网计算 |
| 异常降级 | ✅ 完成 | 数据库/LLM 异常自动降级 mock |
