<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="brand">📚 RAG 知识库系统</div>
      <el-tabs v-model="mode" stretch>
        <el-tab-pane label="登录" name="login">
          <el-form @submit.prevent @keyup.enter="doLogin">
            <el-form-item>
              <el-input v-model="loginForm.username" placeholder="用户名" size="large">
                <template #prefix><el-icon><User /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="密码"
                size="large"
                show-password
              >
                <template #prefix><el-icon><Lock /></el-icon></template>
              </el-input>
            </el-form-item>
            <el-button type="primary" size="large" class="full" :loading="loading" @click="doLogin">
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
        <el-tab-pane label="注册" name="register">
          <el-form @submit.prevent @keyup.enter="doRegister">
            <el-form-item>
              <el-input v-model="regForm.username" placeholder="用户名（至少 2 位）" size="large" />
            </el-form-item>
            <el-form-item>
              <el-input
                v-model="regForm.password"
                type="password"
                placeholder="密码（至少 6 位）"
                size="large"
                show-password
              />
            </el-form-item>
            <el-button type="success" size="large" class="full" :loading="loading" @click="doRegister">
              注册并登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>
      <p class="tip">默认管理员账号：admin / admin123（登录后请尽快修改）</p>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, register, me } from '../api/auth'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const mode = ref('login')
const loading = ref(false)
const loginForm = reactive({ username: '', password: '' })
const regForm = reactive({ username: '', password: '' })

async function doLogin() {
  if (!loginForm.username || !loginForm.password) {
    return ElMessage.warning('请输入用户名和密码')
  }
  loading.value = true
  try {
    const res = await login(loginForm)
    auth.setAuth(res.access_token, res.username)
    try {
      auth.setUser(await me())
    } catch (e) {
      /* 用户信息获取失败不阻塞登录 */
    }
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/kbs')
  } catch (e) {
    /* 错误已由拦截器提示 */
  } finally {
    loading.value = false
  }
}

async function doRegister() {
  if (regForm.username.length < 2) return ElMessage.warning('用户名至少 2 位')
  if (regForm.password.length < 6) return ElMessage.warning('密码至少 6 位')
  loading.value = true
  try {
    const res = await register(regForm)
    auth.setAuth(res.access_token, res.username)
    try {
      auth.setUser(await me())
    } catch (e) {
      /* ignore */
    }
    ElMessage.success('注册成功')
    router.push('/kbs')
  } catch (e) {
    /* ignore */
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-wrap {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}
.login-card { width: 400px; }
.brand { text-align: center; font-size: 22px; font-weight: 700; margin-bottom: 20px; }
.full { width: 100%; }
.tip { text-align: center; color: #999; font-size: 12px; margin-top: 12px; }
</style>
