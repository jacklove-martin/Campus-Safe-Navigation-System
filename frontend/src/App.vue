<template>
  <div class="app-shell reset-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <AppHeader
      :active-view="activeView"
      :active-mode-label="activeModeLabel"
      :backend-status="backendStatus"
      :message="headerMessage"
      :loading="loading"
      @change-view="activeView = $event"
    />

    <main v-if="activeView === 'assistant'" class="assistant-layout">
      <ResultPanel
        :messages="chatMessages"
        :loading="loading"
        :query="query"
        :modes="routeModes"
        :active-mode="activeMode"
        :quick-questions="quickQuestions"
        @update:query="query = $event"
        @submit="handleSubmit"
        @clear-history="clearConversation"
        @view-route="openRouteOnMap"
        @change-mode="activeMode = $event"
        @select-question="query = $event"
      />
    </main>

    <main v-else class="dashboard-grid refined-layout">
      <ControlSidebar
        v-model:query="query"
        :quick-questions="quickQuestions"
        :modes="routeModes"
        :active-mode="activeMode"
        :layers="layers"
        :loading="loading"
        :source-label="dataSourceLabel"
        compact
        @select-question="query = $event"
        @change-mode="activeMode = $event"
        @toggle-layer="toggleLayer"
        @submit="handleSubmit"
        @reset="resetToMock"
        @evacuation="handleEmergency"
      />

      <section class="workspace-column refined-workspace">
        <MapCanvas
          :summary="uiSummary"
          :stats="uiStats"
          :timeline="uiTimeline"
          :layers="layers"
          :route-geojson="currentRouteGeojson"
          :facilities="currentFacilities"
          :map-layers="mapLayerData"
          :focus-route-token="focusRouteToken"
        />
        <StatusBoard :alerts="uiAlerts" :scenarios="scenarioCards" />
      </section>
    </main>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import AppHeader from './components/AppHeader.vue'
import ControlSidebar from './components/ControlSidebar.vue'
import MapCanvas from './components/MapCanvas.vue'
import ResultPanel from './components/ResultPanel.vue'
import StatusBoard from './components/StatusBoard.vue'
import {
  alerts,
  facilityCards,
  liveStats,
  mapLayers,
  quickQuestions,
  resultSummary,
  routeModes,
  routeTimeline,
  scenarioCards
} from './mock/data'
import { fetchCampusBuildings, fetchHealth, fetchMapLayer, submitSmartQuery } from './services/api'

const defaultQuery = '晚上从教学楼北门回一组团四栋，哪条路更安全？'

const query = ref('')
const activeMode = ref('night')
const activeView = ref('assistant')
const layers = ref(mapLayers)
const loading = ref(false)
const backendHealthy = ref(false)
const backendDbStatus = ref('unknown')
const serverVersion = ref('')
const lastMessage = ref('当前显示的是前端默认数据。')
const usingMockFallback = ref(true)
const currentSummary = ref(structuredClone(resultSummary))
const currentStats = ref(structuredClone(liveStats))
const currentTimeline = ref(structuredClone(routeTimeline))
const currentFacilityCards = ref(structuredClone(facilityCards))
const currentAlerts = ref(structuredClone(alerts))
const currentRouteGeojson = ref(null)
const currentFacilities = ref([])
const chatMessages = ref([])
const focusRouteToken = ref(0)
const mapLayerData = ref({
  buildings: null,
  roads: null,
  hazards: null,
  assembly: null,
  facilities: null
})

const modeLabelMap = {
  night: '夜间安全路径',
  accessible: '无障碍路径',
  evacuation: '应急疏散路径',
  multi: '多目标导航'
}

const modeIntentKeywords = {
  night: '夜间安全',
  accessible: '无障碍',
  evacuation: '应急疏散',
  multi: '多目标'
}

const facilityQuestionKeywords = ['在哪', '哪里', '开门', '营业', '几点', '有没有', '最近', '食堂', '便利店', '超市', '售货机']
const routeQuestionKeywords = ['从', '到', '去', '回', '怎么走', '导航', '路线', '哪条路', '疏散', '撤离', '无障碍', '安全']

