"""测评任务（HR 把试卷绑定给候选人）：创建 / 查询 / 取消，以及"简历列表显示已测评"的汇总。

设计要点（需求④）：
- 一个「简历 × 试卷」只允许一条 `pending`；重复绑定返回已存在的那条，不报错（幂等）。
- 取消是置 `cancelled`，不物理删除——保留审计轨迹。
- 简历列表的 `exam_summary` 必须**批量查询**：本页 N 条简历只查 2 次库，
  不能逐条查（N+1）。
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.response import ApiError
from app.models.orm import (
    Exam, ExamAssignment, ExamSubmission, ParsedResume, ResumeFile,
)

STATE_LABELS = {"none": "未测评", "assigned": "待测评", "submitted": "已测评"}


def _serialize(a: ExamAssignment, exam: Exam | None, submission: ExamSubmission | None) -> dict:
    return {
        "id": a.id,
        "exam_id": a.exam_id,
        "exam_name": exam.name if exam else "",
        "audience": (exam.audience if exam else "candidate") or "candidate",
        "parsed_resume_id": a.parsed_resume_id,
        "candidate_name": a.candidate_name,
        "status": a.status,
        "submission_id": a.submission_id,
        "assigned_by": a.assigned_by,
        "deadline": a.deadline.isoformat(sep=" ", timespec="seconds") if a.deadline else None,
        "note": a.note,
        "created_at": a.created_at.isoformat(sep=" ", timespec="seconds") if a.created_at else "",
        "result": None if submission is None else {
            "score": submission.score,
            "max_score": submission.max_score,
            "pass_score": submission.pass_score,
            "passed": submission.result == "passed",
        },
    }


def _resume_of(db: Session, user: CurrentUser, parsed_resume_id: int) -> ParsedResume:
    row = db.execute(
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ParsedResume.id == int(parsed_resume_id))
    ).first()
    if row is None:
        raise ApiError(404, "简历不存在")
    parsed, file = row
    scope = user.scope_of("resume")
    if scope != "all":
        visible = (file.dept_id == user.department_id) if scope == "dept" else (file.created_by == user.id)
        if not visible:
            raise ApiError(403, "无权操作该简历")
    return parsed


def create_assignments(db: Session, user: CurrentUser, payload: dict) -> dict:
    """绑定试卷给候选人。支持单条与批量（parsed_resume_ids 数组）。"""
    exam_id = payload.get("exam_id")
    if not exam_id or db.get(Exam, int(exam_id)) is None:
        raise ApiError(400, "试卷不存在")
    exam = db.get(Exam, int(exam_id))

    ids = payload.get("parsed_resume_ids")
    if ids is None:
        single = payload.get("parsed_resume_id")
        ids = [single] if single else []
    ids = [int(i) for i in ids if i]
    if not ids:
        raise ApiError(400, "至少要指定一份简历")

    deadline = None
    raw_deadline = payload.get("deadline")
    if raw_deadline:
        try:
            deadline = datetime.fromisoformat(str(raw_deadline).replace("Z", ""))
        except ValueError:
            raise ApiError(400, "deadline 格式应为 YYYY-MM-DD HH:MM:SS")

    note = str(payload.get("note") or "")
    created, existed, failed = [], [], []
    for rid in ids:
        try:
            parsed = _resume_of(db, user, rid)
        except ApiError as exc:
            failed.append({"parsed_resume_id": rid, "reason": exc.message})
            continue

        current = db.execute(
            select(ExamAssignment).where(
                ExamAssignment.exam_id == int(exam_id),
                ExamAssignment.parsed_resume_id == rid,
                ExamAssignment.status == "pending",
            )
        ).scalar_one_or_none()
        if current is not None:
            existed.append(_serialize(current, exam, None))
            continue

        row = ExamAssignment(
            exam_id=int(exam_id),
            parsed_resume_id=rid,
            candidate_name=parsed.name or "",
            status="pending",
            assigned_by=user.id,
            deadline=deadline,
            note=note,
        )
        db.add(row)
        db.flush()
        created.append(_serialize(row, exam, None))

    db.commit()
    return {"created": created, "existed": existed, "failed": failed,
            "created_count": len(created), "existed_count": len(existed), "failed_count": len(failed)}


def list_assignments(db: Session, parsed_resume_id: int | None, exam_id: int | None,
                     status: str | None) -> dict:
    query = select(ExamAssignment).order_by(ExamAssignment.id.desc())
    if parsed_resume_id:
        query = query.where(ExamAssignment.parsed_resume_id == int(parsed_resume_id))
    if exam_id:
        query = query.where(ExamAssignment.exam_id == int(exam_id))
    if status:
        query = query.where(ExamAssignment.status == status)
    rows = db.execute(query).scalars().all()

    exams = {e.id: e for e in db.execute(
        select(Exam).where(Exam.id.in_([r.exam_id for r in rows] or [0]))).scalars()}
    subs = {s.id: s for s in db.execute(
        select(ExamSubmission).where(
            ExamSubmission.id.in_([r.submission_id for r in rows if r.submission_id] or [0]))).scalars()}
    items = [_serialize(r, exams.get(r.exam_id), subs.get(r.submission_id) if r.submission_id else None)
             for r in rows]
    return {"items": items, "total": len(items)}


def cancel_assignment(db: Session, assignment_id: int) -> dict:
    row = db.get(ExamAssignment, int(assignment_id))
    if row is None:
        raise ApiError(404, "测评任务不存在")
    if row.status == "submitted":
        raise ApiError(409, "已提交的测评任务不能取消")
    row.status = "cancelled"
    db.commit()
    return {"id": row.id, "status": row.status}


def summaries_for(db: Session, parsed_ids: list[int]) -> dict[int, dict]:
    """批量算「已测评」汇总：本页 N 条简历只查 2 次库（禁止 N+1）。

    返回 {parsed_resume_id: exam_summary}；没有测评记录的简历给 state=none。
    """
    clean = [int(i) for i in parsed_ids if i]
    if not clean:
        return {}

    assigns = db.execute(
        select(ExamAssignment).where(
            ExamAssignment.parsed_resume_id.in_(clean),
            ExamAssignment.status.in_(["pending", "submitted"]),
        ).order_by(ExamAssignment.id)
    ).scalars().all()
    exam_ids = {a.exam_id for a in assigns} or {0}
    exams = {e.id: e for e in db.execute(select(Exam).where(Exam.id.in_(list(exam_ids)))).scalars()}
    sub_ids = [a.submission_id for a in assigns if a.submission_id] or [0]
    subs = {s.id: s for s in db.execute(
        select(ExamSubmission).where(ExamSubmission.id.in_(sub_ids))).scalars()}

    # 历史答卷（没有绑定记录、但按 parsed_resume_id 直接归属的）
    extra_subs = db.execute(
        select(ExamSubmission).where(
            ExamSubmission.parsed_resume_id.in_(clean),
            ExamSubmission.id.notin_(sub_ids),
        ).order_by(ExamSubmission.id)
    ).scalars().all()
    extra_exams = {e.id: e for e in db.execute(
        select(Exam).where(Exam.id.in_([s.exam_id for s in extra_subs] or [0]))).scalars()}

    grouped: dict[int, list[dict]] = {i: [] for i in clean}
    for a in assigns:
        exam = exams.get(a.exam_id)
        sub = subs.get(a.submission_id) if a.submission_id else None
        grouped[a.parsed_resume_id].append({
            "exam_id": a.exam_id,
            "exam_name": exam.name if exam else "",
            "audience": (exam.audience if exam else "candidate") or "candidate",
            "state": "submitted" if a.status == "submitted" else "assigned",
            "assignment_id": a.id,
            "submission_id": a.submission_id,
            "deadline": a.deadline.isoformat(sep=" ", timespec="seconds") if a.deadline else None,
            "score": sub.score if sub else None,
            "max_score": sub.max_score if sub else None,
            "pass_score": sub.pass_score if sub else None,
            "passed": (sub.result == "passed") if sub else None,
            "submitted_at": None,
        })
    for s in extra_subs:
        exam = extra_exams.get(s.exam_id)
        grouped.setdefault(s.parsed_resume_id, []).append({
            "exam_id": s.exam_id,
            "exam_name": exam.name if exam else "",
            "audience": (exam.audience if exam else "candidate") or "candidate",
            "state": "submitted",
            "assignment_id": None,
            "submission_id": s.id,
            "deadline": None,
            "score": s.score,
            "max_score": s.max_score,
            "pass_score": s.pass_score,
            "passed": s.result == "passed",
            "submitted_at": None,
        })

    out: dict[int, dict] = {}
    for pid, items in grouped.items():
        submitted = [i for i in items if i["state"] == "submitted"]
        if submitted:
            state = "submitted"
        elif items:
            state = "assigned"
        else:
            state = "none"
        out[pid] = {
            "state": state,
            "label": STATE_LABELS[state],
            "total": len(items),
            "passed": sum(1 for i in submitted if i.get("passed")),
            "items": items,
        }
    return out
