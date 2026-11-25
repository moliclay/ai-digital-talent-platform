from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok, page
from app.services import job_service

router = APIRouter(tags=["岗位条件"])


@router.get("/positions")
def positions(db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("job", "view"))):
    return ok(job_service.list_positions(db))


@router.get("/job-profiles")
def list_jobs(
    keyword: str = Query(default=""),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("job", "view")),
):
    items, total = job_service.list_jobs(db, keyword, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.post("/job-profiles")
def create_job(payload: dict, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("job", "create"))):
    return ok(job_service.create_job(db, payload))


@router.get("/job-profiles/alerts")
def vacancy_alerts(db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("job", "view"))):
    return ok(job_service.vacancy_alerts(db, user))


@router.post("/job-profiles/parse-jd")
def parse_jd(payload: dict, user: CurrentUser = Depends(require_perm("job", "create"))):
    """JD 文本 → 岗位条件草稿（不落库，HR 确认后再保存）。"""
    from app.services import jd_service
    return ok(jd_service.parse_jd(str(payload.get("text") or "")))


@router.get("/job-profiles/{job_id}/reserve")
def reserve_pool(job_id: int, db: Session = Depends(get_db),
                 user: CurrentUser = Depends(require_perm("job", "view"))):
    return ok(job_service.reserve_pool(db, user, job_id))


@router.get("/job-profiles/{job_id}/semantic-candidates")
def semantic_candidates(job_id: int, top_k: int = Query(default=10, ge=1, le=50),
                        db: Session = Depends(get_db),
                        user: CurrentUser = Depends(require_perm("job", "view"))):
    from app.services import vector_service
    return ok(vector_service.job_semantic_candidates(db, user, job_id, top_k))


@router.get("/job-profiles/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("job", "view"))):
    job = job_service.get_job(db, job_id)
    return ok(job_service._serialize(job))


@router.put("/job-profiles/{job_id}")
def update_job(job_id: int, payload: dict, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("job", "edit"))):
    return ok(job_service.update_job(db, job_id, payload))


@router.delete("/job-profiles/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("job", "delete"))):
    job_service.delete_job(db, job_id)
    return ok({"deleted": job_id})


@router.get("/job-profiles/{job_id}/summary")
def summary(job_id: int, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("job", "view"))):
    return ok(job_service.match_summary(db, job_id))


@router.post("/job-profiles/{job_id}/dry-run")
def dry_run(job_id: int, db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("job", "view"))):
    return ok(job_service.dry_run(db, user, job_id))
