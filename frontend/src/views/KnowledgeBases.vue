<template>
  <div>
    <div class="header">
      <h2>知识库管理</h2>
      <el-button type="primary" @click="openCreate">
        <el-icon><Plus /></el-icon>&nbsp;新建知识库
      </el-button>
    </div>

    <el-row :gutter="16">
      <el-col v-for="kb in kbs" :key="kb.id" :span="8">
        <el-card class="kb-card" shadow="hover" @click="go(kb.id)">
          <div class="kb-title">
            {{ kb.name }}
            <el-tag v-if="kb.is_public" size="small" type="success">公开</el-tag>
            <el-tag v-else size="small" type="info">私有</el-tag>
          </div>
          <div class="kb-desc">{{ kb.description || '暂无描述' }}</div>
          <div class="kb-meta">
            {{ kb.document_count }} 个文档 · 嵌入 {{ shortModel(kb.embedding_model) }}
          </div>
          <div class="kb-actions" @click.stop>
            <el-button size="small" @click="togglePublic(kb)">
              {{ kb.is_public ? '设为私有' : '设为公开' }}
            </el-button>
            <el-button size="small" type="danger" @click="remove(kb)">删除</el-button>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-empty v-if="!loading && !kbs.length" description="暂无知识库，点击右上角新建" />

    <!-- 新建知识库对话框 -->
    <el-dialog v-model="dialogVisible" title="新建知识库" width="520px">
      <el-form label-width="90px">
        <el-form-item label="名称" required>
          <el-input v-model="form.name" placeholder="知识库名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input v-model="form.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="可见性">
          <el-switch v-model="form.is_public" active-text="公开" inactive-text="私有" />
        </el-form-item>
        <el-form-item label="嵌入模型">
          <el-select v-model="form.embedding_model" style="width: 100%">
            <el-option v-for="(v, k) in embeddingModels" :key="k" :label="k" :value="v" />
          </el-select>
        </el-form-item>
        <el-form-item label="分块大小">
          <el-input-number v-model="form.chunk_size" :min="100" :max="4000" :step="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="create">创建</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { reactive, ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKbs, createKb, updateKb, deleteKb } from '../api/kb'

const router = useRouter()
const kbs = ref([])
const loading = ref(false)
const dialogVisible = ref(false)
const creating = ref(false)

// 与后端 config.EMBEDDING_MODELS 保持一致
const embeddingModels = {
  'bge-small-zh-v1.5 (中文优化, 512维, 推荐中文)': 'BAAI/bge-small-zh-v1.5',
  'all-MiniLM-L6-v2 (英文优化, 384维, 轻量)': 'sentence-transformers/all-MiniLM-L6-v2',
  'paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维)':
    'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2',
  'all-mpnet-base-v2 (英文最佳, 768维, 较慢)': 'sentence-transformers/all-mpnet-base-v2',
}

const form = reactive({
  name: '',
  description: '',
  is_public: false,
  embedding_model: 'BAAI/bge-small-zh-v1.5',
  chunk_size: 800,
})

onMounted(load)

async function load() {
  loading.value = true
  try {
    kbs.value = await listKbs()
  } finally {
    loading.value = false
  }
}

function go(id) {
  router.push(`/kb/${id}`)
}

function openCreate() {
  form.name = ''
  form.description = ''
  form.is_public = false
  form.embedding_model = 'BAAI/bge-small-zh-v1.5'
  form.chunk_size = 800
  dialogVisible.value = true
}

async function create() {
  if (!form.name) return ElMessage.warning('请输入知识库名称')
  creating.value = true
  try {
    await createKb(form)
    ElMessage.success('创建成功')
    dialogVisible.value = false
    load()
  } finally {
    creating.value = false
  }
}

async function togglePublic(kb) {
  try {
    await updateKb(kb.id, { is_public: !kb.is_public })
    kb.is_public = !kb.is_public
    ElMessage.success('已更新可见性')
  } catch (e) {
    /* ignore */
  }
}

async function remove(kb) {
  await ElMessageBox.confirm(`确认删除知识库「${kb.name}」？将同时删除其全部文档与向量数据。`, '删除确认', {
    type: 'warning',
  })
  await deleteKb(kb.id)
  ElMessage.success('已删除')
  load()
}

function shortModel(m) {
  return m ? m.split('/').pop() : ''
}
</script>

<style scoped>
.header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.kb-card { cursor: pointer; margin-bottom: 16px; }
.kb-title { font-size: 16px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
.kb-desc { color: #666; font-size: 13px; margin: 8px 0; min-height: 20px; }
.kb-meta { color: #999; font-size: 12px; margin-bottom: 12px; }
.kb-actions { border-top: 1px solid #eee; padding-top: 10px; }
</style>
