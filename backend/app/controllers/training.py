from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ok, page
from app.services import training_service

router = APIRouter(tags=["培训成长"])


@router.get("/training-courses")
def list_courses(keyword: str = Query(default=""), page_no: int = Query(default=1, alias="page", ge=1),
                 page_size: int = Query(default=50, ge=1, le=200),
                 db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("train", "view"))):
    items, total = training_service.list_courses(db, keyword, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.post("/training-courses")
def create_course(payload: dict, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "create"))):
    return ok(training_service.create_course(db, payload))


@router.put("/training-courses/{course_id}")
def update_course(course_id: int, payload: dict, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "edit"))):
    return ok(training_service.update_course(db, course_id, payload))


@router.delete("/training-courses/{course_id}")
def delete_course(course_id: int, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "delete"))):
    training_service.delete_course(db, course_id)
    return ok({"deleted": course_id})


@router.get("/training/diagnose")
def diagnose(candidate_id: int = Query(...), job_id: int = Query(...),
             db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("train", "view"))):
    training_service.assert_candidate_scope(db, user, candidate_id)
    return ok(training_service.diagnose(db, candidate_id, job_id))


@router.post("/prejob-plans/generate")
def generate_plan(payload: dict, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "create"))):
    candidate_id = int(payload.get("candidate_id"))
    job_id = int(payload.get("job_id") or 0)
    weeks = int(payload.get("weeks") or 4)
    mentor = str(payload.get("mentor") or "")
    return ok(training_service.generate_plan(db, user, candidate_id, job_id, weeks, mentor))


@router.get("/prejob-plans")
def list_plans(candidate_id: int | None = Query(default=None), page_no: int = Query(default=1, alias="page", ge=1),
               page_size: int = Query(default=20, ge=1, le=200),
               db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("train", "view"))):
    if candidate_id:
        training_service.assert_candidate_scope(db, user, candidate_id)
    else:
        # 没传 candidate_id 时，self 范围的账号只能看到自己的
        own = training_service.self_candidate_id(db, user)
        if own is not None:
            candidate_id = own
        elif training_service.is_self_scoped(user):
            return ok(page([], 0, page_no, page_size))
    items, total = training_service.list_plans(db, candidate_id, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.get("/prejob-plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_perm("train", "view"))):
    training_service.assert_plan_scope(db, user, plan_id)
    return ok(training_service.get_plan(db, plan_id))


@router.post("/prejob-plans/tasks/{task_id}/progress")
def progress_task(task_id: int, payload: dict, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "edit"))):
    training_service.assert_task_owner(db, user, task_id)
    return ok(training_service.progress_task(db, task_id, int(payload.get("minutes") or 0), int(payload.get("progress") or 0)))


@router.post("/prejob-plans/tasks/{task_id}/complete")
def complete_task(task_id: int, db: Session = Depends(get_db),
                  user: CurrentUser = Depends(require_perm("train", "edit"))):
    training_service.assert_task_owner(db, user, task_id)
    return ok(training_service.complete_task(db, task_id))


@router.post("/prejob-plans/tasks/{task_id}/assess")
def assess_task(task_id: int, payload: dict, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("train", "edit"))):
    training_service.assert_task_owner(db, user, task_id)
    return ok(training_service.assess_task(db, task_id, int(payload.get("submission_id"))))


@router.get("/training/ledger")
def ledger(candidate_id: int = Query(...), page_no: int = Query(default=1, alias="page", ge=1),
           page_size: int = Query(default=20, ge=1, le=200),
           db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("train", "view"))):
    training_service.assert_candidate_scope(db, user, candidate_id)
    items, total = training_service.ledger(db, candidate_id, page_no, page_size)
    return ok(page(items, total, page_no, page_size))
