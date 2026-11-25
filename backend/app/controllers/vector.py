from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok
from app.services import vector_service

router = APIRouter(tags=["向量能力"])


@router.get("/vector/status")
def vector_status(db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("resume", "view"))):
    return ok(vector_service.status(db))


@router.post("/vector/reindex-if-stale")
def reindex_if_stale(db: Session = Depends(get_db),
                     user: CurrentUser = Depends(require_perm("resume", "create"))):
    """向量库行数与应索引数不一致时才重建；一致则直接返回 rebuilt=false。"""
    return ok(vector_service.ensure_indexed(db))


@router.post("/vector/index")
def build_index(payload: dict | None = None, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("resume", "create"))):
    """把简历与岗位写入向量库（幂等，可重复执行）。"""
    payload = payload or {}
    resume_ids = payload.get("resume_ids")
    job_ids = payload.get("job_ids")
    out = {"resumes": vector_service.index_resumes(db, [int(i) for i in resume_ids] if resume_ids else None),
           "jobs": vector_service.index_jobs(db, [int(i) for i in job_ids] if job_ids else None)}
    out["status"] = vector_service.status()
    return ok(out)


@router.get("/resumes/semantic")
def semantic_search(q: str = Query(..., min_length=1), top_k: int = Query(default=10, ge=1, le=50),
                    db: Session = Depends(get_db),
                    user: CurrentUser = Depends(require_perm("resume", "view"))):
    """自然语言检索简历（如「做过 RAG 的算法工程师」）。"""
    return ok(vector_service.semantic_search_resumes(db, user, q, top_k))


@router.get("/resumes/duplicates")
def duplicates(threshold: float = Query(default=0.93, ge=0.5, le=0.999),
               db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("resume", "view"))):
    """简历查重：向量相似度 ≥ 阈值即判为疑似重复，成对返回 brief（可点进详情）。"""
    return ok(vector_service.find_duplicates(db, user, threshold))
