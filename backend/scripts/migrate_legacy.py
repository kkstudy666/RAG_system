"""
RAG 知识库系统 —— 旧数据迁移脚本（可选）
==========================================
将旧 Streamlit 版本的单一向量库（legacy_streamlit/vector_store）迁移到
admin 用户的「默认知识库」中。由于新旧系统使用相同嵌入模型（bge-small-zh-v1.5），
可直接复用 FAISS 索引，无需重新向量化。

用法（在 backend/ 目录下运行）：
    python scripts/migrate_legacy.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.database import Base, engine, SessionLocal  # noqa: E402
from app.models import User, KnowledgeBase  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.core.embeddings import load_embedding_model  # noqa: E402
from app.core import vector_store as vs  # noqa: E402

LEGACY_MODEL = "BAAI/bge-small-zh-v1.5"


def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    # 确保 admin 用户存在
    admin = db.query(User).filter(User.username == "admin").first()
    if not admin:
        admin = User(username="admin", password_hash=hash_password("admin123"))
        db.add(admin)
        db.commit()
        db.refresh(admin)
        print("已创建 admin 用户（密码 admin123）")

    # 创建默认知识库
    kb = (
        db.query(KnowledgeBase)
        .filter(KnowledgeBase.owner_id == admin.id, KnowledgeBase.name == "默认知识库")
        .first()
    )
    if not kb:
        kb = KnowledgeBase(
            name="默认知识库",
            description="从旧版 Streamlit 迁移",
            owner_id=admin.id,
            is_public=False,
            embedding_model=LEGACY_MODEL,
        )
        db.add(kb)
        db.commit()
        db.refresh(kb)

    # 定位旧向量库
    legacy_path = (
        Path(__file__).resolve().parent.parent.parent / "legacy_streamlit" / "vector_store"
    )
    if not (legacy_path / "index.faiss").exists():
        print(f"未找到旧向量库: {legacy_path}")
        db.close()
        return

    # 加载并迁移（同嵌入模型，直接复用索引；复用 chdir 方案规避中文路径）
    embeddings = load_embedding_model(LEGACY_MODEL)
    store = vs._load_local(legacy_path, embeddings)
    vs._save_local(store, vs.kb_storage_dir(kb.id))

    print(f"迁移完成：知识库 #{kb.id}「{kb.name}」，向量数 {store.index.ntotal}")
    db.close()


if __name__ == "__main__":
    main()
