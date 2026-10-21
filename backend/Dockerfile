# RAG 知识库系统 —— 后端镜像
FROM python:3.11-slim

WORKDIR /app

# libgomp1：faiss-cpu / onnxruntime 运行时依赖
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖清单，利用 Docker 层缓存加速重复构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app ./app

# 国内 HuggingFace 镜像（模型下载加速）
ENV HF_ENDPOINT=https://hf-mirror.com

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
