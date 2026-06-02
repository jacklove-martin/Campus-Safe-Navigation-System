<template>
  <aside class="panel sidebar">
    <section class="sidebar-block sidebar-intro">
      <div class="section-head">
        <h2>任务面板</h2>
        <span class="pill pill-emerald">Mock Data</span>
      </div>
      <p class="sidebar-note">
        通过自然语言输入、模式切换和图层控制，模拟后续接入 LLM 与 GIS 的统一入口。
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
          @click="$emit('select-question', question)"
        >
          {{ question }}
        </button>
      </div>
      <div class="primary-actions action-row">
        <button class="primary-button">解析问题</button>
        <button class="secondary-button">重置输入</button>
      </div>
    </section>

    <section class="sidebar-block">
      <div class="section-head">
        <h2>场景模式</h2>
        <span class="muted-mini">分析模型切换</span>
      </div>
      <div class="mode-stack">
        <button
          v-for="mode in modes"
          :key="mode.id"
          class="mode-panel"
          :class="[`accent-${mode.accent}`, { active: mode.id === activeMode }]"
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
        <button class="danger-button">一键撤离到最近校门</button>
        <button class="secondary-button">切换最近操场</button>
        <button class="secondary-button">查看应急出口</button>
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
  }
})

defineEmits(['update:query', 'select-question', 'change-mode', 'toggle-layer'])
</script>
