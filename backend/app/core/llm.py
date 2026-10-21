"""
RAG 知识库系统 —— LLM 客户端
==============================
获取 LLM 实例（Ollama 本地模型 / OpenAI 兼容 API），
并提供统一的流式生成接口，屏蔽两类模型 `.stream()` 的返回差异。
"""
from typing import Any, Iterator

from langchain_community.llms import Ollama
from langchain_openai import ChatOpenAI


def get_llm(config: dict) -> Any:
    """
    根据配置获取 LLM 实例

    Args:
        config: 包含 llm_provider / model / url / api_key / temperature 的字典
    """
    provider = config.get("llm_provider", "ollama")
    temperature = float(config.get("temperature", 0.1))

    if provider == "ollama":
        return Ollama(
            model=config.get("ollama_model", "llama3"),
            base_url=config.get("ollama_url", "http://localhost:11434"),
            temperature=temperature,
            num_predict=2048,
        )
    elif provider == "openai_compatible":
        return ChatOpenAI(
            model=config.get("api_model", "deepseek-chat"),
            openai_api_key=config.get("api_key", "not-needed"),
            base_url=config.get("api_url", "https://api.deepseek.com/v1"),
            temperature=temperature,
            max_tokens=2048,
        )
    else:
        raise ValueError(f"不支持的 LLM 提供商: {provider}")


def stream_llm(llm: Any, prompt: str) -> Iterator[str]:
    """
    统一的流式生成接口，逐 token 产出文本

    - Ollama.stream 直接产出 str
    - ChatOpenAI.stream 产出 AIMessageChunk，需取 .content
    """
    if isinstance(llm, Ollama):
        for token in llm.stream(prompt):
            if token:
                yield token
    else:
        for chunk in llm.stream(prompt):
            content = getattr(chunk, "content", None)
            if content:
                yield content
