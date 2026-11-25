from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok, page
from app.services import talent_service
from app.infrastructure.ai_gateway import gateway

router = APIRouter(prefix="/talent-profiles", tags=["人才画像"])


@router.get("")
def list_profiles(
    keyword: str = Query(default=""),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("talent", "view")),
):
    items, total = talent_service.list_profiles(db, user, keyword, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.post("/generate")
def generate(payload: dict | None = None, db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_perm("talent", "create"))):
    payload = payload or {}
    resume_id = payload.get("resume_id")
    use_ai = bool(payload.get("use_ai", True))
    use_exam = bool(payload.get("use_exam", True))
    return ok(talent_service.generate(db, user, int(resume_id) if resume_id else None, use_ai, use_exam))


@router.get("/{profile_id}")
def detail(profile_id: int, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("talent", "view"))):
    return ok(talent_service.get_profile(db, user, profile_id))


@router.get("/{profile_id}/trend")
def trend(profile_id: int, db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_perm("talent", "view"))):
    return ok(talent_service.ability_trend(db, user, profile_id))


@router.get("/{profile_id}/analysis")
def analysis(profile_id: int, job_id: int | None = Query(default=None),
             db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_perm("talent", "view"))):
    return ok(talent_service.analysis_report(db, user, profile_id, job_id))


@router.get("/meta/skills")
def skills(user: CurrentUser = Depends(require_perm("talent", "view"))):
    return ok(talent_service.skill_catalog())
