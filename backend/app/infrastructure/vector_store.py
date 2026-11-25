"""向量库适配层：Milvus（standalone，localhost:19530）。

- 懒连接：第一次用到才建客户端，连不上返回 None，上层降级；
- 集合统一结构：id(INT64) + vector(FLOAT_VECTOR) + 若干标量字段（用于过滤与回显）；
- 度量用 COSINE：bge-m3 向量做语义相似度，分数天然落在 [-1,1]，阈值好定。
"""
from __future__ import annotations

from typing import Any

from app.core.config import settings


class MilvusStore:
    _client: Any = None
    _failed_at: float = 0.0
    RETRY_SECONDS = 60.0

    def _get_client(self):
        import time

        if self._client is not None:
            return self._client
        if self._failed_at and (time.time() - self._failed_at) < self.RETRY_SECONDS:
            return None
        try:
            from pymilvus import MilvusClient

            client = MilvusClient(uri=settings.milvus_uri, timeout=5)
            client.list_collections()  # 探活
            self._client = client
            self._failed_at = 0.0
        except Exception:
            import time as _t

            self._failed_at = _t.time()
            self._client = None
        return self._client

    @property
    def available(self) -> bool:
        return self._get_client() is not None

    def ensure(self, collection: str, dim: int | None = None) -> bool:
        client = self._get_client()
        if client is None:
            return False
        dim = dim or settings.embed_dim
        try:
            if not client.has_collection(collection):
                # enable_dynamic_field：pymilvus 3.x 默认只建 id+vector，额外字段会被丢弃
                client.create_collection(
                    collection_name=collection,
                    dimension=dim,
                    metric_type="COSINE",
                    auto_id=False,
                    id_type="int",
                    enable_dynamic_field=True,
                )
            return True
        except Exception:
            return False

    def upsert(self, collection: str, rows: list[dict]) -> int:
        """rows: [{"id": 1, "vector": [...], "name": "...", ...}]"""
        client = self._get_client()
        if client is None or not rows:
            return 0
        if not self.ensure(collection):
            return 0
        try:
            client.upsert(collection_name=collection, data=rows)
            # 不 flush 的话紧接着的 search 可能读不到刚写的数据
            try:
                client.flush(collection)
            except Exception:
                pass
            return len(rows)
        except Exception:
            return 0

    def search(self, collection: str, vector: list[float], top_k: int = 10,
               expr: str | None = None, output_fields: list[str] | None = None) -> list[dict]:
        client = self._get_client()
        if client is None or not vector:
            return []
        if not self.ensure(collection):
            return []
        try:
            hits = client.search(
                collection_name=collection,
                data=[vector],
                limit=max(1, min(100, top_k)),
                filter=expr or "",
                output_fields=output_fields or [],
            )
        except Exception:
            return []
        out: list[dict] = []
        for group in hits or []:
            for h in group:
                entity = h.get("entity", {}) if isinstance(h, dict) else {}
                out.append({"id": h.get("id"), "score": float(h.get("distance", 0.0)), **entity})
        return out

    def delete(self, collection: str, ids: list[int]) -> int:
        client = self._get_client()
        if client is None or not ids:
            return 0
        try:
            client.delete(collection_name=collection, ids=ids)
            return len(ids)
        except Exception:
            return 0

    def count(self, collection: str) -> int:
        """精确行数。

        不用 get_collection_stats：Milvus 的 row_count 含 upsert 产生的墓碑行，
        实测 upsert 6 行后报 18，不能当幂等判据。改用 count(*) 聚合。
        """
        client = self._get_client()
        if client is None:
            return 0
        try:
            if not client.has_collection(collection):
                return 0
        except Exception:
            return 0
        try:
            # 注意：count(*) 不能带 limit，否则报 1100 "count entities with pagination is not allowed"
            rows = client.query(collection_name=collection, filter="id >= 0",
                                output_fields=["count(*)"])
            if rows:
                return int(rows[0].get("count(*)", 0))
        except Exception:
            pass
        try:
            stats = client.get_collection_stats(collection_name=collection)
            return int(stats.get("row_count", 0))
        except Exception:
            return 0

    def drop(self, collection: str) -> bool:
        client = self._get_client()
        if client is None:
            return False
        try:
            client.drop_collection(collection_name=collection)
            return True
        except Exception:
            return False


store = MilvusStore()
