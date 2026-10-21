"""
RAG 知识库系统 —— 后端全局配置
=================================
集中管理路径、模型选项、安全策略、JWT 配置等。
其余模块通过 `from config import ...` 引用，避免重复定义。
"""
import os

# ============================================================================
# 国内用户使用 HuggingFace 镜像站，解决网络无法访问问题
# 必须在加载任何 HuggingFace 模型之前设置，因此放在最顶部
# ============================================================================
os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

from pathlib import Path

# ============================================================================
# 路径配置（相对 backend/ 目录定位，保证任意工作目录下运行一致）
# ============================================================================
BACKEND_DIR = Path(__file__).resolve().parent.parent   # backend/
DATA_DIR = BACKEND_DIR / "data"                        # 运行期数据根目录
STORAGE_DIR = DATA_DIR / "storage"                     # 各知识库向量库目录
BACKUP_DIR = DATA_DIR / "backups"                      # 向量库备份目录
LOG_DIR = DATA_DIR / "logs"                            # 日志目录
TMP_DIR = DATA_DIR / "tmp"                             # 分片上传临时目录

for _d in (STORAGE_DIR, BACKUP_DIR, LOG_DIR, TMP_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ============================================================================
# 文件上传安全策略
# ============================================================================
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}  # 上传白名单
MAX_FILE_SIZE = 200 * 1024 * 1024                      # 单文件大小上限 200MB
CHUNK_SIZE_UPLOAD = 5 * 1024 * 1024                    # 前端分片大小 5MB

# ============================================================================
# 分块默认值（可被用户在配置面板覆盖）
# ============================================================================
CHUNK_SIZE_MAP = {"txt": 600, "md": 600, "pdf": 800, "docx": 800}  # 按类型适配
CHUNK_OVERLAP_RATIO = 0.15        # 重叠率 15%
DEFAULT_CHUNK_SIZE = 800
DEFAULT_TOP_K = 4                 # 重排后返回给 LLM 的块数
RETRIEVAL_TOP_K = 20              # 粗召回候选数（重排前的召回量）
DEFAULT_TEMPERATURE = 0.1
MAX_CONTEXT_CHARS = 6000          # 拼入 prompt 的上下文最大字符数

# ============================================================================
# 模型选项
# ============================================================================
EMBEDDING_MODELS = {
    "all-MiniLM-L6-v2 (英文优化, 384维, 轻量)": "sentence-transformers/all-MiniLM-L6-v2",
    "bge-small-zh-v1.5 (中文优化, 512维, 推荐中文)": "BAAI/bge-small-zh-v1.5",
    "paraphrase-multilingual-MiniLM-L12-v2 (多语言, 384维)": "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
    "all-mpnet-base-v2 (英文最佳, 768维, 较慢)": "sentence-transformers/all-mpnet-base-v2",
}
DEFAULT_EMBEDDING_MODEL = "BAAI/bge-small-zh-v1.5"

# Rerank 重排序模型（BGE-Reranker cross-encoder）
RERANK_MODEL = "BAAI/bge-reranker-base"

# ============================================================================
# JWT 鉴权
# ============================================================================
JWT_SECRET_KEY = os.getenv(
    "JWT_SECRET_KEY", "rag-system-dev-secret-change-me-please-set-in-production"
)
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 默认 24 小时

# ============================================================================
# 日志
# ============================================================================
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