const activeModeLabel = computed(() => {
  return routeModes.find((mode) => mode.id === activeMode.value)?.label ?? '夜间安全'
})

const backendStatus = computed(() => {
  if (loading.value) {
    return '正在请求后端'
  }

  if (!backendHealthy.value) {
    return '后端未连接'
  }

  if (backendDbStatus.value === 'connected') {
    return `后端在线 · DB 已连接`
  }

  return `后端在线 · DB ${backendDbStatus.value}`
})

const headerMessage = computed(() => {
  if (serverVersion.value) {
    return `${lastMessage.value} · API ${serverVersion.value}`
  }

  return lastMessage.value
})

const dataSourceLabel = computed(() => {
  if (loading.value) {
    return 'Loading'
  }

  return usingMockFallback.value ? 'Mock Data' : 'API Live'
})

const uiSummary = computed(() => currentSummary.value)
const uiStats = computed(() => currentStats.value)
const uiTimeline = computed(() => currentTimeline.value)
const uiFacilityCards = computed(() => currentFacilityCards.value)
const uiAlerts = computed(() => currentAlerts.value)

function cloneDefaults() {
  currentSummary.value = structuredClone(resultSummary)
  currentStats.value = structuredClone(liveStats)
  currentTimeline.value = structuredClone(routeTimeline)
  currentFacilityCards.value = structuredClone(facilityCards)
  currentAlerts.value = structuredClone(alerts)
  currentRouteGeojson.value = null
  currentFacilities.value = []
  chatMessages.value = []
}

function clearConversation() {
  chatMessages.value = []
}

function openRouteOnMap() {
  activeView.value = 'dashboard'
  focusRouteToken.value += 1
}

function toggleLayer(id) {
  layers.value = layers.value.map((layer) =>
    layer.id === id ? { ...layer, active: !layer.active } : layer
  )
}

function formatDistance(distance) {
  if (typeof distance !== 'number') {
    return '暂无'
  }

  return `${Math.round(distance)} 米`
}

function formatEta(eta) {
  if (typeof eta !== 'number') {
    return '暂无'
  }

  return `${Math.max(1, Math.round(eta))} 分钟`
}

function formatScore(score) {
  if (typeof score !== 'number') {
    return '待评估'
  }

  return `安全评分 ${Math.round(score)}`
}

function mapRouteSteps(route) {
  if (!route?.steps?.length) {
    return structuredClone(routeTimeline)
  }

  return route.steps.map((step, index) => ({
    time: `${String(index * 2).padStart(2, '0')}:${String((index * 10) % 60).padStart(2, '0')}`,
    title: step.title,
    detail: step.detail,
    state: step.state || 'normal'
  }))
}

function mapFacilities(facilities) {
  if (!facilities?.length) {
    return structuredClone(facilityCards)
  }

  return facilities.slice(0, 3).map((item) => ({
    name: item.facility_name,
    type: item.facility_type,
    status: item.night_available ? '夜间可用' : '常规时段',
    badge: item.is_evacuation_point ? '疏散' : '推荐',
    detail: item.distance_m
      ? `距离当前位置约 ${Math.round(item.distance_m)} 米。`
      : item.remark || '已从后端设施检索结果中载入。'
  }))
}

function mapAlerts(message, route, facilities, isMock) {
  const nextAlerts = [
    {
      level: isMock ? '提示' : '正常',
      title: isMock ? '当前为演示结果' : '后端结果已同步',
      text: message || '系统已完成本次分析。'
    }
  ]

  if (route?.is_mock) {
    nextAlerts.push({
      level: '提示',
      title: '路线使用降级数据',
      text: '后端返回了 mock 路线，通常表示数据库或地名匹配暂未成功。'
    })
  }

  if (facilities?.length) {
    nextAlerts.push({
      level: '正常',
      title: '设施联动已更新',
      text: `本次共返回 ${facilities.length} 个相关设施结果。`
    })
  }

  if (!facilities?.length && !route) {
    nextAlerts.push({
      level: '应急',
      title: '建议补充更具体的问题',
      text: '可以直接写出出发地和目的地，例如“从图书馆到一食堂怎么走”。'
    })
  }

  return nextAlerts
}

