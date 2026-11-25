from __future__ import annotations

import redis
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.db_url,
    pool_pre_ping=True,
    pool_recycle=1800,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


_redis: redis.Redis | None = None


def get_redis() -> redis.Redis | None:
    """Redis 是可降级的：连不上时返回 None，会话与限流自动退化为无缓存模式。"""
    global _redis
    if _redis is None:
        try:
            # 本机 Redis 是老版本（不支持 RESP3 的 HELLO），必须显式 protocol=2
            client = redis.Redis.from_url(
                settings.redis_url, decode_responses=True, socket_timeout=1, protocol=2
            )
            client.ping()
            _redis = client
        except Exception:
            _redis = None
    return _redis


def redis_healthy() -> bool:
    return get_redis() is not None
