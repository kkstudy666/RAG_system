<template>
  <div v-loading="loading">
    <div class="header">
      <div class="left">
        <el-button text @click="$router.push('/kbs')">
          <el-icon><ArrowLeft /></el-icon>&nbsp;返回
        </el-button>
        <h2 class="inline">{{ kb.name }}</h2>
        <el-tag v-if="kb.is_public" type="success" size="small">公开</el-tag>
        <el-tag v-else type="info" size="small">私有</el-tag>
        <span class="meta">· {{ kb.document_count }} 个文档 · 嵌入 {{ shortModel(kb.embedding_model) }}</span>
      </div>
      <div class="ops">
        <el-button :disabled="isOwner !== true" @click="backup">备份向量库</el-button>
        <el-button :disabled="isOwner !== true" @click="rebuild">重建索引</el-button>
        <el-button v-if="isOwner === true" @click="togglePublic">
          {{ kb.is_public ? '设为私有' : '设为公开' }}
        </el-button>
      </div>
    </div>

    <el-tabs v-model="tab">
      <el-tab-pane label="对话" name="chat">
        <ChatPanel :kb-id="kb.id" />
      </el-tab-pane>
      <el-tab-pane label="文档管理" name="docs">
        <DocumentPanel v-if="isOwner === true" :kb-id="kb.id" @changed="reload" />
        <el-empty v-else description="私有知识库仅创建者可管理文档" />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { getKb, updateKb, rebuildKb, backupKb } from '../api/kb'
import { useAuthStore } from '../stores/auth'
import ChatPanel from '../components/ChatPanel.vue'
import DocumentPanel from '../components/DocumentPanel.vue'

const route = useRoute()
const auth = useAuthStore()
const kb = ref({})
const loading = ref(false)
const tab = ref('chat')

const isOwner = computed(() => auth.user && kb.value.owner_id === auth.user.id)

onMounted(load)

async function load() {
  loading.value = true
  try {
    kb.value = await getKb(route.params.id)
  } finally {
    loading.value = false
  }
}

async function reload() {
  await load()
}

async function togglePublic() {
  kb.value = await updateKb(kb.value.id, { is_public: !kb.value.is_public })
  ElMessage.success('已更新可见性')
}

async function rebuild() {
  const res = await rebuildKb(kb.value.id)
  ElMessage.success(`重建完成，共 ${res.chunk_count} 个文本块`)
}

async function backup() {
  const res = await backupKb(kb.value.id)
  ElMessage.success(`备份完成：${res.filename}`)
}

function shortModel(m) {
  return m ? m.split('/').pop() : ''
}
</script>

<style scoped>
.header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 16px; }
.left { display: flex; align-items: center; gap: 10px; }
.inline { display: inline; margin: 0; }
.meta { color: #999; font-size: 13px; }
.ops { display: flex; gap: 8px; }
</style>