function buildStats(route, facilities, isMock) {
  return [
    { label: '当前模式', value: activeModeLabel.value, tone: 'teal' },
    { label: '数据来源', value: isMock ? 'Mock' : 'API', tone: 'sky' },
    { label: '设施结果', value: `${facilities?.length ?? 0} 条`, tone: 'gold' },
    { label: '路径状态', value: route ? '已生成' : '待补充', tone: route ? 'coral' : 'teal' }
  ]
}

function mapSummaryFromResponse(data) {
  const route = data.route
  const facilities = data.facilities ?? []
  const isMock = data.is_mock ?? route?.is_mock ?? true
  const origin = route?.origin || data.parsed_task?.origin || '当前位置'
  const destination = route?.destination || data.parsed_task?.destination || '目标地点'

  currentSummary.value = {
    title: `${origin} → ${destination}`,
    mode: modeLabelMap[activeMode.value] || activeModeLabel.value,
    eta: formatEta(route?.eta_min),
    distance: formatDistance(route?.distance_m),
    score: formatScore(route?.safety_score),
    message: data.message || '后端已返回结果。',
    dataSource: isMock ? 'Mock Fallback' : 'Backend API',
    originLabel: origin,
    midpointLabel: route?.steps?.[1]?.title || '路径中段',
    facilityLabel: facilities[0]?.facility_name || '联动设施',
    destinationLabel: destination,
    poiLabel: facilities.find((item) => item.is_evacuation_point)?.facility_name || '疏散点',
    hazardLabel: route?.is_mock ? '待确认风险区' : '已避让风险区',
    reason: route?.reason?.length ? route.reason : ['后端已完成意图解析，但暂未返回详细推荐理由。'],
    steps: route?.steps?.length
      ? route.steps.map((step) => `${step.seq}. ${step.title}：${step.detail}`)
      : ['本次返回未包含路径步骤，可结合设施结果继续细化提问。']
  }

  currentTimeline.value = mapRouteSteps(route)
  currentFacilityCards.value = mapFacilities(facilities)
  currentStats.value = buildStats(route, facilities, isMock)
  currentAlerts.value = mapAlerts(data.message, route, facilities, isMock)
  currentRouteGeojson.value = route?.route_geojson ?? null
  currentFacilities.value = facilities
  usingMockFallback.value = isMock
  lastMessage.value = data.message || '后端已返回结果。'
}

function createConversationTurn(userText, summary) {
  const routeGeojson = currentRouteGeojson.value
  const hasRoute = routeGeojson?.type === 'FeatureCollection'
    ? routeGeojson.features?.some((feature) => Boolean(feature?.geometry?.coordinates?.length))
    : Boolean(routeGeojson?.geometry?.coordinates?.length)

  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    userText,
    assistant: {
      title: summary.title,
      mode: summary.mode,
      message: summary.message,
      distance: summary.distance,
      eta: summary.eta,
      score: summary.score,
      reason: [...(summary.reason ?? [])],
      steps: [...(summary.steps ?? [])],
      hasRoute
    }
  }
}

function resetToMock() {
  query.value = ''
  cloneDefaults()
  usingMockFallback.value = true
  lastMessage.value = backendHealthy.value
    ? '已重置为前端默认展示数据。'
    : '后端尚未连接，已恢复前端默认展示数据。'
}

async function refreshHealth() {
  try {
    const health = await fetchHealth()
    backendHealthy.value = health?.status === 'ok'
    backendDbStatus.value = health?.db || 'unknown'
    serverVersion.value = health?.version || ''
  } catch {
    backendHealthy.value = false
    backendDbStatus.value = 'disconnected'
    serverVersion.value = ''
  }
}

