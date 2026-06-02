<template>
  <header class="hero-header panel">
    <div class="hero-copy-group">
      <div class="hero-kicker-row">
        <p class="eyebrow">Campus Safety Console</p>
        <span class="status-dot">前端演示版</span>
      </div>
      <h1>校园安全智能导览工作台</h1>
      <p class="hero-copy">
        面向夜间返宿、无障碍通行、应急撤离和服务设施检索的统一地图交互界面。
        当前页面为前端原型，已预留后续接入 GIS 分析与大模型问答的结构。
      </p>
    </div>

    <div class="hero-side">
      <div class="hero-mode-card">
        <span class="metric-label">当前模式</span>
        <strong>{{ activeModeLabel }}</strong>
        <small>路线分析与说明同步展示</small>
      </div>
      <div class="hero-actions">
        <button class="secondary-button">导出结果</button>
        <button class="primary-button">开始演示</button>
      </div>
    </div>
  </header>
</template>

<script setup>
defineProps({
  activeModeLabel: {
    type: String,
    required: true
  }
})
</script>
