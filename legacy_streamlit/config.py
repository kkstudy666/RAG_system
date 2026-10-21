"""
RAG 知识库智能问答系统 —— 全局配置
=====================================
集中管理路径常量、模型选项、提示词模板、页面样式等配置。
其余模块通过 `from config import ...` 引用，避免各文件重复定义。
"""

# ============================================================================
# 国内用户使用 HuggingFace 镜像站，解决网络无法访问问题
# 必须在加载任何 HuggingFace 模型之前设置，因此放在最顶部
# ============================================================================
import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"

from pathlib import Path

from langchain_core.prompts import PromptTemplate

# ============================================================================
# 路径配置
# ============================================================================
VECTOR_STORE_PATH = Path("./vector_store")
UPLOAD_DIR = Path("./uploaded_files")
DOC_INFO_FILE = VECTOR_STORE_PATH / "doc_info.json"  # 文档元信息持久化文件
EMBEDDING_MODEL_FILE = VECTOR_STORE_PATH / "embedding_model.json"  # 索引嵌入模型持久化文件
VECTOR_STORE_PATH.mkdir(parents=True, exist_ok=True)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 模型选项
# ============================================================================
# 支持的嵌入模型
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2 (英文优化, 384维, 轻量)": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-small-zh-v1.5 (中文优化, 512维, 推荐中文)": "BAAI/bge-small-zh-v1.5",
    "paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维)": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "all-mpnet-base-v2 (英文最佳, 768维, 较慢)": "sentence-transformers/all-mpnet-base-v2",
}

# ============================================================================
# RAG 提示词模板
# ============================================================================
RAG_PROMPT_TEMPLATE = """你是一个专业的知识库问答助手。请严格基于以下提供的上下文信息来回答问题。

## 规则
1. 只使用下面【上下文】中提供的具体信息来回答
2. 如果上下文中没有相关信息，请明确说"根据已有文档，无法找到相关信息"
3. 不要编造或猜测任何不在上下文中的信息
4. 回答时请引用具体的文档来源
5. 如果信息充足，请给出详细、结构化的回答
6. 使用与用户问题相同的语言回答

## 上下文信息
{context}

## 用户问题
{question}

## 详细回答
"""

RAG_PROMPT = PromptTemplate(
    template=RAG_PROMPT_TEMPLATE,
    input_variables=["context", "question"],
)

# ============================================================================
# 自定义 CSS 样式
# ============================================================================
CUSTOM_CSS = """
<style>
    /* 整体字体优化 */
    .stApp {
        font-family: 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif;
    }

    /* 主标题 */
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }

    /* 副标题 */
    .sub-header {
        font-size: 1rem;
        color: #888;
        margin-bottom: 1.5rem;
    }

    /* 侧边栏样式 */
    .sidebar-section {
        padding: 0.5rem 0;
        border-bottom: 1px solid #eee;
        margin-bottom: 0.8rem;
    }

    /* 文档卡片 */
    .doc-card {
        background: #f8f9fa;
        border-radius: 8px;
        padding: 0.6rem 0.8rem;
        margin: 0.3rem 0;
        font-size: 0.85rem;
        border-left: 3px solid #667eea;
    }

    /* 引用来源框 */
    .source-box {
        background: #f0f4ff;
        border-radius: 8px;
        padding: 0.8rem 1rem;
        margin: 0.5rem 0;
        border-left: 4px solid #667eea;
        font-size: 0.85rem;
    }

    .source-box .title {
        font-weight: 600;
        color: #4a4a8a;
        margin-bottom: 0.3rem;
    }

    .source-box .content {
        color: #555;
        max-height: 100px;
        overflow-y: auto;
        white-space: pre-wrap;
        font-size: 0.8rem;
    }

    .source-box .meta {
        color: #999;
        font-size: 0.75rem;
        margin-top: 0.3rem;
    }

    /* 状态指示器 */
    .status-ready {
        color: #28a745;
        font-weight: 600;
    }

    .status-empty {
        color: #dc3545;
        font-weight: 600;
    }

    /* 按钮样式 */
    .stButton > button {
        border-radius: 8px;
        font-weight: 500;
        transition: all 0.2s;
    }

    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.3);
    }

    /* 聊天气泡优化 */
    .stChatMessage {
        border-radius: 12px;
    }

    /* 文件上传区域 */
    .stFileUploader {
        border-radius: 12px;
    }

    /* 进度条 */
    .stProgress > div > div > div {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
</style>
"""
