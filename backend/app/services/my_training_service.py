"""员工自助：我的培训（需求⑤）。

解析路径：`user.id` → `parsed_resumes.employee_user_id` → `parsed_resume.id`
          → `prejob_plans.candidate_id` → 计划/任务/台账

未关联账号时返回空列表 + `onboarded: false`（不是 404），
因为 HR 也可能调这些接口（看到的是自己的，通常为空）。
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.response import ApiError
from app.models.orm import (
    GrowthLedger, ParsedResume, PrejobPlan, PrejobPlanTask, TalentProfile,
)


def my_candidate_id(db: Session, user: CurrentUser) -> int | None:
    """当前登录账号对应的候选人 id（parsed_resumes.id）；未转正返回 None。"""
    parsed = db.execute(
        select(ParsedResume).where(ParsedResume.employee_user_id == int(user.id))
    ).scalars().first()
    return int(parsed.id) if parsed else None


def _onboard_state(db: Session, user: CurrentUser) -> dict:
    cid = my_candidate_id(db, user)
    return {"onboarded": cid is not None, "candidate_id": cid}


def _my_plans(db: Session, candidate_id: int) -> list[PrejobPlan]:
    return list(db.execute(
        select(PrejobPlan)
        .where(PrejobPlan.candidate_id == int(candidate_id), PrejobPlan.status == "generated")
        .order_by(PrejobPlan.id.desc())
    ).scalars().all())


def _tasks_of(db: Session, plan_id: int) -> list[PrejobPlanTask]:
    return list(db.execute(
        select(PrejobPlanTask)
        .where(PrejobPlanTask.plan_id == int(plan_id))
        .order_by(PrejobPlanTask.phase_index, PrejobPlanTask.id)
    ).scalars().all())


def _task_dict(t: PrejobPlanTask) -> dict:
    return {
        "id": t.id, "plan_id": t.plan_id, "phase_index": t.phase_index, "title": t.title,
        "dimension": t.dimension, "course_id": t.course_id, "exam_id": t.exam_id,
        "required_minutes": t.required_minutes, "study_minutes": t.study_minutes,
        "progress": t.progress, "status": t.status,
        "detail": t.detail or {},
    }


def summary(db: Session, user: CurrentUser) -> dict:
    """我的培训概览：计划数、任务进度、待办、台账条数。"""
    state = _onboard_state(db, user)
    if not state["onboarded"]:
        return {**state, "plans": 0, "tasks": 0, "done_tasks": 0, "pending_tasks": 0,
                "progress_pct": 0, "ledger": 0, "todo": []}

    cid = state["candidate_id"]
    plans = _my_plans(db, cid)
    all_tasks = []
    for p in plans:
        all_tasks.extend(_tasks_of(db, p.id))
    done = [t for t in all_tasks if t.status == "done"]
    pending = [t for t in all_tasks if t.status != "done"]
    ledger_count = len(db.execute(
        select(GrowthLedger).where(GrowthLedger.candidate_id == cid)
    ).scalars().all())
    pct = round(100 * len(done) / len(all_tasks)) if all_tasks else 0

    return {
        **state,
        "candidate_name": (plans[0].candidate_name if plans else ""),
        "plans": len(plans),
        "tasks": len(all_tasks),
        "done_tasks": len(done),
        "pending_tasks": len(pending),
        "progress_pct": pct,
        "ledger": ledger_count,
        "todo": [_task_dict(t) for t in pending[:5]],
    }


def plans(db: Session, user: CurrentUser) -> dict:
    """我的培养计划（含任务明细）。"""
    state = _onboard_state(db, user)
    if not state["onboarded"]:
        return {**state, "items": [], "total": 0}

    items = []
    for p in _my_plans(db, state["candidate_id"]):
        tasks = _tasks_of(db, p.id)
        done = sum(1 for t in tasks if t.status == "done")
        items.append({
            "id": p.id, "plan_title": p.plan_title, "goal": p.goal,
            "position_name": p.position_name, "total_weeks": p.total_weeks,
            "mentor": p.mentor, "status": p.status,
            "total_tasks": len(tasks), "done_tasks": done,
            "progress_pct": round(100 * done / len(tasks)) if tasks else 0,
            "tasks": [_task_dict(t) for t in tasks],
        })
    return {**state, "items": items, "total": len(items)}


def ledger(db: Session, user: CurrentUser) -> dict:
    """我的成长台账。"""
    state = _onboard_state(db, user)
    if not state["onboarded"]:
        return {**state, "items": [], "total": 0}

    rows = db.execute(
        select(GrowthLedger)
        .where(GrowthLedger.candidate_id == state["candidate_id"])
        .order_by(GrowthLedger.id.desc())
    ).scalars().all()
    items = [{
        "id": r.id, "dimension": r.dimension,
        "before_score": r.before_score, "after_score": r.after_score, "delta": r.delta,
        "source": r.source, "note": r.note,
        "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
    } for r in rows]
    return {**state, "items": items, "total": len(items)}


def assert_task_owner(db: Session, user: CurrentUser, task: PrejobPlanTask) -> None:
    """任务归属校验（安全项）：员工只能操作自己的任务。

    HR / admin 放行（它们本来就有 train:edit 且需要代管）；
    其余角色必须 `plan.candidate_id == 自己的 parsed_resume.id`，否则 403。
    """
    from app.core.deps import has_perm

    if has_perm(user, "resume", "view") and user.scope_of("resume") == "all":
        return  # admin
    if "hr" in (user.roles or []):
        return  # HR 代管
    plan = db.get(PrejobPlan, task.plan_id)
    if plan is None:
        raise ApiError(404, "培养计划不存在")
    cid = my_candidate_id(db, user)
    if cid is None or int(plan.candidate_id or 0) != int(cid):
        raise ApiError(403, "无权操作该任务")
