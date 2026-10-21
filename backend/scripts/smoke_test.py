"""
RAG 知识库系统 —— 端到端冒烟测试
==================================
验证「登录 → 建库 → 分片上传 → 合并 → 解析入库 → 查询」完整链路。

用法（在 backend/ 目录下运行）：
    python scripts/smoke_test.py
"""
import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402

TEST_TEXT = (
    "Python 是一种解释型、面向对象的高级编程语言。\n"
    "Python 内置的数据类型包括：列表（list）、字典（dict）、元组（tuple）、集合（set）。\n"
    "函数使用 def 关键字定义，例如：def add(a, b): return a + b。\n"
)


def main():
    with TestClient(app) as c:
        # 1. 登录
        r = c.post("/api/auth/login", json={"username": "admin", "password": "admin123"})
        assert r.status_code == 200, f"登录失败: {r.text}"
        token = r.json()["access_token"]
        h = {"Authorization": f"Bearer {token}"}
        print("✓ 登录成功")

        # 2. 创建知识库
        r = c.post(
            "/api/kb",
            json={"name": "冒烟测试库", "is_public": False, "chunk_size": 500},
            headers=h,
        )
        assert r.status_code == 200, f"建库失败: {r.text}"
        kb_id = r.json()["id"]
        print(f"✓ 创建知识库 #{kb_id}")

        # 3. 分片上传（单分片）
        data = TEST_TEXT.encode("utf-8")
        fhash = hashlib.sha256(data).hexdigest()[:16]
        r = c.post(
            "/api/documents/chunk",
            files={"file": ("smoke.txt", data, "text/plain")},
            data={"file_hash": fhash, "chunk_index": 0},
            headers=h,
        )
        assert r.status_code == 200, f"分片上传失败: {r.text}"
        print("✓ 分片上传成功")

        # 4. 合并
        r = c.post(
            "/api/documents/merge",
            json={
                "filename": "smoke.txt",
                "kb_id": kb_id,
                "total_chunks": 1,
                "file_hash": fhash,
                "file_type": "txt",
            },
            headers=h,
        )
        assert r.status_code == 200, f"合并失败: {r.text}"
        print("✓ 分片合并成功")

        # 5. 解析入库（会加载嵌入模型，首次较慢）
        print("  正在解析入库（加载嵌入模型，首次可能较慢）...")
        r = c.post(
            "/api/documents/process",
            params={
                "kb_id": kb_id,
                "file_hash": fhash,
                "filename": "smoke.txt",
                "file_type": "txt",
            },
            headers=h,
        )
        assert r.status_code == 200, f"入库失败: {r.text}"
        doc = r.json()
        print(f"✓ 入库成功：分块 {doc['chunk_count']} 个，状态 {doc['status']}")

        # 6. 查询文档列表
        r = c.get("/api/documents", params={"kb_id": kb_id}, headers=h)
        assert r.status_code == 200
        assert len(r.json()) == 1
        print("✓ 文档列表查询成功")

        # 7. 知识库文档数
        r = c.get(f"/api/kb/{kb_id}", headers=h)
        assert r.json()["document_count"] == 1
        print("✓ 知识库文档数正确")

        print("\n全部冒烟测试通过 ✅")


if __name__ == "__main__":
    main()
