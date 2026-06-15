<template>
  <header class="hero-header panel">
    <div class="hero-copy-group">
      <div class="hero-kicker-row">
        <p class="eyebrow">Campus Safety Console</p>
        <span class="status-dot">{{ backendStatus }}</span>
      </div>
      <h1>校园安全智能导览工作台</h1>
      <p class="hero-copy">
        面向夜间返宿、无障碍通行、应急疏散和服务设施检索的统一地图交互界面。
        当前页面已接入后端接口，可根据真实返回结果刷新路线与设施信息。
      </p>
    </div>

    <div class="hero-side">
      <div class="hero-mode-card">
        <span class="metric-label">当前模式</span>
        <strong>{{ activeModeLabel }}</strong>
        <small>{{ message }}</small>
      </div>
      <div class="hero-actions">
        <button class="secondary-button" :disabled="loading">导出结果</button>
        <button class="primary-button" :disabled="loading">{{ loading ? '请求中...' : '开始分析' }}</button>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
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
    default: '路线分析与结果说明会在这里同步展示'
  },
  loading: {
    type: Boolean,
    default: false
  }
})
</script>
