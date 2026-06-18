<template>
  <section class="assistant-chat-shell">
    <div class="assistant-chat-topbar">
      <select
        class="mode-select"
        :value="activeMode"
        :disabled="loading"
        aria-label="选择导航模式"
        @change="$emit('change-mode', $event.target.value)"
      >
        <option v-for="mode in modes" :key="mode.id" :value="mode.id">
          {{ mode.label }}
        </option>
      </select>

      <button
        class="mini-button clear-history-button"
        type="button"
        :disabled="!messages.length && !loading"
        @click="$emit('clear-history')"
      >
        清除记录
      </button>
    </div>

    <div v-if="messages.length" class="chat-thread history-thread">
      <template v-for="item in messages" :key="item.id">
        <article class="message-row user-row">
          <div class="avatar-badge user-avatar">你</div>
          <div class="message-bubble user-bubble">
            <p class="chat-text">{{ item.userText }}</p>
          </div>
        </article>

        <article class="message-row assistant-row">
          <div class="avatar-badge assistant-avatar">AI</div>
          <div class="message-bubble assistant-bubble">
            <div class="message-meta">
              <strong>校园安全助手</strong>
              <span class="pill pill-sky">{{ item.assistant.mode }}</span>
            </div>

            <h3>{{ item.assistant.title }}</h3>
            <p class="chat-text">{{ item.assistant.message }}</p>

            <div class="reply-stats">
              <div>
                <span class="metric-label">距离</span>
                <strong>{{ item.assistant.distance }}</strong>
              </div>
              <div>
                <span class="metric-label">耗时</span>
                <strong>{{ item.assistant.eta }}</strong>
              </div>
              <div>
                <span class="metric-label">评分</span>
                <strong>{{ item.assistant.score }}</strong>
              </div>
            </div>

            <div class="reply-section">
              <span class="reply-label">推荐理由</span>
              <ul class="reply-list">
                <li v-for="reason in item.assistant.reason" :key="reason">{{ reason }}</li>
              </ul>
            </div>

            <div class="reply-section">
              <span class="reply-label">路线步骤</span>
              <ol class="reply-list ordered">
                <li v-for="step in item.assistant.steps" :key="step">{{ step }}</li>
              </ol>
            </div>

            <div v-if="item.assistant.hasRoute" class="route-action-row">
              <button class="mini-button route-link-button" type="button" @click="$emit('view-route')">
                点击地图查看具体路线
              </button>
            </div>
          </div>
        </article>
      </template>

      <article v-if="loading" class="message-row assistant-row pending-row">
        <div class="avatar-badge assistant-avatar">AI</div>
        <div class="message-bubble assistant-bubble pending-bubble">
          <div class="message-meta">
            <strong>校园安全助手</strong>
            <span class="pill pill-gold">思考中</span>
          </div>
          <p class="chat-text typing-text">正在分析你的问题，准备路线建议与安全说明...</p>
        </div>
      </article>
    </div>

    <div v-else class="assistant-empty-state">
      <h2>开始对话</h2>
      <p>询问校园导航、安全避险、疏散路径或设施位置。</p>
    </div>

    <div class="suggestion-row">
      <button
        v-for="question in quickQuestions"
        :key="question"
        class="suggestion-chip"
        type="button"
        :disabled="loading"
        @click="$emit('select-question', question)"
      >
        {{ question }}
      </button>
    </div>

    <form class="composer-panel clean-composer" @submit.prevent="handleSubmit">
      <textarea
        :value="query"
        class="composer-input"
        rows="3"
        placeholder="输入你的问题，例如：从图书馆到宿舍，夜间更安全的路线是什么？"
        @input="$emit('update:query', $event.target.value)"
      ></textarea>
      <div class="composer-actions">
        <button class="primary-button" type="submit" :disabled="loading || !query.trim()">
          {{ loading ? '发送中...' : '发送' }}
        </button>
      </div>
    </form>
  </section>
</template>

<script setup>
const props = defineProps({
  messages: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  query: {
    type: String,
    default: ''
  },
  modes: {
    type: Array,
    default: () => []
  },
  activeMode: {
    type: String,
    default: ''
  },
  quickQuestions: {
    type: Array,
    default: () => []
  }
})

const emit = defineEmits([
  'update:query',
  'submit',
  'clear-history',
  'view-route',
  'change-mode',
  'select-question'
])

function handleSubmit() {
  if (!props.query.trim() || props.loading) {
    return
  }

  emit('submit', props.query)
}
</script>
