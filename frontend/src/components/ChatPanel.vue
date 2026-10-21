<template>
  <div class="chat-panel">
    <div ref="msgBox" class="messages">
      <div v-for="(m, i) in messages" :key="i" class="msg" :class="m.role">
        <div class="avatar">{{ m.role === 'user' ? '👤' : '🤖' }}</div>
        <div class="bubble">
          <div v-if="m.role === 'assistant'" class="md" v-html="renderMd(m.content)"></div>
          <div v-else class="plain">{{ m.content }}</div>
          <div v-if="m.sources && m.sources.length" class="sources">
            <div class="src-title">📎 引用来源</div>
            <div v-for="(s, j) in m.sources" :key="j" class="src-item" @click="jumpSource(s, j)">
              <div class="src-name">来源 {{ j + 1 }}：{{ s.source }}<span v-if="s.page"> · 第 {{ s.page }} 页</span></div>
              <div class="src-content">{{ s.content.slice(0, 120) }}…</div>
            </div>
          </div>
        </div>
      </div>

      <div v-if="streaming" class="msg assistant">
        <div class="avatar">🤖</div>
        <div class="bubble">
          <div class="md" v-html="renderMd(streamText || '💭 正在检索知识库并生成回答…')"></div>
        </div>
      </div>
    </div>

    <div class="input-bar">
      <el-input
        v-model="input"
        placeholder="基于知识库内容提问，回车发送…"
        size="large"
        :disabled="streaming"
        @keyup.enter="send"
      />
      <el-button type="primary" size="large" :loading="streaming" @click="send">发送</el-button>
      <el-button size="large" @click="clear">清空</el-button>
    </div>

    <el-dialog v-model="sourceDialog" title="引用来源原文" width="640px">
      <div class="src-full">{{ currentSource?.content }}</div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { marked } from 'marked'
import { streamChat } from '../api/chat'
import { useChatStore } from '../stores/chat'
import { useConfigStore } from '../stores/config'

const props = defineProps({
  kbId: { type: [Number, String], required: true },
})

const chatStore = useChatStore()
const configStore = useConfigStore()

const msgBox = ref(null)
const messages = ref([])
const input = ref('')
const streaming = ref(false)
const streamText = ref('')
const sourceDialog = ref(false)
const currentSource = ref(null)

onMounted(async () => {
  messages.value = chatStore.getHistory(props.kbId)
  if (!configStore.loaded) await configStore.load()
  scrollToBottom()
})

function renderMd(text) {
  // marked 渲染 Markdown（生产环境建议引入 DOMPurify 做 XSS 过滤）
  return marked.parse(text || '')
}

async function send() {
  const q = input.value.trim()
  if (!q || streaming.value) return
  input.value = ''

  messages.value.push({ role: 'user', content: q })
  chatStore.addMessage(props.kbId, { role: 'user', content: q })

  // 多轮上下文：取当前消息之前的最近几轮
  const history = messages.value
    .slice(0, -1)
    .map((m) => ({ role: m.role, content: m.content }))

  streaming.value = true
  streamText.value = ''

  const answerParts = []
  let sources = []

  await streamChat(
    {
      kb_id: props.kbId,
      question: q,
      history,
      config: configStore.config,
    },
    {
      onToken: (t) => {
        streamText.value += t
        answerParts.push(t)
        scrollToBottom()
      },
      onSources: (ev) => {
        sources = ev.sources || []
      },
      onDone: () => {
        const answer = answerParts.join('')
        messages.value.push({ role: 'assistant', content: answer, sources })
        chatStore.addMessage(props.kbId, { role: 'assistant', content: answer, sources })
        streaming.value = false
        streamText.value = ''
        scrollToBottom()
      },
      onError: (msg) => {
        const answer = `❌ ${msg}`
        messages.value.push({ role: 'assistant', content: answer })
        chatStore.addMessage(props.kbId, { role: 'assistant', content: answer })
        streaming.value = false
        streamText.value = ''
        ElMessage.error(msg)
      },
    },
  )

  // 兜底：若流异常未触发 done/error
  if (streaming.value) {
    streaming.value = false
    streamText.value = ''
  }
}

function clear() {
  messages.value = []
  chatStore.clear(props.kbId)
}

function jumpSource(s, idx) {
  currentSource.value = s
  sourceDialog.value = true
}

function scrollToBottom() {
  nextTick(() => {
    if (msgBox.value) msgBox.value.scrollTop = msgBox.value.scrollHeight
  })
}
</script>

<style scoped>
.chat-panel { display: flex; flex-direction: column; height: calc(100vh - 200px); }
.messages { flex: 1; overflow-y: auto; padding: 16px; background: #fff; border-radius: 8px; }
.msg { display: flex; gap: 10px; margin-bottom: 16px; }
.msg.user { flex-direction: row-reverse; }
.avatar { width: 36px; height: 36px; border-radius: 50%; background: #f0f4ff; display: flex; align-items: center; justify-content: center; font-size: 18px; flex-shrink: 0; }
.bubble { max-width: 75%; padding: 10px 14px; border-radius: 10px; }
.msg.user .bubble { background: #667eea; color: #fff; }
.msg.assistant .bubble { background: #f5f7fa; }
.plain { white-space: pre-wrap; }
.md { line-height: 1.6; }
.sources { margin-top: 10px; border-top: 1px dashed #ddd; padding-top: 8px; }
.src-title { font-weight: 600; font-size: 13px; margin-bottom: 6px; color: #667eea; }
.src-item { cursor: pointer; padding: 6px 8px; border-radius: 6px; background: #fff; margin-bottom: 6px; border-left: 3px solid #667eea; }
.src-item:hover { background: #f0f4ff; }
.src-name { font-size: 12px; color: #4a4a8a; }
.src-content { font-size: 12px; color: #666; }
.input-bar { display: flex; gap: 10px; margin-top: 12px; }
.input-bar .el-input { flex: 1; }
.src-full { white-space: pre-wrap; line-height: 1.7; max-height: 400px; overflow-y: auto; }
</style>
