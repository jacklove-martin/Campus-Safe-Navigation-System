<template>
  <aside class="panel result-panel">
    <section class="result-block highlight">
      <div class="section-head">
        <h2>响应摘要</h2>
        <span class="pill pill-sky">{{ summary.mode }}</span>
      </div>
      <h3>{{ summary.title }}</h3>
      <div class="summary-stats">
        <div>
          <span class="metric-label">步行距离</span>
          <strong>{{ summary.distance }}</strong>
        </div>
        <div>
          <span class="metric-label">预计耗时</span>
          <strong>{{ summary.eta }}</strong>
        </div>
        <div>
          <span class="metric-label">综合评分</span>
          <strong>{{ summary.score }}</strong>
        </div>
      </div>
    </section>

    <section class="result-block">
      <div class="section-head">
        <h2>推荐理由</h2>
      </div>
      <ul class="reason-list">
        <li v-for="item in summary.reason" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section class="result-block">
      <div class="section-head">
        <h2>路径说明</h2>
      </div>
      <ol class="step-list">
        <li v-for="step in summary.steps" :key="step">{{ step }}</li>
      </ol>
    </section>

    <section class="result-block">
      <div class="section-head">
        <h2>设施联动推荐</h2>
      </div>
      <div class="facility-list">
        <article v-for="card in facilityCards" :key="card.name" class="facility-card editorial">
          <div class="facility-topline">
            <div>
              <strong>{{ card.name }}</strong>
              <p class="facility-type">{{ card.type }}</p>
            </div>
            <span class="pill pill-neutral">{{ card.badge }}</span>
          </div>
          <p class="facility-status">{{ card.status }}</p>
          <p class="facility-detail">{{ card.detail }}</p>
        </article>
      </div>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  summary: {
    type: Object,
    required: true
  },
  facilityCards: {
    type: Array,
    required: true
  }
})
</script>
