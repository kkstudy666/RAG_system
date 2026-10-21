import axios from 'axios'
import { ElMessage } from 'element-plus'
import router from '../router'
import { useAuthStore } from '../stores/auth'

// axios 实例：baseURL 指向 /api（开发环境经 vite 代理到后端）
const http = axios.create({
  baseURL: '/api',
  timeout: 120000,
})

// 请求拦截：注入 JWT
http.interceptors.request.use((config) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截：统一错误处理（401 跳登录、断网提示）
http.interceptors.response.use(
  (res) => res.data,
  (err) => {
    if (!err.response) {
      ElMessage.error('网络连接失败，请检查网络或后端服务是否启动')
      return Promise.reject(err)
    }
    const status = err.response.status
    const detail = err.response.data?.detail || '请求失败'
    if (status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push('/login')
      ElMessage.error('登录已过期，请重新登录')
    } else {
      ElMessage.error(typeof detail === 'string' ? detail : '请求失败')
    }
    return Promise.reject(err)
  },
)

export default http
