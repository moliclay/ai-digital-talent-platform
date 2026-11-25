"""集中配置：只从环境变量读取，缺省值适用于本机 MVP 环境。"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[2]  # backend/


def _load_dotenv(path: Path) -> None:
    """极简 .env 加载：KEY=VALUE，忽略注释与空行；已存在的环境变量优先。"""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _env(key: str, default: str) -> str:
    return os.getenv(key, default)


@dataclass(frozen=True)
class Settings:
    app_name: str = "AI 数字化人才平台"
    env: str = field(default_factory=lambda: _env("APP_ENV", "dev"))

    db_url: str = field(
        default_factory=lambda: _env(
            "DATABASE_URL",
            "mysql+pymysql://root:123456@127.0.0.1:3306/ai_talent?charset=utf8mb4",
        )
    )
    redis_url: str = field(default_factory=lambda: _env("REDIS_URL", "redis://127.0.0.1:6379/0"))

    jwt_secret: str = field(
        default_factory=lambda: _env("JWT_SECRET", "mvp1-dev-secret-change-me-in-prod")
    )
    jwt_alg: str = "HS256"
    jwt_ttl_minutes: int = field(default_factory=lambda: int(_env("JWT_TTL_MINUTES", "480")))

    storage_backend: str = field(default_factory=lambda: _env("STORAGE_BACKEND", "local"))
    storage_dir: Path = field(default_factory=lambda: Path(_env("STORAGE_DIR", str(BASE_DIR / "storage"))))

    max_upload_mb: int = field(default_factory=lambda: int(_env("MAX_UPLOAD_MB", "10")))
    cors_origins: tuple[str, ...] = ("http://127.0.0.1:5173", "http://localhost:5173")
    rate_limit_per_minute: int = field(default_factory=lambda: int(_env("RATE_LIMIT_PER_MINUTE", "600")))

    # AI 网关（OpenAI 兼容）。留空则所有 AI 能力自动回退到规则实现。
    ai_enabled: bool = field(default_factory=lambda: _env("AI_ENABLED", "1") == "1")
    ai_base_url: str = field(default_factory=lambda: _env("AI_BASE_URL", "http://127.0.0.1:3065/v1"))
    ai_api_key: str = field(default_factory=lambda: _env("AI_API_KEY", ""))
    ai_model: str = field(default_factory=lambda: _env("AI_MODEL", "deepseek-v4.1-flash"))
    # 主模型超时/报错时的备用模型（网关同源），留空则不做降级
    # 注意：Doubao-Seed-2.1-Pro 已被网关关闭（404），改用实测可用的 qwen3.8-max
    ai_fallback_model: str = field(default_factory=lambda: _env("AI_FALLBACK_MODEL", "qwen3.8-max"))
    # 多模态模型（扫描件 OCR）：网关里支持 image 输入的模型
    # 注意：Doubao-Seed-2.1-Turbo 已被网关关闭，改用 glm-5v-turbo（网关内唯一的视觉模型）
    ai_vision_model: str = field(default_factory=lambda: _env("AI_VISION_MODEL", "glm-5v-turbo"))
    # 多模态比纯文本慢得多（实测单页 60~90s），单独给超时
    ai_vision_timeout: int = field(default_factory=lambda: int(_env("AI_VISION_TIMEOUT", "180")))
    # 总预算：主模型失败后还要留时间给备用模型，所以是两者之和的上限
    ai_timeout: int = field(default_factory=lambda: int(_env("AI_TIMEOUT", "120")))
    # 主模型单次超时。实测 1900 字简历正文需 15s 左右，给到 45s 覆盖波动
    ai_timeout_primary: int = field(default_factory=lambda: int(_env("AI_TIMEOUT_PRIMARY", "45")))
    # 备用模型单次超时。实测同一正文备用需 47s，给到 60s
    ai_timeout_fallback: int = field(default_factory=lambda: int(_env("AI_TIMEOUT_FALLBACK", "60")))

    # 嵌入（本地 Ollama）
    embed_base_url: str = field(default_factory=lambda: _env("EMBED_BASE_URL", "http://127.0.0.1:11434"))
    embed_model: str = field(default_factory=lambda: _env("EMBED_MODEL", "bge-m3"))
    embed_dim: int = field(default_factory=lambda: int(_env("EMBED_DIM", "1024")))
    embed_timeout: int = field(default_factory=lambda: int(_env("EMBED_TIMEOUT", "30")))

    # 向量库（Milvus）
    milvus_uri: str = field(default_factory=lambda: _env("MILVUS_URI", "http://127.0.0.1:19530"))
    milvus_resume_collection: str = field(default_factory=lambda: _env("MILVUS_RESUME_COLLECTION", "resume_vectors"))
    milvus_job_collection: str = field(default_factory=lambda: _env("MILVUS_JOB_COLLECTION", "job_vectors"))
    ai_reasoning_effort: str = field(default_factory=lambda: _env("AI_REASONING_EFFORT", "medium"))


_load_dotenv(BASE_DIR / ".env")

settings = Settings()
