"""
RAG 知识库智能问答系统 —— 持久化存储
=====================================
负责文档元信息与索引嵌入模型名的 JSON 读写，
使应用重启后能够恢复已加载文档列表并校验嵌入维度。
"""
import json
from typing import List, Dict, Any, Optional

from config import DOC_INFO_FILE, EMBEDDING_MODEL_FILE


def save_doc_info(doc_info_list: List[Dict[str, Any]]):
    """将文档信息列表持久化为 JSON 文件，重启后可恢复显示"""
    DOC_INFO_FILE.write_text(
        json.dumps(doc_info_list, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def load_doc_info() -> List[Dict[str, Any]]:
    """从磁盘加载之前持久化的文档信息列表"""
    if not DOC_INFO_FILE.exists():
        return []
    try:
        return json.loads(DOC_INFO_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []


def save_embedding_model(model_name: str):
    """持久化当前向量索引所使用的嵌入模型名，避免重启后维度不匹配"""
    EMBEDDING_MODEL_FILE.write_text(
        json.dumps({"model_name": model_name}, ensure_ascii=False),
        encoding="utf-8",
    )


def load_saved_embedding_model() -> Optional[str]:
    """读取上次构建索引时保存的嵌入模型名，不存在则返回 None"""
    if not EMBEDDING_MODEL_FILE.exists():
        return None
    try:
        data = json.loads(EMBEDDING_MODEL_FILE.read_text(encoding="utf-8"))
        return data.get("model_name")
    except Exception:
        return None