async function refreshMapLayers() {
  try {
    const [roads, hazards, assembly, facilities] = await Promise.all([
      fetchMapLayer('roads'),
      fetchMapLayer('hazards'),
      fetchMapLayer('assembly-points'),
      fetchMapLayer('facilities')
    ])

    const layerBounds = deriveMapBounds({
      roads,
      hazards,
      assembly,
      facilities
    })

    const buildings = await fetchCampusBuildings(layerBounds, {
      roads,
      hazards,
      assembly,
      facilities
    })

    mapLayerData.value = {
      buildings,
      roads,
      hazards,
      assembly,
      facilities
    }
  } catch (error) {
    currentAlerts.value = [
      {
        level: '提示',
        title: '地图图层加载失败',
        text: error instanceof Error ? error.message : '无法加载道路网、风险点或疏散点图层。'
      },
      ...currentAlerts.value
    ]
  }
}

function deriveMapBounds(layers) {
  const points = []

  function collectCoordinates(coordinates) {
    if (!Array.isArray(coordinates)) {
      return
    }

    if (typeof coordinates[0] === 'number' && typeof coordinates[1] === 'number') {
      points.push(coordinates)
      return
    }

    coordinates.forEach(collectCoordinates)
  }

  Object.values(layers).forEach((layer) => {
    if (layer?.type === 'FeatureCollection') {
      layer.features.forEach((feature) => collectCoordinates(feature.geometry?.coordinates))
    } else if (layer?.type === 'Feature') {
      collectCoordinates(layer.geometry?.coordinates)
    }
  })

  if (!points.length) {
    return null
  }

  const lngs = points.map((item) => item[0])
  const lats = points.map((item) => item[1])
  const padding = 0.0015

  return {
    west: Math.min(...lngs) - padding,
    east: Math.max(...lngs) + padding,
    south: Math.min(...lats) - padding,
    north: Math.max(...lats) + padding
  }
}

function normalizePromptByMode(text, mode) {
  const trimmed = text.trim()

  if (!trimmed) {
    return defaultQuery
  }

  const hint = modeIntentKeywords[mode]
  if (trimmed.includes(hint)) {
    return trimmed
  }

  const looksLikeFacilityQuestion = facilityQuestionKeywords.some((keyword) => trimmed.includes(keyword))
  const looksLikeRouteQuestion = routeQuestionKeywords.some((keyword) => trimmed.includes(keyword))
  if (looksLikeFacilityQuestion && !looksLikeRouteQuestion) {
    return trimmed
  }

  return `${hint}：${trimmed}`
}

async function handleSubmit(submittedQuery = query.value) {
  loading.value = true
  const nextQuery = typeof submittedQuery === 'string' ? submittedQuery : query.value
  query.value = nextQuery
  const originalQuery = nextQuery.trim() || defaultQuery
  const normalizedText = normalizePromptByMode(originalQuery, activeMode.value)

  try {
    const payload = {
      text: normalizedText
    }

    const data = await submitSmartQuery(payload)
    await refreshHealth()
    mapSummaryFromResponse(data)
    chatMessages.value = [...chatMessages.value, createConversationTurn(originalQuery, currentSummary.value)]
  } catch (error) {
    usingMockFallback.value = true
    lastMessage.value = error instanceof Error ? error.message : '请求失败，已保留默认演示数据。'
    currentAlerts.value = [
      {
        level: '应急',
        title: '后端请求失败',
        text: lastMessage.value
      },
      ...structuredClone(alerts).slice(0, 2)
    ]
    chatMessages.value = [
      ...chatMessages.value,
      createConversationTurn(originalQuery, {
        title: '请求失败',
        mode: activeModeLabel.value,
        message: lastMessage.value,
        distance: '暂无',
        eta: '暂无',
        score: '待重试',
        reason: ['本次请求未成功完成，请检查后端连接或稍后重试。'],
        steps: ['你可以重新发送问题，或换一种更明确的表达。']
      })
    ]
  } finally {
    loading.value = false
  }
}

function handleEmergency(target) {
  activeMode.value = 'evacuation'

  if (target === 'gate') {
    query.value = '如果现在需要紧急撤离，带我去最近校门'
  } else if (target === 'playground') {
    query.value = '发生突发情况时，去最近操场的疏散路线是什么'
  } else {
    query.value = '帮我查看附近可用的应急出口和疏散点'
  }

  handleSubmit()
}

onMounted(async () => {
  cloneDefaults()
  await refreshHealth()
  await refreshMapLayers()
})
</script>
