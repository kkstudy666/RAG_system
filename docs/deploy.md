# RAG 知识库系统 —— 部署文档

## 一、Docker 一键部署（推荐）

### 前置条件

- 已安装 [Docker](https://www.docker.com/) 与 Docker Compose 插件
- 若使用本地 Ollama 模型：宿主机已安装并运行 Ollama（`ollama serve`）

### 步骤

```bash
# 1. 进入项目根目录
cd RAG_system

# 2.（可选）配置环境变量：复制示例并修改 JWT 密钥
cp .env.example .env   # Windows: copy .env.example .env

# 3. 一键构建并启动
docker compose up -d --build
```

启动后访问：

- **前端**：http://localhost
- **后端接口文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/api/health

### 说明

- `backend/data/` 挂载为数据卷：SQLite 数据库、向量库、日志、备份持久化，容器重建不丢失。
- `hf-cache` 卷缓存 HuggingFace 模型（嵌入/重排模型），避免每次重建重新下载。
- 首次启动会触发嵌入模型下载（约 100MB~1GB，走 `hf-mirror.com` 镜像）。
- 停止：`docker compose down`；带数据卷清理：`docker compose down -v`（慎用）。

> **Ollama 连接提示**：容器内后端默认访问 `http://localhost:11434`，但该地址在容器内指向容器自身。
> 若 Ollama 运行在宿主机，需在配置面板把「Ollama 服务地址」改为
> `http://host.docker.internal:11434`（macOS/Windows）或宿主机局域网 IP。

## 二、本地开发运行（不依赖 Docker）

### 后端

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:5173（开发服务器已配置 `/api` 代理到 `:8000`）。

### 依赖模型准备

- **嵌入模型**：`BAAI/bge-small-zh-v1.5`（默认，中文优化）首次运行自动从镜像下载。
- **Rerank 模型**：`BAAI/bge-reranker-base`（约 1.1GB）首次调用重排时懒加载下载；无网环境下自动降级为无重排，不影响可用。
- **生成模型**：Ollama（`ollama pull llama3` / `qwen2`）或任意 OpenAI 兼容 API（DeepSeek / 智谱 / SiliconFlow 等）。

## 三、默认账号

| 用户名 | 密码 | 说明 |
|--------|------|------|
| admin | admin123 | 首次启动自动创建，登录后请在配置中修改 |

> 生产环境务必修改默认密码，并通过 `.env` 设置随机 `JWT_SECRET_KEY`。

## 四、数据备份与恢复

- 在知识库详情页点击「备份向量库」，生成 `backend/data/backups/{kb_id}_{时间}.zip`。
- 手动备份：整体复制 `backend/data/` 目录即可（含 SQLite + 向量 + 备份）。
- 恢复：通过 API `POST /api/kb/{kb_id}/restore?filename=...`，或将 `data/` 目录整体还原后重启。

## 五、常见问题

| 问题 | 处理 |
|------|------|
| 首次启动卡在模型下载 | 确认网络可访问 `hf-mirror.com`，或预先 `pip install sentence-transformers` 后手动下载模型 |
| 问答提示「生成回答失败」 | 检查 Ollama 是否运行（`ollama list`），或在配置面板改用 OpenAI 兼容 API |
| 扫描版 PDF 识别质量差 | 文档状态会标注「低质量」，建议提供更清晰的原始文件 |
| 前端 401 频繁跳登录 | 检查 `.env` 中 `JWT_SECRET_KEY` 是否被改动导致旧 token 失效 |
