"""
RAG 知识库系统 —— 系统接口
============================
健康检查、用户配置读写、可观测性指标（问答埋点统计）。
"""
import json
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, QALog
from app.schemas import SystemConfig, MetricsOut
from app.core.deps import get_current_user
from app.config import DATA_DIR

router = APIRouter(tags=["system"])

# 用户配置存储目录（JSON 文件，MVP 简化；生产建议改数据库或环境变量）
CONFIG_DIR = DATA_DIR / "configs"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _config_path(user_id: int) -> Path:
    return CONFIG_DIR / f"{user_id}.json"


def _load_config(user_id: int) -> dict:
    p = _config_path(user_id)
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}
    return {}


def _save_config(user_id: int, config: dict) -> None:
    _config_path(user_id).write_text(
        json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8"
    )


@router.get("/health")
def health():
    """健康检查"""
    return {"status": "ok"}


@router.get("/config", response_model=SystemConfig)
def get_config(user: User = Depends(get_current_user)):
    """读取当前用户配置（缺失字段用默认值填充）"""
    return SystemConfig(**_load_config(user.id))


@router.put("/config", response_model=SystemConfig)
def put_config(config: SystemConfig, user: User = Depends(get_current_user)):
    """保存用户配置，实时生效（前端保存后携带新配置发起问答）"""
    _save_config(user.id, config.model_dump())
    return config


@router.get("/metrics", response_model=MetricsOut)
def get_metrics(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """问答埋点统计：总问答数、平均耗时"""
    total = db.query(func.count(QALog.id)).scalar() or 0
    avg = db.query(func.avg(QALog.latency_ms)).scalar() or 0.0
    return MetricsOut(total_qa=int(total), avg_latency_ms=round(float(avg), 1))
