<template>
  <div class="config-wrap">
    <h2>系统配置</h2>
    <el-alert
      title="配置保存后实时生效，无需重启；检索 Top-K 指重排后送入 LLM 的片段数。"
      type="info"
      :closable="false"
      class="tip"
    />

    <el-card class="card">
      <el-form label-width="140px" style="max-width: 640px">
        <el-form-item label="文本块大小">
          <el-slider v-model="config.chunk_size" :min="100" :max="2000" :step="50" show-input />
        </el-form-item>
        <el-form-item label="块重叠大小">
          <el-slider v-model="config.chunk_overlap" :min="0" :max="500" :step="10" show-input />
        </el-form-item>
        <el-form-item label="检索 Top-K">
          <el-slider v-model="config.retrieval_top_k" :min="1" :max="10" :step="1" show-input />
        </el-form-item>
        <el-form-item label="模型温度">
          <el-slider v-model="config.temperature" :min="0" :max="1" :step="0.05" show-input />
        </el-form-item>

        <el-divider>生成模型</el-divider>

        <el-form-item label="LLM 提供商">
          <el-radio-group v-model="config.llm_provider">
            <el-radio value="ollama">Ollama（本地）</el-radio>
            <el-radio value="openai_compatible">OpenAI 兼容 API</el-radio>
          </el-radio-group>
        </el-form-item>

        <template v-if="config.llm_provider === 'ollama'">
          <el-form-item label="模型名称">
            <el-input v-model="config.ollama_model" placeholder="如 llama3 / qwen2" />
          </el-form-item>
          <el-form-item label="服务地址">
            <el-input v-model="config.ollama_url" />
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="模型名称">
            <el-input v-model="config.api_model" placeholder="如 deepseek-chat" />
          </el-form-item>
          <el-form-item label="API 地址">
            <el-input v-model="config.api_url" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="config.api_key" type="password" show-password />
          </el-form-item>
        </template>

        <el-form-item label="嵌入模型">
          <el-select v-model="config.embedding_model" style="width: 100%">
            <el-option v-for="(v, k) in embeddingModels" :key="k" :label="k" :value="v" />
          </el-select>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存配置</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useConfigStore } from '../stores/config'

const configStore = useConfigStore()
const config = configStore.config
const saving = ref(false)

const embeddingModels = {
  'bge-small-zh-v1.5 (中文优化, 512维, 推荐中文)': 'BAAI/bge-small-zh-v1.5',
  'all-MiniLM-L6-v2 (英文优化, 384维, 轻量)': 'sentence-transformers/all-MiniLM-L6-v2',
  'paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维)':
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
  'all-mpnet-base-v2 (英文最佳, 768维, 较慢)': 'sentence-transformers/all-mpnet-base-v2',
}

onMounted(() => {
  if (!configStore.loaded) configStore.load()
})

async function save() {
  saving.value = true
  try {
    await configStore.save()
    ElMessage.success('配置已保存并实时生效')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.config-wrap { max-width: 800px; }
.tip { margin: 12px 0 20px; }
.card { padding: 8px 0; }
</style>
