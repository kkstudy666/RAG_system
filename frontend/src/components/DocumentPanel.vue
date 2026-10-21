<template>
  <div>
    <div class="upload-bar">
      <input
        ref="fileInput"
        type="file"
        multiple
        accept=".pdf,.txt,.md,.docx"
        style="display: none"
        @change="onFilesChosen"
      />
      <el-button type="primary" :disabled="uploading" @click="fileInput.click()">
        <el-icon><Upload /></el-icon>&nbsp;上传文档
      </el-button>
      <el-button :disabled="uploading" @click="load">刷新</el-button>
      <span class="hint">支持 PDF / TXT / MD / DOCX，单文件 ≤ 200MB，大文件自动分片上传</span>
    </div>

    <el-progress
      v-if="uploading"
      :percentage="progress"
      :status="uploadStatus"
      class="progress"
    >
      <template #default>{{ uploadTip }}</template>
    </el-progress>

    <el-table :data="docs" v-loading="loading" border>
      <el-table-column prop="name" label="文件名" min-width="220" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="70" />
      <el-table-column label="状态" width="120">
        <template #default="{ row }">
          <el-tooltip :content="row.message" :disabled="!row.message" placement="top">
            <el-tag :type="statusType(row.status)" size="small">{{ statusText(row.status) }}</el-tag>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column prop="chunk_count" label="分块数" width="90" />
      <el-table-column label="大小" width="110">
        <template #default="{ row }">{{ row.size_kb.toFixed(1) }} KB</template>
      </el-table-column>
      <el-table-column label="操作" width="90">
        <template #default="{ row }">
          <el-button size="small" type="danger" text @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
      <template #empty>
        <el-empty description="暂无文档，请上传" />
      </template>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  uploadChunk,
  getUploadedChunks,
  mergeChunks,
  processDocument,
  listDocuments,
  deleteDocument,
} from '../api/document'

const props = defineProps({
  kbId: { type: [Number, String], required: true },
})
const emit = defineEmits(['changed'])

const fileInput = ref(null)
const docs = ref([])
const loading = ref(false)
const uploading = ref(false)
const progress = ref(0)
const uploadStatus = ref('')
const uploadTip = ref('')

const CHUNK_SIZE = 5 * 1024 * 1024 // 5MB 分片

onMounted(load)

async function load() {
  loading.value = true
  try {
    docs.value = await listDocuments(props.kbId)
  } finally {
    loading.value = false
  }
}

// 计算文件 SHA-256 前 16 位（与后端 get_file_hash 保持一致）
async function computeFileHash(file) {
  const buffer = await file.arrayBuffer()
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer)
  const hashArray = Array.from(new Uint8Array(hashBuffer))
  const hex = hashArray.map((b) => b.toString(16).padStart(2, '0')).join('')
  return hex.slice(0, 16)
}

async function onFilesChosen(e) {
  const files = Array.from(e.target.files || [])
  e.target.value = ''
  if (!files.length) return

  for (const file of files) {
    await uploadOne(file)
  }
  emit('changed')
}

async function uploadOne(file) {
  const ext = file.name.split('.').pop().toLowerCase()
  if (!['pdf', 'txt', 'md', 'docx'].includes(ext)) {
    return ElMessage.warning(`不支持的文件类型: ${file.name}`)
  }

  uploading.value = true
  uploadStatus.value = ''
  progress.value = 0
  uploadTip.value = '正在准备上传...'

  try {
    const hash = await computeFileHash(file)
    const totalChunks = Math.ceil(file.size / CHUNK_SIZE)

    // 断点续传：查询已上传分片
    const { uploaded } = await getUploadedChunks(hash)
    const uploadedSet = new Set(uploaded || [])

    for (let i = 0; i < totalChunks; i++) {
      if (uploadedSet.has(i)) continue
      const chunk = file.slice(i * CHUNK_SIZE, Math.min((i + 1) * CHUNK_SIZE, file.size))
      const fd = new FormData()
      fd.append('file', chunk, file.name)
      fd.append('file_hash', hash)
      fd.append('chunk_index', i)
      await uploadChunk(fd)
      progress.value = Math.round(((i + 1) / totalChunks) * 80)
      uploadTip.value = `正在上传分片 ${i + 1}/${totalChunks}`
    }

    uploadTip.value = '正在合并文件...'
    await mergeChunks({
      filename: file.name,
      kb_id: props.kbId,
      total_chunks: totalChunks,
      file_hash: hash,
      file_type: ext,
    })

    uploadTip.value = '正在解析入库（构建向量索引）...'
    progress.value = 90
    await processDocument({
      kb_id: props.kbId,
      file_hash: hash,
      filename: file.name,
      file_type: ext,
    })

    progress.value = 100
    uploadStatus.value = 'success'
    uploadTip.value = `${file.name} 上传完成`
    ElMessage.success(`「${file.name}」上传并入库成功`)
    await load()
  } catch (err) {
    uploadStatus.value = 'exception'
    uploadTip.value = '上传失败'
  } finally {
    uploading.value = false
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`确认删除文档「${row.name}」？将同步清理其向量数据。`, '删除确认', {
    type: 'warning',
  })
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  await load()
  emit('changed')
}

function statusType(status) {
  return { done: 'success', low_quality: 'warning', error: 'danger' }[status] || 'info'
}

function statusText(status) {
  return {
    pending: '待处理',
    processing: '处理中',
    done: '已完成',
    low_quality: '低质量',
    error: '失败',
  }[status] || status
}
</script>

<style scoped>
.upload-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 16px; }
.hint { color: #999; font-size: 13px; }
.progress { margin-bottom: 16px; }
</style>
