import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  { path: '/login', name: 'login', component: () => import('../views/Login.vue') },
  {
    path: '/kbs',
    name: 'kbs',
    component: () => import('../views/KnowledgeBases.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/kb/:id',
    name: 'kb-detail',
    component: () => import('../views/KnowledgeBaseDetail.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/config',
    name: 'config',
    component: () => import('../views/Config.vue'),
    meta: { requiresAuth: true },
  },
  { path: '/', redirect: '/kbs' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录跳转登录页
router.beforeEach((to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth && !auth.isLoggedIn) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.name === 'login' && auth.isLoggedIn) {
    return { name: 'kbs' }
  }
  return true
})

export default router
