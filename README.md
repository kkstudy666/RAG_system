# 📚 RAG 知识库智能问答系统

基于 **LangChain + FAISS + Streamlit** 构建的检索增强生成（RAG）系统，支持上传 PDF/TXT/MD/DOCX 文档，进行向量化存储，并通过大语言模型实现智能问答。

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-red.svg)](https://streamlit.io)
[![LangChain](https://img.shields.io/badge/LangChain-0.1+-green.svg)](https://langchain.com)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 📄 **多格式文档上传** | 支持 PDF、TXT、Markdown、DOCX 格式 |
| 🧩 **智能文本分块** | 递归分块策略，保持语义完整性 |
| 🔢 **向量化存储** | 基于 FAISS 的高效向量相似度搜索 |
| 🤖 **多 LLM 支持** | Ollama 本地开源模型 + OpenAI 兼容 API |
| 🌍 **多语言嵌入** | 支持中英文优化嵌入模型 |
| 💬 **对话式交互** | 类 ChatGPT 的聊天界面 |
| 📖 **来源追溯** | 显示回答引用的原始文档片段 |
| 💾 **持久化存储** | 向量库自动保存，重启无需重建 |
| ⚙️ **灵活配置** | 可调节分块大小、检索数量、温度等参数 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                   Streamlit Web UI                       │
│  ┌──────────────┐  ┌──────────────────────────────────┐ │
│  │   侧边栏      │  │        主内容区                    │ │
│  │              │  │                                  │ │
│  │ 📄 文档上传   │  │  💬 聊天对话                      │ │
│  │ ⚙️ 模型配置   │  │  📖 引用来源                      │ │
│  │ 📋 文档列表   │  │  📊 状态指示                      │ │
│  └──────────────┘  └──────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ┌────────────┐  ┌────────────┐  ┌──────────────┐
   │ 文档加载器  │  │ 嵌入模型    │  │  LLM 大模型   │
   │            │  │            │  │              │
   │ PyPDFLoader│  │ Sentence-  │  │ Ollama 🦙    │
   │ TextLoader │  │ Transformers│  │ OpenAI API   │
   │ DocxLoader │  │ (本地运行)  │  │ Compatible   │
   └────────────┘  └────────────┘  └──────────────┘
          │               │               │
          ▼               ▼               ▼
   ┌─────────────────────────────────────────────┐
   │              FAISS 向量数据库                 │
   │         (磁盘持久化 + 相似度搜索)              │
   └─────────────────────────────────────────────┘
```

### 工作流程

1. **文档上传** → 用户通过 UI 上传文档
2. **文本提取** → LangChain 加载器解析文档内容
3. **智能分块** → `RecursiveCharacterTextSplitter` 将文本切分为语义块
4. **向量化** → `sentence-transformers` 将文本块转为向量
5. **存储索引** → FAISS 建立向量索引并持久化到磁盘
6. **用户提问** → 问题向量化后在 FAISS 中检索最相关文本块
7. **生成回答** → 检索结果 + 问题 → LLM 生成精准回答
8. **来源追溯** → 展示引用文档片段

---

## 🚀 快速开始

### 环境要求

- **Python** >= 3.10
- **系统内存** >= 8GB（推荐 16GB）
- **磁盘空间** >= 2GB（模型下载 + 向量库存储）

### 第一步：克隆项目

```bash
git clone <your-repo-url>
cd RAG_system
```

### 第二步：创建虚拟环境

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python3 -m venv venv
source venv/bin/activate
```

### 第三步：安装依赖

```bash
pip install -r requirements.txt
```

### 第四步：配置 LLM

#### 方案 A：Ollama 本地模型（推荐，完全开源）

1. 安装 Ollama：[https://ollama.com](https://ollama.com)

2. 下载并运行模型：

```bash
# 推荐模型
ollama pull llama3          # Meta Llama 3 (8B)
ollama pull qwen2           # 通义千问 Qwen 2 (7B) - 中文优化
ollama pull mistral         # Mistral (7B)
ollama pull deepseek-r1     # DeepSeek R1 - 深度推理
```

3. 验证 Ollama 是否运行：

```bash
ollama list    # 查看已安装的模型
curl http://localhost:11434/api/tags  # 验证服务
```

#### 方案 B：OpenAI 兼容 API

支持任何 OpenAI 兼容的 API 服务（DeepSeek, ZhipuAI, SiliconFlow 等）：

- 在应用侧边栏选择 "OpenAI 兼容 API"
- 填入 API 地址和 Key

### 第五步：启动应用

```bash
streamlit run app.py
```

浏览器会自动打开 `http://localhost:8501`

---

## 📖 使用指南

### 1. 上传文档

- 点击侧边栏 "上传文档" 区域
- 选择 PDF / TXT / MD / DOCX 文件（支持多选）
- 点击 "🔄 处理文档" 按钮
- 等待进度条完成（嵌入模型首次加载需下载 ~80MB）

### 2. 选择模型

| 嵌入模型 | 推荐场景 |
|----------|----------|
| `bge-small-zh-v1.5` | 中文文档为主（推荐） |
| `all-MiniLM-L6-v2` | 英文文档为主，速度最快 |
| `paraphrase-multilingual-MiniLM-L12-v2` | 多语言混合 |
| `all-mpnet-base-v2` | 英文最佳质量 |

### 3. 开始提问

- 在主区域底部的输入框中输入问题
- 系统会自动检索相关文档片段
- LLM 基于检索结果生成回答
- 展开 "📖 查看引用来源" 查看原始文档片段

### 4. 高级设置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| Chunk Size | 500 | 文本块大小，越大上下文越丰富 |
| Chunk Overlap | 50 | 块间重叠，避免信息在边界丢失 |
| Top-K | 4 | 每次检索返回的最相关文本块数 |
| Temperature | 0.1 | LLM 创造性，越低越精确 |

---

## 📁 项目结构

```
RAG_system/
├── app.py                  # 主应用程序
├── requirements.txt        # Python 依赖
├── README.md               # 项目文档
├── .gitignore              # Git 忽略规则
├── vector_store/           # FAISS 向量库（自动生成）
│   ├── index.faiss         # 向量索引
│   └── index.pkl           # 文档元数据
└── uploaded_files/         # 上传文件缓存（自动生成）
```

---

## 🔧 常见问题

<details>
<summary><b>Q: 首次运行下载模型很慢怎么办？</b></summary>

嵌入模型托管在 HuggingFace，国内用户可通过镜像加速：

```bash
export HF_ENDPOINT=https://hf-mirror.com
streamlit run app.py
```

或者提前手动下载模型：

```bash
# 使用 huggingface-cli 下载
pip install huggingface-hub
huggingface-cli download BAAI/bge-small-zh-v1.5 --local-dir ./models/bge-small-zh-v1.5
```
</details>

<details>
<summary><b>Q: Ollama 连接失败？</b></summary>

1. 确保 Ollama 正在运行：`ollama serve`
2. 检查端口是否被占用：`netstat -ano | findstr 11434`
3. 确认模型已下载：`ollama list`
</details>

<details>
<summary><b>Q: 内存不足怎么办？</b></summary>

1. 减小 Chunk Size（如 300）
2. 使用更小的嵌入模型（`all-MiniLM-L6-v2`）
3. 减少上传文档数量，分批处理
</details>

<details>
<summary><b>Q: 如何更新向量库？</b></summary>

- 上传新文档 → 点击处理 → 自动追加到现有知识库
- 点击 "🗑️ 清空知识库" → 重新上传 → 重建索引
</details>

<details>
<summary><b>Q: 支持 .doc (旧格式) 文件吗？</b></summary>

不支持 .doc 格式。请将 .doc 文件另存为 .docx 格式后再上传。
</details>

---

## 🛠️ 技术栈详解

| 组件 | 技术选型 | 说明 |
|------|----------|------|
| **UI 框架** | Streamlit | Python 原生的数据应用框架 |
| **文档加载** | LangChain Loaders | PyPDFLoader, TextLoader, Docx2txtLoader |
| **文本分块** | RecursiveCharacterTextSplitter | 递归语义分块，保留段落完整性 |
| **嵌入模型** | sentence-transformers | 开源嵌入模型，本地运行，无需 API |
| **向量数据库** | FAISS | Meta 开源的高效向量相似度搜索库 |
| **LLM 接入** | Ollama / OpenAI API | 支持本地和云端大模型 |
| **RAG 框架** | LangChain | RetrievalQA + PromptTemplate |

---

## 📝 后续计划

- [ ] 支持更多文件格式（HTML, CSV, EPUB）
- [ ] 添加多轮对话记忆
- [ ] 支持图片 OCR 识别
- [ ] 添加用户认证系统
- [ ] Docker 一键部署
- [ ] Web 搜索增强
- [ ] 问答历史导出

---

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 📄 许可证

本项目基于 MIT License 开源，详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

- [LangChain](https://github.com/langchain-ai/langchain) - LLM 应用开发框架
- [FAISS](https://github.com/facebookresearch/faiss) - 高效向量相似度搜索
- [Ollama](https://ollama.com) - 本地大模型运行工具
- [Streamlit](https://streamlit.io) - 快速构建数据应用
- [sentence-transformers](https://sbert.net) - 开源文本嵌入模型

---

**Made with ❤️ for the Open Source Community**
