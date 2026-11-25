from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ApiError, ok, page
from app.services import match_service

router = APIRouter(prefix="/matching", tags=["匹配"])


@router.post("/run")
def run(payload: dict, db: Session = Depends(get_db),
        user: CurrentUser = Depends(require_perm("match", "create"))):
    job_id = payload.get("job_profile_id")
    if not job_id:
        raise ApiError(400, "job_profile_id 必填")
    resume_ids = payload.get("resume_ids")
    return ok(match_service.run(db, user, int(job_id), resume_ids))


@router.get("/summary")
def summary(job_profile_id: int = Query(...), db: Session = Depends(get_db),
            user: CurrentUser = Depends(require_perm("match", "view"))):
    return ok(match_service.summary(db, job_profile_id))


@router.get("/lists")
def lists(
    job_profile_id: int | None = Query(default=None),
    passed: bool | None = Query(default=None),
    keyword: str = Query(default=""),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=20, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("match", "view")),
):
    items, total = match_service.lists(db, user, job_profile_id, passed, keyword, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.get("/{match_id:int}")
def detail(match_id: int, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("match", "view"))):
    return ok(match_service.detail(db, user, match_id))
