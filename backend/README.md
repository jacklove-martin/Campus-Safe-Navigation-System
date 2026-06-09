# 后端开发文档

校园安全服务一体化智能导览系统 — 后端服务

## 目录

- [技术栈](#技术栈)
- [项目结构](#项目结构)
- [环境准备](#环境准备)
- [启动服务](#启动服务)
- [接口文档](#接口文档)
- [模块说明](#模块说明)
- [当前状态与后续计划](#当前状态与后续计划)

---

## 技术栈

| 组件 | 版本 | 说明 |
|------|------|------|
| Python | 3.12 | 运行环境 |
| FastAPI | 0.115.5 | Web 框架 |
| Uvicorn | 0.32.1 | ASGI 服务器 |
| Pydantic | 2.10.3 | 数据校验与序列化 |
| OpenAI SDK | 1.57.0 | DeepSeek API 调用（兼容 OpenAI 协议） |
| python-dotenv | 1.0.1 | 环境变量管理 |
| ArcPy | ArcGIS Pro 内置 | 路网分析（mdb 就绪后启用） |

---

## 项目结构

```
backend/
├── .env.example              # 环境变量模板，复制为 .env 后填写实际值
├── .env                      # 本地环境变量（已加入 .gitignore，不提交）
├── requirements.txt          # Python 依赖列表
├── README.md                 # 本文档
└── app/
    ├── main.py               # FastAPI 应用入口，注册路由、CORS、日志
    ├── config.py             # 从 .env 读取全局配置
    ├── models.py             # 所有请求/响应 Pydantic 模型及枚举定义
    ├── mock_data.py          # 过渡期 mock 数据（mdb 就绪后由真实数据替代）
    ├── routers/
    │   ├── query.py          # POST /query          自然语言问答统一入口
    │   ├── route.py          # GET  /route-*        四类路径分析接口
    │   └── facility.py       # GET  /facility-search 设施检索接口
    └── services/
        ├── llm.py            # DeepSeek API 调用 + 本地规则兜底解析
        ├── gis.py            # ArcPy 路径分析封装（含 mock 与真实两套逻辑）
        └── facility.py       # 设施查询逻辑（含距离计算）
```

---

## 环境准备

### 1. Python 环境要求

需要使用系统独立安装的 Python 3.12，**不能使用 QGIS/OSGeo4W 内置的 Python**。

确认方式：

```powershell
C:\Users\<你的用户名>\AppData\Local\Programs\Python\Python312\python.exe --version
```

### 2. 创建虚拟环境

由于项目路径含有中文，需将虚拟环境创建在纯英文路径下：

```powershell
# 创建目录
New-Item -ItemType Directory -Path C:\venv -Force

# 创建虚拟环境（替换为你自己的用户名）
C:\Users\<你的用户名>\AppData\Local\Programs\Python\Python312\python.exe -m venv C:\venv\hiq
```

### 3. 安装依赖

```powershell
C:\venv\hiq\Scripts\python.exe -m pip install -r requirements.txt
```

### 4. 配置环境变量

复制模板文件并填写实际值：

```powershell
copy .env.example .env
```

用文本编辑器打开 `.env`，填写以下字段：

```env
# DeepSeek API 配置
DEEPSEEK_API_KEY=你的_API_Key
DEEPSEEK_BASE_URL=https://api.deepseek.com
DEEPSEEK_MODEL=deepseek-chat

# CORS：前端开发地址
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# ArcGIS 数据库配置（mdb 就绪后填写）
MDB_PATH=
NETWORK_DATASET=
```

> `.env` 文件已加入 `.gitignore`，不会被提交到 GitHub，请勿将 API Key 提交至代码仓库。

---

## 启动服务

每次开发时在 PowerShell 中执行：

```powershell
cd "项目路径\backend"
C:\venv\hiq\Scripts\python.exe -m uvicorn app.main:app --reload
```

启动成功后访问：

- API 根地址：`http://127.0.0.1:8000`
- Swagger 交互文档：`http://127.0.0.1:8000/docs`
- 健康检查：`http://127.0.0.1:8000/health`

---

## 接口文档

### POST /query — 自然语言问答入口

接收用户自然语言输入，由 DeepSeek 解析意图后自动分发到对应服务，返回统一响应。

**请求体**

```json
{
  "text": "晚上从教学楼回一组团四栋哪条路更安全？",
  "user_location": {
    "lng": 114.3548,
    "lat": 30.5355
  }
}
```

**响应体**

```json
{
  "success": true,
  "message": "已为您规划夜间安全路径，全程约 640 米，预计步行 8 分钟，安全评分 92.0。",
  "parsed_task": {
    "intent": "night_safe_route",
    "origin": "教学楼A栋北门",
    "destination": "一组团四栋",
    "route_mode": "night"
  },
  "route": { ... },
  "facilities": [ ... ],
  "is_mock": true
}
```

**支持的问题类型示例**

| 问题示例 | 识别意图 |
|----------|----------|
| 晚上从教学楼回宿舍哪条路更安全？ | `night_safe_route` |
| 从图书馆去操场的无障碍路线怎么走？ | `accessible_route` |
| 宿舍发生火灾，如何撤离到操场？ | `evacuation_route` |
| 吃完饭去便利店买笔记本再回宿舍 | `multi_stop_service_route` |
| 现在最近还开门的食堂在哪？ | `facility_query` |

---

### GET /route-night-safe — 夜间安全路径

```
GET /route-night-safe?origin=教学楼A栋&destination=一组团四栋
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin | string | ✅ | 出发地名称 |
| destination | string | ✅ | 目的地名称 |
| user_lng | float | ❌ | 用户当前经度 |
| user_lat | float | ❌ | 用户当前纬度 |

---

### GET /route-accessible — 无障碍路径

```
GET /route-accessible?origin=教学楼A栋&destination=图书馆
```

参数同上。台阶路段直接禁行，其余按 `wheelchair_score` 计算成本。

---

### GET /route-evacuation — 应急撤离路径

```
GET /route-evacuation?origin=一组团四栋&destination=操场
```

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| origin | string | ✅ | 出发地名称 |
| destination | string | ❌ | 默认为"最近安全集结点" |
| user_lng | float | ❌ | 用户当前经度 |
| user_lat | float | ❌ | 用户当前纬度 |

---

### POST /route-multistop — 多目标串联路径

```json
{
  "origin": "教学楼A栋",
  "stops": ["第一食堂", "图书馆东侧便利店"],
  "destination": "一组团四栋",
  "time_constraint": "22:00"
}
```

---

### GET /facility-search — 设施检索

```
GET /facility-search?keyword=食堂&night_available=true
```

| 参数 | 类型 | 说明 |
|------|------|------|
| keyword | string | 关键词，匹配名称/别名/标签/备注 |
| facility_type | string | 类型筛选，见下方枚举 |
| night_available | bool | 是否夜间可用 |
| is_evacuation_point | bool | 是否为撤离集结点 |
| user_lng / user_lat | float | 提供后按距离排序 |
| limit | int | 返回数量上限，默认 20 |

**facility_type 枚举值**

| 值 | 说明 |
|----|------|
| `dormitory` | 宿舍 |
| `teaching_building` | 教学楼 |
| `library` | 图书馆 |
| `canteen` | 食堂 |
| `store` | 便利店 |
| `vending_machine` | 自动售货机 |
| `playground` | 操场 |
| `gate` | 校门 |
| `other` | 其他地标 |

---

### GET /facility-search/evacuation-points — 获取所有撤离集结点

```
GET /facility-search/evacuation-points?user_lng=114.36&user_lat=30.53
```

---

### GET /facility-search/{facility_id} — 按 ID 获取设施详情

```
GET /facility-search/f001
```

---

## 模块说明

### services/llm.py — 自然语言解析

调用 DeepSeek API 将用户输入解析为结构化任务对象 `ParsedTask`。

- API Key 未配置时自动降级到本地关键词规则解析（兜底逻辑）
- 解析结果包含：`intent`、`origin`、`destination`、`stops`、`facility_type`、`route_mode` 等字段

### services/gis.py — 路径分析

封装四类路径分析逻辑。当前返回 mock 数据，mdb 就绪后替换为 ArcPy Network Analyst 调用。

**mdb 就绪后的替换步骤：**

1. 在 `.env` 中填写 `MDB_PATH` 和 `NETWORK_DATASET`
2. 打开 `services/gis.py`，在对应函数中取消 ArcPy 代码块的注释
3. 删除该函数末尾的 mock 返回语句

### services/facility.py — 设施查询

提供多条件设施检索，支持关键词、类型、夜间可用、撤离点、距离排序等筛选条件。

mdb 就绪后将 `MOCK_FACILITIES` 替换为 `arcpy.SearchCursor` 或 SQLite 查询结果。

### mock_data.py — Mock 数据

过渡期使用的内存数据，包含：

- `MOCK_FACILITIES`：12 条示例设施数据（食堂、宿舍、图书馆、校门、操场等）
- `MOCK_ROUTES`：四类路径的示例结果（含 GeoJSON、步骤、推荐理由）

真实数据接入后此文件可保留用于单元测试。

---

## 当前状态与后续计划

### 当前状态

| 功能 | 状态 | 说明 |
|------|------|------|
| FastAPI 骨架 | ✅ 完成 | 所有接口可调用 |
| 自然语言解析 | ✅ 完成 | DeepSeek API 已接入 |
| 设施检索 | ✅ Mock 可用 | 等待真实 mdb 数据替换 |
| 夜间安全路径 | ✅ Mock 可用 | 等待 ArcPy 接入 |
| 无障碍路径 | ✅ Mock 可用 | 等待 ArcPy 接入 |
| 应急撤离路径 | ✅ Mock 可用 | 等待 ArcPy 接入 |
| 多目标串联路径 | ✅ Mock 可用 | 等待 ArcPy 接入 |
| ArcPy 路径分析 | ⏳ 待接入 | 等待数据库同学完成 mdb |

### 下一阶段计划

1. **接入真实 mdb 数据**：在 `services/gis.py` 中替换 mock 逻辑为 ArcPy Network Analyst 调用
2. **设施数据同步**：将 mdb 中的 `campus_facilities` 主表数据同步到后端查询层
3. **前端联调**：配合前端同学完成接口对接，替换前端 mock 数据
4. **Prompt 优化**：根据实际测试结果调整 DeepSeek 解析 Prompt
