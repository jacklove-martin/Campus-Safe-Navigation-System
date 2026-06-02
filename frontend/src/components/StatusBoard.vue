<template>
  <section class="status-board panel">
    <div class="section-head">
      <h2>场景快照</h2>
      <span class="muted-mini">System Snapshot</span>
    </div>

    <div class="scenario-grid">
      <article
        v-for="item in scenarios"
        :key="item.title"
        class="scenario-card"
        :class="`accent-${item.accent}`"
      >
        <strong>{{ item.title }}</strong>
        <p>{{ item.subtitle }}</p>
      </article>
    </div>

    <div class="section-head second">
      <h2>运行提醒</h2>
      <span class="muted-mini">Live Alerts</span>
    </div>

    <div class="alert-stack">
      <article v-for="item in alerts" :key="item.title" class="alert-card editorial">
        <div class="alert-top">
          <span class="pill" :class="pillClass(item.level)">{{ item.level }}</span>
          <strong>{{ item.title }}</strong>
        </div>
        <p>{{ item.text }}</p>
      </article>
    </div>
  </section>
</template>

<script setup>
const pillClass = (level) => {
  if (level === '应急') return 'pill-warm'
  if (level === '提示') return 'pill-gold'
  return 'pill-emerald'
}

defineProps({
  alerts: {
    type: Array,
    required: true
  },
  scenarios: {
    type: Array,
    required: true
  }
})
</script>
