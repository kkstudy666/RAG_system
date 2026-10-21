import http from './http'

// 上传单个分片（FormData）
export const uploadChunk = (formData) => http.post('/documents/chunk', formData)

// 查询已上传分片序号（断点续传）
export const getUploadedChunks = (fileHash) =>
  http.get('/documents/chunks', { params: { file_hash: fileHash } })

// 合并分片为完整文件
export const mergeChunks = (data) => http.post('/documents/merge', data)

// 解析入库
export const processDocument = (params) =>
  http.post('/documents/process', null, { params })

// 文档列表
export const listDocuments = (kbId) =>
  http.get('/documents', { params: { kb_id: kbId } })

// 删除文档
export const deleteDocument = (id) => http.delete(`/documents/${id}`)
