import { defineStore } from 'pinia'

// 对话历史：按知识库 id 缓存到 localStorage，实现多轮上下文记忆
export const useChatStore = defineStore('chat', {
  state: () => ({
    histories: JSON.parse(localStorage.getItem('chat_histories') || '{}'),
  }),
  actions: {
    getHistory(kbId) {
      return this.histories[kbId] || []
    },
    addMessage(kbId, msg) {
      const list = this.histories[kbId] || []
      list.push(msg)
      this.histories[kbId] = list
      this._persist()
    },
    clear(kbId) {
      delete this.histories[kbId]
      this._persist()
    },
    _persist() {
      localStorage.setItem('chat_histories', JSON.stringify(this.histories))
    },
  },
})
