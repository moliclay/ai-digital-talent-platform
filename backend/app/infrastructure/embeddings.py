"""嵌入层：本地 Ollama（bge-m3，1024 维）。

设计原则与其他适配器一致：
- **可缺席**：Ollama 没起时 `available=False`，调用方回退到"无向量"模式，不影响主流程；
- **批量优先**：Ollama 的 /api/embed 支持一次传多条，避免逐条往返；
- **不重试风暴**：单次失败即返回 None，由上层决定降级。
"""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from app.core.config import settings


class OllamaEmbedder:
    _last_check: float = 0.0
    _ok: bool = False
    CHECK_TTL = 60.0

    @property
    def available(self) -> bool:
        now = time.time()
        if now - self._last_check < self.CHECK_TTL:
            return self._ok
        self._last_check = now
        try:
            req = urllib.request.Request(f"{settings.embed_base_url.rstrip('/')}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
            names = [m.get("name", "") for m in data.get("models", [])]
            self._ok = any(settings.embed_model.split(":")[0] in n for n in names)
        except Exception:
            self._ok = False
        return self._ok

    def embed(self, texts: list[str]) -> list[list[float]] | None:
        texts = [t for t in (texts or []) if t and t.strip()]
        if not texts or not self.available:
            return None
        payload = {"model": settings.embed_model, "input": texts}
        req = urllib.request.Request(
            f"{settings.embed_base_url.rstrip('/')}/api/embed",
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
        )
        req.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(req, timeout=settings.embed_timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
            vectors = body.get("embeddings")
            if isinstance(vectors, list) and len(vectors) == len(texts):
                return [[float(x) for x in v] for v in vectors]
        except Exception:
            return None
        return None

    def embed_one(self, text: str) -> list[float] | None:
        out = self.embed([text])
        return out[0] if out else None


embedder = OllamaEmbedder()
