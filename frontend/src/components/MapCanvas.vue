<template>
  <section class="panel map-panel">
    <div class="map-panel-top">
      <div>
        <p class="eyebrow">Live Spatial Canvas</p>
        <h2>校园空间态势图</h2>
      </div>
      <div class="toolbar-actions">
        <button class="mini-button active">夜间路线</button>
        <button class="mini-button">无障碍视图</button>
        <button class="mini-button">设施筛选</button>
      </div>
    </div>

    <div class="live-stat-strip">
      <article
        v-for="item in stats"
        :key="item.label"
        class="live-stat-card"
        :class="`tone-${item.tone}`"
      >
        <span>{{ item.label }}</span>
        <strong>{{ item.value }}</strong>
      </article>
    </div>

    <div class="map-stage editorial">
      <div class="terrain-shape terrain-a"></div>
      <div class="terrain-shape terrain-b"></div>
      <div class="grid-overlay"></div>

      <div class="route-band route-band-1"></div>
      <div class="route-band route-band-2"></div>

      <div class="map-chip building a">教学楼北门</div>
      <div class="map-chip building b">图书馆广场</div>
      <div class="map-chip building c">第一食堂</div>
      <div class="map-chip building d">一组团四栋</div>
      <div class="map-chip poi e">东门集结点</div>
      <div class="map-chip poi f">操场</div>
      <div class="map-chip hazard g">施工围挡</div>

      <svg class="route-svg" viewBox="0 0 1100 620" preserveAspectRatio="none">
        <defs>
          <linearGradient id="routeLine" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#0f7f6d" />
            <stop offset="48%" stop-color="#3b9d84" />
            <stop offset="100%" stop-color="#df9f39" />
          </linearGradient>
        </defs>
        <path
          d="M120 160 C220 165, 285 195, 355 248 S540 346, 645 338 S836 255, 980 220"
          fill="none"
          stroke="url(#routeLine)"
          stroke-linecap="round"
          stroke-width="18"
          stroke-dasharray="18 12"
        />
        <circle cx="120" cy="160" r="18" fill="#143f39" />
        <circle cx="980" cy="220" r="18" fill="#cc6b43" />
      </svg>

      <div class="route-summary-card editorial-card">
        <span class="route-tag">系统推荐</span>
        <strong>{{ summary.mode }}</strong>
        <p>{{ summary.title }}</p>
        <div class="route-metrics">
          <span>{{ summary.distance }}</span>
          <span>{{ summary.eta }}</span>
          <span>{{ summary.score }}</span>
        </div>
      </div>
    </div>

    <div class="timeline-card">
      <div class="section-head">
        <h2>路径时间线</h2>
        <span class="muted-mini">Route Timeline</span>
      </div>
      <div class="timeline-list">
        <article
          v-for="item in timeline"
          :key="`${item.time}-${item.title}`"
          class="timeline-item"
          :class="`state-${item.state}`"
        >
          <span class="timeline-time">{{ item.time }}</span>
          <div class="timeline-body">
            <strong>{{ item.title }}</strong>
            <p>{{ item.detail }}</p>
          </div>
        </article>
      </div>
    </div>
  </section>
</template>

<script setup>
defineProps({
  summary: {
    type: Object,
    required: true
  },
  stats: {
    type: Array,
    required: true
  },
  timeline: {
    type: Array,
    required: true
  }
})
</script>
