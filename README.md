# 📚 RAG 知识库智能问答系统

基于 **FastAPI + Vue 3 + LangChain + FAISS + Ollama** 的检索增强生成（RAG）系统，支持多用户、知识库权限隔离、多格式文档解析、流式问答与检索效果优化（语义分块 + BGE-Rerank 重排 + 查询改写）。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![Vue](https://img.shields.io/badge/Vue-3.x-42b883.svg)](https://vuejs.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-green.svg)](https://langchain.com)

---

## ✨ 功能特性

| 模块 | 能力 |
|------|------|
| 📄 文档管理 | 多格式上传（PDF/TXT/MD/DOCX）、**分片上传 + 断点续传**、批量导入、解析状态反馈、删除同步清向量 |
| 💬 智能对话 | **Markdown 流式渲染**、引用来源一键跳转原文、多轮上下文记忆、对话历史本地缓存 |
| 🎯 检索优化 | 语义+重叠分块（15%）、**BGE-Rerank 重排序**、**查询改写（Query Rewrite）** |
| 🔐 安全权限 | **JWT 多用户登录**、知识库公开/私有隔离、上传白名单+大小限制、**提示词注入防护** |
| ⚙️ 可视化配置 | 分块大小/Top-K/温度/嵌入模型/生成模型，保存后实时生效 |
| 🛠️ 工程化 | 向量库增量/重建/**备份恢复**、重启自动加载、OCR 质量校验、耗时统计/问答埋点/日志、**Docker 一键部署** |

## 🏗️ 技术栈

- **后端**：Python 3.10+ · FastAPI · SQLAlchemy + SQLite · PyJWT + bcrypt
- **检索**：LangChain 1.x · FAISS · sentence-transformers · BGE-Reranker
- **文档**：PyPDF · python-docx · RapidOCR（扫描版 PDF）
- **模型**：Ollama 本地模型 / OpenAI 兼容 API；嵌入 `bge-small-zh-v1.5`（中文）
- **前端**：Vue 3 · Vite · Pinia · Element Plus · marked

## 🚀 快速开始

### Docker 一键部署（推荐）

```bash
cd RAG_system
cp .env.example .env          # 可选，修改 JWT 密钥
docker compose up -d --build
```

- 前端：http://localhost
- 后端文档：http://localhost:8000/docs

### 本地开发

**后端**：

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**前端**：

```bash
cd frontend
npm install
npm run dev       # http://localhost:5173（已代理 /api 到 :8000）
```

**默认账号**：`admin / admin123`（首次启动自动创建，请尽快修改）。

> 详细部署说明见 [docs/deploy.md](docs/deploy.md)。

## 🧭 使用流程

1. 登录 → 新建知识库（选择嵌入模型、设置公开/私有）
2. 进入知识库 → 上传文档（大文件自动分片）→ 等待解析入库
3. 切换「对话」标签 → 提问，查看流式回答与引用来源
4. 「系统配置」中调整分块/Top-K/温度/生成模型，实时生效

## 📁 目录结构

```
RAG_system/
├── backend/            # FastAPI 后端（app/api · app/core · app/services）
├── frontend/           # Vue 3 前端（views · components · stores · api）
├── docs/               # 架构说明 / 部署文档 / 测试报告
├── docker-compose.yml  # 一键部署编排
└── .env.example
```

## 📖 文档

- [系统架构说明](docs/architecture.md) —— 架构图、检索流水线、FAISS 选型依据、安全设计
- [部署文档](docs/deploy.md) —— Docker 部署、本地运行、备份恢复、常见问题
- [问答效果测试报告](docs/eval_report.md) —— 评测方法、指标口径、预期效果

## 🧪 评测

```bash
cd backend
# 检索效果评测（对比优化前后命中率）
python scripts/eval.py --kb-id 1 --testset tests.json --top-k 4
```

## 📄 许可证

MIT License
