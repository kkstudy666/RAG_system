"""
RAG 知识库系统 —— 检索效果评测脚本
====================================
对比「优化前（无重排/无改写）」与「优化后（查询改写 + BGE-Rerank 重排）」的
Top-K 命中率与平均耗时，用于生成问答效果测试报告。

用法（在 backend/ 目录下运行）：
    python scripts/eval.py --kb-id 1 --testset tests.json --top-k 4

测试集 JSON 格式：
    [
      {"question": "Python 有哪些数据类型？", "answer": "……", "keywords": ["列表", "字典", "元组"]},
      ...
    ]
keywords 为命中判断关键词：召回片段包含任一关键词即视为命中。
"""
import argparse
import json
import sys
import time
from pathlib import Path

# 让脚本能 import app 包
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.embeddings import load_embedding_model  # noqa: E402
from app.core import vector_store as vs  # noqa: E402
from app.core.rerank import rerank_documents  # noqa: E402
from app.core.query_rewrite import rewrite_query  # noqa: E402
from app.config import RETRIEVAL_TOP_K  # noqa: E402


def _hit(keywords, docs):
    """判断召回片段是否命中任一关键词"""
    if not keywords:
        return None  # 无关键词无法判断，返回 None
    for kw in keywords:
        for d in docs:
            if kw in d.page_content:
                return True
    return False


def evaluate_once(
    store, embeddings, testset, top_k, use_rerank, use_rewrite, llm_config
):
    """执行一轮评测，返回逐条结果与统计"""
    results = []
    hit_count = 0
    judged = 0
    total_latency = 0.0

    for item in testset:
        question = item["question"]
        keywords = item.get("keywords", [])

        start = time.time()
        query = rewrite_query(question, [], llm_config) if use_rewrite else question

        if use_rerank:
            candidates = store.similarity_search(query, k=RETRIEVAL_TOP_K)
            docs = rerank_documents(query, candidates, top_k)
        else:
            docs = store.similarity_search(query, k=top_k)

        latency = (time.time() - start) * 1000
        total_latency += latency

        hit_flag = _hit(keywords, docs)
        if hit_flag is not None:
            judged += 1
            hit_count += 1 if hit_flag else 0

        results.append(
            {
                "question": question,
                "hit": hit_flag,
                "latency_ms": round(latency, 1),
            }
        )

    return {
        "results": results,
        "hit_rate": round(hit_count / judged, 4) if judged else None,
        "judged": judged,
        "avg_latency_ms": round(total_latency / len(results), 1) if results else 0,
    }


def main():
    parser = argparse.ArgumentParser(description="RAG 检索效果评测")
    parser.add_argument("--kb-id", type=int, required=True, help="知识库 id")
    parser.add_argument("--testset", type=str, required=True, help="测试集 JSON 路径")
    parser.add_argument("--top-k", type=int, default=4, help="精排后返回片段数")
    parser.add_argument(
        "--embedding-model",
        type=str,
        default="BAAI/bge-small-zh-v1.5",
        help="嵌入模型（需与知识库索引一致）",
    )
    parser.add_argument(
        "--llm-provider", type=str, default="ollama", help="查询改写所用 LLM 提供商"
    )
    parser.add_argument("--llm-model", type=str, default="llama3", help="LLM 模型名")
    args = parser.parse_args()

    testset_path = Path(args.testset)
    if not testset_path.exists():
        print(f"测试集文件不存在: {testset_path}")
        sys.exit(1)
    testset = json.loads(testset_path.read_text(encoding="utf-8"))

    embeddings = load_embedding_model(args.embedding_model)
    store = vs.load_vector_store(args.kb_id, embeddings)
    if store is None:
        print(f"知识库 {args.kb_id} 无向量索引，请先上传文档")
        sys.exit(1)

    llm_config = {
        "llm_provider": args.llm_provider,
        "ollama_model": args.llm_model,
        "api_model": args.llm_model,
        "temperature": 0.0,
    }

    print("=" * 60)
    print(f"知识库 #{args.kb_id} · 测试集 {len(testset)} 条 · Top-K={args.top_k}")
    print("=" * 60)

    # 优化前：无重排、无改写
    before = evaluate_once(store, embeddings, testset, args.top_k, False, False, llm_config)
    # 优化后：改写 + 重排
    after = evaluate_once(store, embeddings, testset, args.top_k, True, True, llm_config)

    print("\n【优化前】基线检索（无重排/无改写）")
    print(f"  命中率: {before['hit_rate']} ({before['judged']} 条可判定)")
    print(f"  平均耗时: {before['avg_latency_ms']} ms")

    print("\n【优化后】查询改写 + BGE-Rerank 重排")
    print(f"  命中率: {after['hit_rate']} ({after['judged']} 条可判定)")
    print(f"  平均耗时: {after['avg_latency_ms']} ms")

    if before["hit_rate"] is not None and after["hit_rate"] is not None:
        delta = after["hit_rate"] - before["hit_rate"]
        print(f"\n命中率提升: {delta:+.2%}")

    # 输出完整结果 JSON
    report = {"before": before, "after": after, "top_k": args.top_k}
    out_path = Path("eval_result.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n完整结果已保存至: {out_path.resolve()}")


if __name__ == "__main__":
    main()
