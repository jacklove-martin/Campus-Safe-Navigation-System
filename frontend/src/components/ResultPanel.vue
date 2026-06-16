<template>
  <aside class="panel result-panel ai-panel">
    <section class="result-block chat-block user-block compact-chat">
      <div class="section-head">
        <h2>输入内容</h2>
        <span class="pill pill-neutral">User</span>
      </div>
      <p class="chat-text">{{ query }}</p>
    </section>

    <section class="result-block chat-block ai-block compact-chat">
      <div class="section-head">
        <h2>AI 结果</h2>
        <span class="pill" :class="loading ? 'pill-gold' : 'pill-sky'">
          {{ loading ? '生成中' : summary.mode }}
        </span>
      </div>
      <h3>{{ summary.title }}</h3>
      <p class="facility-detail">{{ summary.message }}</p>
      <div class="summary-stats compact-stats">
        <div>
          <span class="metric-label">距离</span>
          <strong>{{ summary.distance }}</strong>
        </div>
        <div>
          <span class="metric-label">耗时</span>
          <strong>{{ summary.eta }}</strong>
        </div>
        <div>
          <span class="metric-label">评分</span>
          <strong>{{ summary.score }}</strong>
        </div>
      </div>
    </section>

    <section class="result-block compact-list-block">
      <div class="section-head">
        <h2>推荐理由</h2>
      </div>
      <ul class="reason-list compact-list">
        <li v-for="item in summary.reason" :key="item">{{ item }}</li>
      </ul>
    </section>

    <section class="result-block compact-list-block">
      <div class="section-head">
        <h2>路线</h2>
      </div>
      <ol class="step-list compact-list">
        <li v-for="step in summary.steps" :key="step">{{ step }}</li>
      </ol>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  summary: { type: Object, required: true },
  facilityCards: { type: Array, required: true },
  query: { type: String, default: '' },
  loading: { type: Boolean, default: false }
})
</script>
