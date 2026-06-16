<template>
  <header class="hero-header panel compact-header">
    <div class="hero-copy-group">
      <div class="hero-kicker-row">
        <p class="eyebrow">Campus Safety Console</p>
        <span class="status-dot">{{ backendStatus }}</span>
      </div>
      <h1>校园安全智能导览</h1>
      <p class="hero-copy">输入问题，快速生成路线建议与安全说明。</p>
    </div>

    <div class="hero-side compact-side">
      <div class="hero-mode-card">
        <span class="metric-label">当前模式</span>
        <strong>{{ activeModeLabel }}</strong>
        <small>{{ message }}</small>
      </div>

      <div class="view-switch">
        <button
          class="mini-button"
          :class="{ active: activeView === 'assistant' }"
          :disabled="loading"
          @click="$emit('change-view', 'assistant')"
        >
          AI 助手
        </button>
        <button
          class="mini-button"
          :class="{ active: activeView === 'map' }"
          :disabled="loading"
          @click="$emit('change-view', 'map')"
        >
          地图
        </button>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  activeView: {
    type: String,
    default: 'assistant'
  },
  activeModeLabel: {
    type: String,
    required: true
  },
  backendStatus: {
    type: String,
    default: '后端未连接'
  },
  message: {
    type: String,
    default: '等待分析结果'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

defineEmits(['change-view'])
</script>
