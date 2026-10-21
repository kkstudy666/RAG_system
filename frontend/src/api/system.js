import http from './http'

export const getConfig = () => http.get('/config')
export const saveConfig = (data) => http.put('/config', data)
export const getMetrics = () => http.get('/metrics')
export const health = () => http.get('/health')
