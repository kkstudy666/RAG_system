"""
RAG 知识库系统 —— FastAPI 主入口
==================================
应用初始化（建表 + 默认管理员）、CORS、请求耗时统计中间件、路由挂载。
"""
import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import LOG_DIR, LOG_LEVEL
from app.database import Base, engine, SessionLocal
from app.models import User
from app.core.security import hash_password
from app.api import auth, knowledge_bases, documents, chat, system

# ============================================================================
# 日志配置：控制台 + 滚动文件（可观测性：错误日志采集）
# ============================================================================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / "app.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("rag")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动时建表并创建默认管理员用户"""
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        if not db.query(User).filter(User.username == "admin").first():
            db.add(User(username="admin", password_hash=hash_password("admin123")))
            db.commit()
            logger.warning("已创建默认管理员账号 admin / admin123，请尽快修改密码")
    finally:
        db.close()

    yield
    logger.info("RAG 知识库系统已停止")


app = FastAPI(title="RAG 知识库系统", version="2.0.0", lifespan=lifespan)

# ============================================================================
# CORS（开发环境放开；生产按需收紧 allow_origins）
# ============================================================================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================================
# 接口耗时统计中间件（可观测性）
# ============================================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = (time.time() - start) * 1000
    logger.info(
        "%s %s -> %s (%.1fms)",
        request.method,
        request.url.path,
        response.status_code,
        duration,
    )
    return response


# ============================================================================
# 路由挂载
# ============================================================================
app.include_router(system.router, prefix="/api")
app.include_router(auth.router, prefix="/api")
app.include_router(knowledge_bases.router, prefix="/api")
app.include_router(documents.router, prefix="/api")
app.include_router(chat.router, prefix="/api")


@app.get("/")
def root():
    return {"name": "RAG 知识库系统", "docs": "/docs", "health": "/api/health"}
