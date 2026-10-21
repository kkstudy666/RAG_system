import { defineStore } from 'pinia'

// 认证状态：token 与用户信息持久化到 localStorage
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    setAuth(token, username) {
      this.token = token
      this.user = { username }
      localStorage.setItem('token', token)
      localStorage.setItem('user', JSON.stringify({ username }))
    },
    setUser(user) {
      this.user = user
      localStorage.setItem('user', JSON.stringify(user))
    },
    logout() {
      this.token = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('user')
    },
  },
})
