import http from './http'

export const listKbs = () => http.get('/kb')
export const createKb = (data) => http.post('/kb', data)
export const getKb = (id) => http.get(`/kb/${id}`)
export const updateKb = (id, data) => http.patch(`/kb/${id}`, data)
export const deleteKb = (id) => http.delete(`/kb/${id}`)
export const rebuildKb = (id) => http.post(`/kb/${id}/rebuild`)
export const backupKb = (id) => http.post(`/kb/${id}/backup`)
export const listBackups = (id) => http.get(`/kb/${id}/backups`)
export const restoreKb = (id, filename) =>
  http.post(`/kb/${id}/restore`, null, { params: { filename } })
