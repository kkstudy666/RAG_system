import { defineStore } from 'pinia'
import { getConfig, saveConfig } from '../api/system'

// 系统配置：分块/Top-K/温度/模型选择，保存后实时生效
export const useConfigStore = defineStore('config', {
  state: () => ({
    config: {
      chunk_size: 800,
      chunk_overlap: 120,
      retrieval_top_k: 4,
      temperature: 0.1,
      embedding_model: 'BAAI/bge-small-zh-v1.5',
      llm_provider: 'ollama',
      ollama_model: 'llama3',
      ollama_url: 'http://localhost:11434',
      api_model: 'deepseek-chat',
      api_url: 'https://api.deepseek.com/v1',
      api_key: '',
    },
    loaded: false,
  }),
  actions: {
    async load() {
      try {
        this.config = { ...this.config, ...(await getConfig()) }
        this.loaded = true
      } catch (e) {
        /* 后端不可用时使用默认值 */
      }
    },
    async save() {
      this.config = await saveConfig(this.config)
      return this.config
    },
  },
})
