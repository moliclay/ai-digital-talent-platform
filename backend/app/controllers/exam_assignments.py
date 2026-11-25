"""测评任务（绑定）路由：HR 把试卷绑定给候选人（需求④）。"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok
from app.services import assignment_service

router = APIRouter(prefix="/exam-assignments", tags=["测评任务"])


@router.post("")
def create(payload: dict, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("exam", "create"))):
    """绑定试卷给候选人。支持单条（parsed_resume_id）与批量（parsed_resume_ids 数组）。"""
    return ok(assignment_service.create_assignments(db, user, payload))


@router.get("")
def list_all(
    parsed_resume_id: int | None = Query(default=None),
    exam_id: int | None = Query(default=None),
    status: str | None = Query(default=None, description="pending / submitted / cancelled"),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("exam", "view")),
):
    return ok(assignment_service.list_assignments(db, parsed_resume_id, exam_id, status))


@router.delete("/{assignment_id}")
def cancel(assignment_id: int, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("exam", "create"))):
    """取消绑定：置 cancelled，不物理删除。"""
    return ok(assignment_service.cancel_assignment(db, assignment_id))
