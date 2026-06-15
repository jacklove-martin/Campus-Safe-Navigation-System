<template>
  <aside class="panel sidebar">
    <section class="sidebar-block sidebar-intro">
      <div class="section-head">
        <h2>任务面板</h2>
        <span class="pill" :class="loading ? 'pill-gold' : 'pill-emerald'">
          {{ loading ? 'Loading' : sourceLabel }}
        </span>
      </div>
      <p class="sidebar-note">
        通过自然语言输入、模式切换和图层控制，统一接入后端 GIS 与问答服务。
      </p>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>智能检索</h2>
        <span class="muted-mini">自然语言问答</span>
      </div>
      <textarea
        :value="query"
        class="smart-textarea"
        placeholder="请输入问题，例如：晚上从教学楼回宿舍哪条路更安全？"
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
          {{ loading ? '请求中...' : '解析问题' }}
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('reset')">重置输入</button>
      </div>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>场景模式</h2>
        <span class="muted-mini">分析模式切换</span>
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
          <p>{{ mode.description }}</p>
        </button>
      </div>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>地图图层</h2>
        <span class="muted-mini">可视化控制</span>
      </div>
      <div class="layer-list">
        <label v-for="layer in layers" :key="layer.id" class="layer-item rich">
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

    <section class="sidebar-block emergency-box">
      <div class="section-head">
        <h2>应急快捷操作</h2>
        <span class="pill pill-warm">高优先级</span>
      </div>
      <div class="emergency-actions">
        <button class="danger-button" :disabled="loading" @click="$emit('evacuation', 'gate')">
          一键疏散到最近校门
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('evacuation', 'playground')">
          切换最近操场
        </button>
        <button class="secondary-button" :disabled="loading" @click="$emit('evacuation', 'exit')">
          查看应急出口
        </button>
      </div>
    </section>
  </aside>
</template>

<script setup>
defineProps({
  query: {
    type: String,
    required: true
  },
  quickQuestions: {
    type: Array,
    required: true
  },
  modes: {
    type: Array,
    required: true
  },
  activeMode: {
    type: String,
    required: true
  },
  layers: {
    type: Array,
    required: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  sourceLabel: {
    type: String,
    default: 'Mock Data'
  }
})

defineEmits([
  'update:query',
  'select-question',
  'change-mode',
  'toggle-layer',
  'submit',
  'reset',
  'evacuation'
])
</script>
