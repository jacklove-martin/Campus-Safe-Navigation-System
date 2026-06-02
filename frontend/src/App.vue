<template>
  <div class="app-shell reset-shell">
    <div class="ambient ambient-left"></div>
    <div class="ambient ambient-right"></div>

    <AppHeader :active-mode-label="activeModeLabel" />

    <main class="dashboard-grid refined-layout">
      <ControlSidebar
        v-model:query="query"
        :quick-questions="quickQuestions"
        :modes="routeModes"
        :active-mode="activeMode"
        :layers="layers"
        @select-question="query = $event"
        @change-mode="activeMode = $event"
        @toggle-layer="toggleLayer"
      />

      <section class="workspace-column refined-workspace">
        <MapCanvas :summary="resultSummary" :stats="liveStats" :timeline="routeTimeline" />
        <StatusBoard :alerts="alerts" :scenarios="scenarioCards" />
      </section>

      <ResultPanel :summary="resultSummary" :facility-cards="facilityCards" />
    </main>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
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

const query = ref('晚上从教学楼北门回一组团四栋，哪条路更安全？')
const activeMode = ref('night')
const layers = ref(mapLayers)

const activeModeLabel = computed(() => {
  return routeModes.find((mode) => mode.id === activeMode.value)?.label ?? '夜间安全'
})

const toggleLayer = (id) => {
  layers.value = layers.value.map((layer) =>
    layer.id === id ? { ...layer, active: !layer.active } : layer
  )
}
</script>
