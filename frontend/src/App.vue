<template>
  <!-- 未登录时仅渲染登录页 -->
  <router-view v-if="!auth.isLoggedIn" />

  <!-- 登录后显示主布局：侧边栏 + 内容区 -->
  <el-container v-else class="layout">
    <el-aside width="220px" class="aside">
      <div class="logo">📚 RAG 知识库</div>
      <el-menu :default-active="$route.path" router class="menu">
        <el-menu-item index="/kbs">
          <el-icon><Folder /></el-icon>
          <span>知识库管理</span>
        </el-menu-item>
        <el-menu-item index="/config">
          <el-icon><Setting /></el-icon>
          <span>系统配置</span>
        </el-menu-item>
      </el-menu>
      <div class="user-box">
        <div class="user-name">👤 {{ auth.user?.username }}</div>
        <el-button size="small" text @click="logout">退出登录</el-button>
      </div>
    </el-aside>
    <el-main class="main">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'
import { me } from './api/auth'

const auth = useAuthStore()
const router = useRouter()

// 刷新页面后，用 localStorage 中的 token 补全完整用户信息（含 id）
onMounted(async () => {
  if (auth.isLoggedIn) {
    try {
      auth.setUser(await me())
    } catch (e) {
      /* token 失效会由拦截器跳转登录 */
    }
  }
})

function logout() {
  auth.logout()
  router.push('/login')
}
</script>

<style>
* { box-sizing: border-box; }
html, body, #app { height: 100%; margin: 0; }
.layout { height: 100%; }
.aside {
  background: #1f2937;
  color: #fff;
  display: flex;
  flex-direction: column;
}
.logo {
  padding: 20px 16px;
  font-size: 18px;
  font-weight: 700;
  color: #fff;
}
.menu {
  border-right: none;
  background: transparent;
  flex: 1;
}
.menu .el-menu-item {
  color: #cbd5e1;
}
.menu .el-menu-item.is-active {
  color: #fff;
  background: #374151;
}
.menu .el-menu-item:hover {
  background: #374151;
}
.user-box {
  padding: 16px;
  border-top: 1px solid #374151;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.user-name { color: #e5e7eb; font-size: 14px; }
.main { background: #f5f7fa; }
</style>
