from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import CurrentUser, require_perm
from app.core.response import ApiError, ok, page
from app.infrastructure.ai_gateway import gateway
from app.services import exam_service

router = APIRouter(tags=["智能测评"])


@router.get("/question-banks")
def banks(audience: str = Query(default="", description="candidate / employee，留空返回全部"),
          db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.list_banks(db, audience))


@router.post("/question-banks")
def create_bank(payload: dict, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("exam", "create"))):
    return ok(exam_service.create_bank(db, payload))


@router.get("/questions")
def questions(
    bank_id: int | None = Query(default=None),
    page_no: int = Query(default=1, alias="page", ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: CurrentUser = Depends(require_perm("exam", "view")),
):
    items, total = exam_service.list_questions(db, bank_id, page_no, page_size)
    return ok(page(items, total, page_no, page_size))


@router.post("/questions")
def create_question(payload: dict, db: Session = Depends(get_db),
                    user: CurrentUser = Depends(require_perm("exam", "create"))):
    return ok(exam_service.create_question(db, payload))


@router.get("/exams")
def exams(audience: str = Query(default="", description="candidate / employee，留空返回全部"),
          db: Session = Depends(get_db), user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.list_exams(db, audience))


@router.post("/exams")
def create_exam(payload: dict, db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("exam", "create"))):
    return ok(exam_service.create_exam(db, payload))


@router.get("/exams/{exam_id}")
def paper(exam_id: int, db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.get_paper(db, exam_id))


@router.post("/exams/adaptive")
def adaptive(payload: dict, db: Session = Depends(get_db),
             user: CurrentUser = Depends(require_perm("exam", "create"))):
    """按错题知识点 + 画像弱项组一份千人千卷（直接落库为已发布试卷）。"""
    return ok(exam_service.adaptive_paper(db, payload))


@router.post("/exams/{exam_id}/submit")
def submit(exam_id: int, payload: dict, db: Session = Depends(get_db),
           user: CurrentUser = Depends(require_perm("exam", "view"))):
    name = str(payload.get("candidate_name") or "").strip()
    answers = payload.get("answers")
    if not isinstance(answers, list):
        raise ApiError(400, "answers 必须是数组")
    return ok(exam_service.submit(
        db, user, exam_id, name, answers,
        assignment_id=payload.get("assignment_id"),
        parsed_resume_id=payload.get("parsed_resume_id"),
    ))


@router.get("/exam-submissions")
def submissions(exam_id: int | None = Query(default=None), db: Session = Depends(get_db),
                user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.list_submissions(db, exam_id))


@router.get("/exam-submissions/{submission_id}")
def submission(submission_id: int, db: Session = Depends(get_db),
               user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.get_submission(db, submission_id))


@router.get("/wrong-questions")
def wrong(candidate_name: str | None = Query(default=None), db: Session = Depends(get_db),
          user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.list_wrong(db, candidate_name))


@router.get("/review-plans")
def review_plans(candidate_name: str | None = Query(default=None), db: Session = Depends(get_db),
                 user: CurrentUser = Depends(require_perm("exam", "view"))):
    return ok(exam_service.list_review_plans(db, candidate_name))


@router.get("/ai/status")
def ai_status(user: CurrentUser = Depends(require_perm("exam", "view"))):
    """让前端知道当前 AI 是否可用（解析/画像/评分会据此说明口径）。"""
    return ok({"available": gateway.available})
