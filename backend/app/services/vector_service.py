"""向量能力：简历/岗位向量化、语义检索、查重、岗位语义召回。

降级策略：
- Ollama 或 Milvus 任一不可用 → 接口返回 `available: false` 与空结果，主流程不受影响；
- 语义检索的结果**必须再过一遍数据库权限**（Milvus 里没有 data_scope），越权结果直接剔除。
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, apply_scope, max_scope
from app.core.response import ApiError
from app.infrastructure.embeddings import embedder
from app.models.orm import JobProfile, ParsedResume, ResumeFile
from app.infrastructure.vector_store import store
from app.services.resume_service import briefs_by_ids


def _skills_text(skills: Any) -> str:
    if isinstance(skills, list):
        return "、".join(str(s) for s in skills)
    return str(skills or "")


def resume_text(parsed: ParsedResume) -> str:
    """拼简历向量文本：结构化字段前置（权重更高），正文截断 2000 字。"""
    parts = [
        f"姓名 {parsed.name or ''}",
        f"学历 {parsed.education or '未识别'}",
        f"专业 {parsed.major or ''}",
        f"工作年限 {parsed.years_experience or 0} 年",
        f"技能 {_skills_text(parsed.skills)}",
    ]
    if parsed.strengths:
        parts.append(f"优势 {parsed.strengths}")
    if parsed.resume_content:
        parts.append(parsed.resume_content[:2000])
    return "\n".join(p for p in parts if p.strip())


def job_text(job: JobProfile) -> str:
    conds = []
    for c in (job.conditions or []):
        if isinstance(c, dict):
            conds.append(f"{c.get('key')}{c.get('op')}{c.get('value')}")
    parts = [f"岗位 {job.name}", job.prompt or "", "条件 " + "；".join(conds)]
    baseline = job.ability_requirements or {}
    if baseline:
        parts.append("能力基线 " + "、".join(f"{k}{v}" for k, v in baseline.items()))
    return "\n".join(p for p in parts if p and p.strip())


def resume_row(parsed: ParsedResume, file: ResumeFile | None, vector: list[float]) -> dict:
    """写 resume_vectors 的唯一入口。

    铁律：Milvus 的 upsert 是**整行替换**，不是字段合并。任何地方要写简历向量，
    必须调这个函数拼 payload；自己手搓 {id, vector, name} 会把其它标量字段覆盖成空。
    """
    return {
        "id": int(parsed.id),
        "vector": vector,
        "name": parsed.name or "",
        "education": parsed.education or "",
        "major": parsed.major or "",
        "years": int(parsed.years_experience or 0),
        "skills": _skills_text(parsed.skills)[:500],
        "filename": (file.filename if file else "")[:200],
        "dept_id": int(getattr(file, "dept_id", 0) or 0),
        "created_by": int(getattr(file, "created_by", 0) or 0),
    }


def index_resumes(db: Session, resume_ids: list[int] | None = None) -> dict:
    query = (
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    )
    if resume_ids:
        query = query.where(ParsedResume.id.in_([int(i) for i in resume_ids]))
    rows = db.execute(query.order_by(ParsedResume.id)).all()
    if not rows:
        return {"indexed": 0, "total": 0, "available": embedder.available and store.available}

    texts = [resume_text(p) for p, _f in rows]
    vectors = embedder.embed(texts)
    if vectors is None:
        return {"indexed": 0, "total": len(rows), "available": False,
                "reason": "嵌入服务不可用（Ollama bge-m3 未就绪）"}
    payload = [resume_row(p, f, v) for (p, f), v in zip(rows, vectors)]
    indexed = store.upsert(settings.milvus_resume_collection, payload)

    # 清掉陈旧向量：被替代/已删除的简历不应留在集合里，否则行数永远对不上，
    # ensure_indexed 会每次判定"过期"并全量重建。
    pruned = prune_stale_vectors(db, {int(p.id) for p, _f in rows})
    return {"indexed": indexed, "total": len(rows), "available": True,
            "pruned": pruned, "collection": settings.milvus_resume_collection}


def live_resume_ids(db: Session) -> set[int]:
    """当前应存在于向量库的简历 id（已解析完成 + 现行）。"""
    return {int(i) for i in db.execute(
        select(ParsedResume.id)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    ).scalars()}


def prune_stale_vectors(db: Session, keep: set[int] | None = None) -> int:
    """删除向量库中不属于 keep 集合的行。返回删除数量。

    Milvus 的 upsert 不会自动清理"已不存在的主键"，所以简历被替代或删除后，
    旧向量会一直留在集合里。这里按主键差集显式删除。
    """
    if not store.available:
        return 0
    live = keep if keep is not None else live_resume_ids(db)
    client = store._get_client()
    if client is None:
        return 0
    try:
        if not client.has_collection(settings.milvus_resume_collection):
            return 0
        rows = client.query(collection_name=settings.milvus_resume_collection,
                            filter="id >= 0", output_fields=["id"])
        existing = {int(r.get("id") or 0) for r in rows}
    except Exception:
        return 0
    stale = sorted(existing - live)
    if not stale:
        return 0
    store.delete(settings.milvus_resume_collection, stale)
    return len(stale)


def expected_resume_count(db: Session) -> int:
    """库里应被索引的简历数（已解析完成 + 现行）。"""
    return int(db.execute(
        select(func.count()).select_from(
            select(ParsedResume.id)
            .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
            .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True)).subquery()
        )
    ).scalar_one())


def is_stale(db: Session) -> bool:
    """向量库行数与应索引数不一致 → 视为过期。"""
    if not store.available:
        return False
    return store.count(settings.milvus_resume_collection) != expected_resume_count(db)


def ensure_indexed(db: Session) -> dict:
    """幂等索引：行数不对就全量重建，对了就跳过。

    查重/语义召回不再自己写向量库，统一调这个——从结构上消灭"手搓 payload"。
    """
    if not (store.available and embedder.available):
        return {"rebuilt": False, "available": False, "reason": "向量能力不可用"}
    expected = expected_resume_count(db)
    current = store.count(settings.milvus_resume_collection)
    if current == expected and expected > 0:
        return {"rebuilt": False, "available": True, "count": current, "expected": expected}
    out = index_resumes(db)
    out["rebuilt"] = True
    out["expected"] = expected
    out["count"] = store.count(settings.milvus_resume_collection)
    return out


def index_jobs(db: Session, job_ids: list[int] | None = None) -> dict:
    query = select(JobProfile).where(JobProfile.status == "active")
    if job_ids:
        query = query.where(JobProfile.id.in_([int(i) for i in job_ids]))
    jobs = db.execute(query.order_by(JobProfile.id)).scalars().all()
    if not jobs:
        return {"indexed": 0, "total": 0, "available": embedder.available and store.available}
    vectors = embedder.embed([job_text(j) for j in jobs])
    if vectors is None:
        return {"indexed": 0, "total": len(jobs), "available": False,
                "reason": "嵌入服务不可用（Ollama bge-m3 未就绪）"}
    payload = [{"id": int(j.id), "vector": v, "name": j.name or "",
                "threshold": int(j.passing_threshold or 70)} for j, v in zip(jobs, vectors)]
    indexed = store.upsert(settings.milvus_job_collection, payload)
    return {"indexed": indexed, "total": len(jobs), "available": True,
            "collection": settings.milvus_job_collection}


def status(db: Session | None = None) -> dict:
    out = {
        "embed": {"available": embedder.available, "model": settings.embed_model, "dim": settings.embed_dim},
        "milvus": {"available": store.available, "uri": settings.milvus_uri,
                   "resume_collection": settings.milvus_resume_collection,
                   "job_collection": settings.milvus_job_collection,
                   "resume_count": store.count(settings.milvus_resume_collection),
                   "job_count": store.count(settings.milvus_job_collection)},
    }
    if db is not None and store.available:
        expected = expected_resume_count(db)
        current = out["milvus"]["resume_count"]
        out["milvus"]["expected_count"] = expected
        out["milvus"]["stale"] = current != expected
    return out


def _scoped_resume_ids(db: Session, user: CurrentUser) -> set[int] | None:
    """返回用户可见的 parsed_resume id 集合；全部可见时返回 None（不过滤）。"""
    if max_scope(user, "resume", "match") == "all":
        return None
    query = (
        select(ParsedResume.id)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    )
    query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))
    return {int(i) for i in db.execute(query).scalars()}


def semantic_search_resumes(db: Session, user: CurrentUser, query: str, top_k: int = 10) -> dict:
    query = (query or "").strip()
    if not query:
        raise ApiError(400, "检索词不能为空")
    vector = embedder.embed_one(query)
    if vector is None:
        return {"available": False, "items": [], "reason": "嵌入服务不可用"}

    hits = store.search(settings.milvus_resume_collection, vector, top_k=max(top_k * 3, 20))
    allowed = _scoped_resume_ids(db, user)
    briefs = briefs_by_ids(db, [int(h.get("id") or 0) for h in hits], user)

    items = []
    for h in hits:
        rid = int(h.get("id") or 0)
        if allowed is not None and rid not in allowed:
            continue
        brief = briefs.get(rid)
        if brief is None:
            continue  # 向量里有、库里没有（已删除的残留），跳过而不是返回空名字
        items.append({**brief, "score": round(float(h.get("score", 0)), 4)})
        if len(items) >= top_k:
            break
    return {"available": True, "query": query, "items": items, "total": len(items)}


def find_duplicates(db: Session, user: CurrentUser, threshold: float = 0.93) -> dict:
    """查重：每份简历取向量近邻，同一个 ID 只保留一次，相似度≥阈值即判重复。

    - 写入向量库统一走 ensure_indexed()，不自己拼 payload（否则整行替换会抹空字段）；
    - 返回成对的 `brief`，前端点任一方都能跳 `GET /api/resumes/{id}`；
    - 越权的一方**不剔除**，标 `accessible=false` 让前端置灰——查重是"告诉你这两份像"，
      把另一半藏起来会让用户以为系统算错了。
    """
    if not (store.available and embedder.available):
        return {"available": False, "pairs": [], "reason": "向量能力不可用"}

    indexed = ensure_indexed(db)
    if not indexed.get("available"):
        return {"available": False, "pairs": [], "reason": indexed.get("reason", "索引不可用")}

    rows = db.execute(
        select(ParsedResume).where(ParsedResume.is_current.is_(True)).order_by(ParsedResume.id)
    ).scalars().all()
    if not rows:
        return {"available": True, "pairs": []}

    vectors = embedder.embed([resume_text(p) for p in rows])
    if vectors is None:
        return {"available": False, "pairs": [], "reason": "嵌入失败"}

    seen: set[tuple[int, int]] = set()
    raw: list[tuple[int, int, float]] = []
    for p, v in zip(rows, vectors):
        for h in store.search(settings.milvus_resume_collection, v, top_k=3):
            other = int(h.get("id") or 0)
            if other == int(p.id):
                continue
            key = (min(int(p.id), other), max(int(p.id), other))
            if key in seen:
                continue
            score = float(h.get("score", 0))
            if score >= threshold:
                seen.add(key)
                raw.append((key[0], key[1], score))

    # 回显字段回 MySQL 取（Milvus 只给 id 与相似度）
    briefs = briefs_by_ids(db, [i for a, b, _s in raw for i in (a, b)], user)
    pairs = []
    for a, b, score in raw:
        a_brief, b_brief = briefs.get(a), briefs.get(b)
        if a_brief is None or b_brief is None:
            continue  # 库里已删的残留，跳过
        # 双方都不可访问 → 整对丢弃（否则越权用户能通过查重看到别人的姓名）
        # 只有一方不可访问 → 保留并标 accessible=false，让前端置灰（"这两份像"的语义要完整）
        if not a_brief["accessible"] and not b_brief["accessible"]:
            continue
        pairs.append({"similarity": round(score, 4), "a": a_brief, "b": b_brief,
                      "a_name": a_brief["name"], "b_name": b_brief["name"],
                      "a_id": a, "b_id": b})
    pairs.sort(key=lambda x: -x["similarity"])
    return {"available": True, "threshold": threshold, "pairs": pairs, "total": len(pairs)}


def job_semantic_candidates(db: Session, user: CurrentUser, job_id: int, top_k: int = 10) -> dict:
    """岗位向量 → 语义召回候选人（与规则储备池互补：这个看"像不像"，那个看"够不够"）。"""
    job = db.get(JobProfile, job_id)
    if job is None or job.status == "deleted":
        raise ApiError(404, "岗位条件不存在")
    vector = embedder.embed_one(job_text(job))
    if vector is None:
        return {"available": False, "items": [], "reason": "嵌入服务不可用"}

    store.upsert(settings.milvus_job_collection,
                 [{"id": int(job.id), "vector": vector, "name": job.name or "",
                   "threshold": int(job.passing_threshold or 70)}])
    hits = store.search(settings.milvus_resume_collection, vector, top_k=max(top_k * 3, 20))
    allowed = _scoped_resume_ids(db, user)
    briefs = briefs_by_ids(db, [int(h.get("id") or 0) for h in hits], user)
    items = []
    for h in hits:
        rid = int(h.get("id") or 0)
        if allowed is not None and rid not in allowed:
            continue
        brief = briefs.get(rid)
        if brief is None:
            continue
        items.append({**brief, "similarity": round(float(h.get("score", 0)), 4)})
        if len(items) >= top_k:
            break
    return {"available": True, "job_id": job_id, "job_name": job.name, "items": items}
