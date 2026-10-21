# RAG 知识库系统 —— 系统架构说明

## 1. 总体架构

```
┌────────────────────────────────────────────────────────────────────┐
│                        浏览器（Vue 3 SPA）                          │
│  ┌──────────┐ ┌──────────┐ ┌──────────────┐ ┌──────────────────┐  │
│  │ 登录/注册 │ │ 知识库管理 │ │ 文档管理(分片) │ │ 对话(流式+引用)  │  │
│  └──────────┘ └──────────┘ └──────────────┘ └──────────────────┘  │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ HTTP/SSE（JWT Bearer 鉴权）
                               ▼
┌────────────────────────────────────────────────────────────────────┐
│                       FastAPI 后端（backend/）                      │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ API 层：auth / knowledge_bases / documents / chat / system   │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ 中间件：CORS · JWT 鉴权 · 耗时统计 · 结构化日志                │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Service 层：doc_service / kb_service / chat_service          │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ Core 层：chunking / embeddings / rerank / query_rewrite /    │  │
│  │          llm / vector_store / ocr / prompts / security        │  │
│  └──────────────────────────────────────────────────────────────┘  │
└──────┬──────────────┬──────────────┬──────────────┬────────────────┘
       ▼              ▼              ▼              ▼
 ┌──────────┐  ┌────────────┐  ┌───────────┐  ┌────────────────────┐
 │  SQLite   │  │  FAISS     │  │  Ollama /  │  │ 嵌入模型 + BGE-     │
 │(用户/KB/  │  │ (按KB隔离)  │  │  OpenAI    │  │ Reranker(本地加载)  │
 │ 文档/埋点) │  │            │  │  兼容API   │  │                    │
 └──────────┘  └────────────┘  └───────────┘  └────────────────────┘
```

## 2. 目录结构

```
RAG_system/
├── backend/                     # FastAPI 后端
│   ├── app/
│   │   ├── main.py              # 入口：CORS + 耗时中间件 + 路由挂载
│   │   ├── config.py            # 全局配置（路径/模型/安全策略/JWT）
│   │   ├── database.py          # SQLAlchemy + SQLite
│   │   ├── models.py            # User / KnowledgeBase / Document / QALog
│   │   ├── schemas.py           # Pydantic 请求/响应模型
│   │   ├── api/                 # 路由：auth/kb/documents/chat/system
│   │   ├── core/                # 核心：chunking/rerank/query_rewrite/vector_store/...
│   │   └── services/            # 业务编排：doc/kb/chat_service
│   ├── scripts/                 # eval.py 评测 / migrate_legacy.py 迁移
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/                    # Vue 3 前端
│   ├── src/
│   │   ├── router/  stores/  api/  views/  components/
│   │   └── main.js / App.vue
│   ├── nginx.conf               # 生产反向代理（含 SSE 免缓冲）
│   └── Dockerfile
├── docs/                        # 架构 / 部署 / 测试报告
├── docker-compose.yml
├── .env.example
└── legacy_streamlit/            # 归档的旧版 Streamlit 实现
```

## 3. 检索增强流水线（核心）

```
用户提问 ──► Query Rewrite（LLM 多轮改写）
                │
                ▼
        Embedding 向量化 ──► FAISS 粗召回 Top-K(20)
                │
                ▼
        BGE-Reranker 二次精排 ──► 取 Top-N(4)
                │
                ▼
        组装上下文 + 注入防护 Prompt ──► LLM 流式生成（SSE）
                │
                ▼
        引用来源回传 + 问答埋点（QALog）
```

- **Query Rewrite**：将多轮模糊提问（含"它/这个"等指代）改写为独立检索语句。
- **Rerank**：`BAAI/bge-reranker-base` cross-encoder 对 20 个候选做精确相关性打分，取前 4，显著优于纯向量相似度排序。模型懒加载，加载失败自动降级。
- **流式输出**：SSE `text/event-stream`，逐 token 下发，前端 `marked` 实时渲染 Markdown。

## 4. 分块策略

- 采用 `RecursiveCharacterTextSplitter` + 中文优先分隔符（`\n\n`、`\n`、`。`、`！`、`？`、`；`…），保证语义完整性。
- **重叠率 15%**：`overlap = chunk_size × 0.15`，解决上下文在块边界断裂的问题。
- **按文档类型适配大小**：txt/md=600、pdf/docx=800（可在配置面板覆盖）。
- 每个块生成稳定唯一 id `{file_hash}_{idx}`，支持 FAISS 精确删除。

## 5. FAISS 选型说明

| 维度 | FAISS（选型） | Milvus | Chroma |
|------|--------------|--------|--------|
| 部署形态 | 进程内库，零服务依赖 | 独立服务（需 Docker/分布式） | 独立服务或嵌入式 |
| 资源占用 | 极低，纯 CPU | 高（需维护服务） | 中 |
| 适用规模 | 万~百万级向量 | 亿级、分布式 | 中小规模 |
| 本地轻量部署 | ✅ 最佳 | ❌ 过重 | ⚠️ 可 |

**结论**：本项目面向实习生演示/简历展示，定位「本地轻量、一键部署」，知识库规模在万级向量以内，**FAISS 进程内库零运维、随应用启停**，是最优选择；Milvus 适合需要独立向量服务的大规模生产，Chroma 提供了更友好的 API 但额外引入服务依赖。

**索引类型**：默认使用 FAISS 的 `IndexFlatIP`（精确内积检索）。在 512 维、万级向量的本地场景下，精确检索的延迟完全可接受（毫秒级），无需 IVF/HNSW 等近似索引带来的精度损失与调参成本；数据规模增长后可按需切换 `IndexIVFFlat`。

## 6. 安全设计

- **JWT 鉴权**：PyJWT 签发 `HS256` 令牌，bcrypt 密码哈希，默认过期 24h。
- **权限隔离**：知识库分公开/私有，私有库仅创建者可读、可管理（上传/删除/备份/重建）。
- **上传防护**：扩展名白名单（.pdf/.txt/.md/.docx）+ 单文件 200MB 上限。
- **提示词注入防护**：RAG Prompt 内嵌最高优先级安全规则，声明系统指令不可被用户输入覆盖、禁止泄露 prompt 与未公开文档。
- **数据安全**：向量库按 `data/storage/{kb_id}/` 隔离；删除文档时通过 FAISS 显式 ids 精确删除对应向量，保证「删文档同步清向量」。

## 7. 可观测性

- 接口耗时统计中间件 + `data/logs/app.log` 滚动日志。
- 问答埋点 `QALog`（原始/改写问题、来源、答案、耗时），`GET /api/metrics` 汇总。
- `scripts/eval.py` 评测脚本对比优化前后命中率与耗时。
