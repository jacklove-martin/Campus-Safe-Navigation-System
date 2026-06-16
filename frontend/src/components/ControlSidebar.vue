<template>
  <aside class="panel sidebar" :class="{ compact }">
    <section class="sidebar-block">
      <div class="section-head">
        <h2>输入</h2>
        <span class="pill" :class="loading ? 'pill-gold' : 'pill-emerald'">
          {{ loading ? 'Loading' : sourceLabel }}
        </span>
      </div>
      <textarea
        :value="query"
        class="smart-textarea"
        placeholder="例如：晚上从教学楼回宿舍，哪条路更安全？"
        @input="$emit('update:query', $event.target.value)"
      />
      <div class="quick-list">
        <button
          v-for="question in quickQuestions"
          :key="question"
          class="ghost-chip"
          :disabled="loading"
          @click="$emit('select-question', question)"
        >
          {{ question }}
        </button>
      </div>
      <div class="primary-actions action-row">
        <button class="primary-button" :disabled="loading" @click="$emit('submit')">
          {{ loading ? '分析中...' : '发送' }}
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('reset')">重置</button>
      </div>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>模式</h2>
      </div>
      <div class="mode-stack">
        <button
          v-for="mode in modes"
          :key="mode.id"
          class="mode-panel"
          :class="[`accent-${mode.accent}`, { active: mode.id === activeMode }]"
          :disabled="loading"
          @click="$emit('change-mode', mode.id)"
        >
          <div class="mode-panel-top">
            <strong>{{ mode.label }}</strong>
            <span class="mode-icon">{{ mode.icon }}</span>
          </div>
        </button>
      </div>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>地图图层</h2>
      </div>
      <div class="layer-list">
        <label
          v-for="layer in layers"
          :key="layer.id"
          class="layer-item rich"
        >
          <div class="layer-main">
            <input
              type="checkbox"
              :checked="layer.active"
              :disabled="loading"
              @change="$emit('toggle-layer', layer.id)"
            />
            <div>
              <strong>{{ layer.label }}</strong>
              <p>{{ layer.hint }}</p>
            </div>
          </div>
          <span class="layer-state" :class="{ active: layer.active }">
            {{ layer.active ? '开' : '关' }}
          </span>
        </label>
      </div>
    </section>

    <section v-if="!compact" class="sidebar-block emergency-box">
      <div class="section-head">
        <h2>应急</h2>
      </div>
      <div class="emergency-actions">
        <button class="danger-button" :disabled="loading" @click="$emit('evacuation', 'gate')">
          最近校门
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('evacuation', 'playground')">
          最近操场
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('evacuation', 'exit')">
          应急出口
        </button>
      </div>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  query: { type: String, required: true },
  quickQuestions: { type: Array, required: true },
  modes: { type: Array, required: true },
  activeMode: { type: String, required: true },
  layers: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  sourceLabel: { type: String, default: 'Mock Data' },
  compact: { type: Boolean, default: false }
})

defineEmits(['update:query', 'select-question', 'change-mode', 'toggle-layer', 'submit', 'reset', 'evacuation'])
</script>
