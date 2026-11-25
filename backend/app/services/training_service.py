"""培训成长模块（MVP-2，规则实现，不接 AI）。

闭环：能力缺口诊断 → 千人千面计划 → 课程学习（学时监控/防挂机）→ 课后考核
      → 通过则更新画像能力并写入成长台账；不通过则复用测评域的错题/复习计划。

设计约定：
- candidate_id 与人才画像一致，指向 parsed_resumes.id；
- 课程按 category 映射到画像五维；没有映射的课程不进诊断推荐，但不影响课程 CRUD；
- 培养计划幂等：同一「候选人 × 岗位」重复生成会作废旧计划，保留新计划；
- 防挂机：任务完成必须满足「学时达标」且「进度 100」，否则 400 拒绝。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, max_scope
from app.core.response import ApiError
from app.models.orm import (
    ExamSubmission,
    GrowthLedger,
    JobProfile,
    PrejobPlan,
    PrejobPlanTask,
    TalentProfile,
    TrainingCourse,
)
from app.services import my_training_service

DIMENSIONS = ["技术深度", "工程能力", "业务理解", "协作沟通", "成长性"]
DEFAULT_TARGET = 70
MIN_REQUIRED_MINUTES = 15

# 课程分类 → 画像维度（与测评反哺用同一套映射，保证两条线口径一致）
COURSE_DIM_RULES: list[tuple[tuple[str, ...], str]] = [
    (("算法", "模型", "ai", "机器学习", "深度学习", "大模型", "框架", "数据", "python", "nlp", "向量"), "技术深度"),
    (("工程", "架构", "部署", "运维", "测试", "后端", "性能", "容器", "数据库"), "工程能力"),
    (("产品", "业务", "需求", "行业", "分析", "指标", "商业"), "业务理解"),
    (("沟通", "协作", "团队", "管理", "项目", "领导"), "协作沟通"),
    (("成长", "职业", "复盘", "学习", "规划", "效能"), "成长性"),
]


def _course_dimension(course: TrainingCourse) -> str | None:
    text = f"{course.category} {course.name}".lower()
    for words, dim in COURSE_DIM_RULES:
        if any(w in text for w in words):
            return dim
    return None


def _severity(gap: int) -> str:
    if gap <= 0:
        return "none"
    if gap >= 20:
        return "high"
    if gap >= 10:
        return "medium"
    return "low"


def _job_targets(job: JobProfile | None) -> dict[str, int]:
    req = (job.ability_requirements or {}) if job is not None else {}
    return {d: int(req.get(d, DEFAULT_TARGET)) for d in DIMENSIONS}


def _serialize_course(c: TrainingCourse) -> dict:
    return {
        "id": c.id, "name": c.name, "description": c.description, "category": c.category,
        "duration_hours": c.duration_hours, "difficulty": c.difficulty, "instructor": c.instructor,
        "content": c.content, "exam_id": c.exam_id, "status": c.status,
    }


# ---------------------------------------------------------------- 课程目录
def list_courses(db: Session, keyword: str, page: int, page_size: int) -> tuple[list[dict], int]:
    query = select(TrainingCourse).where(TrainingCourse.status == "active")
    if keyword:
        query = query.where(TrainingCourse.name.contains(keyword))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(query.order_by(TrainingCourse.id).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return [_serialize_course(c) for c in rows], total


def create_course(db: Session, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ApiError(400, "课程名称不能为空")
    course = TrainingCourse(
        name=name,
        description=str(payload.get("description") or ""),
        category=str(payload.get("category") or ""),
        duration_hours=int(payload.get("duration_hours") or 2),
        difficulty=str(payload.get("difficulty") or "medium"),
        instructor=str(payload.get("instructor") or ""),
        content=str(payload.get("content") or ""),
        exam_id=int(payload["exam_id"]) if payload.get("exam_id") else None,
    )
    db.add(course)
    db.commit()
    return _serialize_course(course)


def update_course(db: Session, course_id: int, payload: dict) -> dict:
    course = db.get(TrainingCourse, course_id)
    if course is None or course.status == "deleted":
        raise ApiError(404, "课程不存在")
    for field in ("name", "description", "category", "instructor", "content", "difficulty"):
        if field in payload:
            setattr(course, field, str(payload[field] or ""))
    if "duration_hours" in payload:
        course.duration_hours = int(payload["duration_hours"] or 2)
    if "exam_id" in payload:
        course.exam_id = int(payload["exam_id"]) if payload.get("exam_id") else None
    db.commit()
    return _serialize_course(course)


def delete_course(db: Session, course_id: int) -> None:
    course = db.get(TrainingCourse, course_id)
    if course is None:
        raise ApiError(404, "课程不存在")
    course.status = "deleted"
    db.commit()


# ---------------------------------------------------------------- 缺口诊断
def diagnose(db: Session, candidate_id: int, job_id: int) -> dict:
    profile = db.execute(
        select(TalentProfile).where(TalentProfile.candidate_id == candidate_id)
    ).scalar_one_or_none()
    if profile is None:
        raise ApiError(404, "候选人还没有画像，先去「人才画像」生成")
    job = db.get(JobProfile, job_id) if job_id else None
    abilities = profile.abilities if isinstance(profile.abilities, dict) else {}
    targets = _job_targets(job)

    courses = db.execute(
        select(TrainingCourse).where(TrainingCourse.status == "active")
    ).scalars().all()
    by_dim: dict[str, list[dict]] = {}
    for c in courses:
        dim = _course_dimension(c)
        if dim:
            by_dim.setdefault(dim, []).append(_serialize_course(c))

    gaps: list[dict] = []
    for dim in DIMENSIONS:
        current = int(abilities.get(dim, 0) or 0)
        target = targets.get(dim, DEFAULT_TARGET)
        gap = max(0, target - current)
        rec = by_dim.get(dim, [])
        rec.sort(key=lambda c: (c["difficulty"] == "hard", c["id"]))
        gaps.append({
            "dimension": dim, "current": current, "target": target, "gap": gap,
            "severity": _severity(gap),
            "recommended_courses": rec,
        })
    gaps.sort(key=lambda g: -g["gap"])
    return {
        "candidate_id": candidate_id,
        "candidate_name": profile.candidate_name,
        "job_id": job_id,
        "position_name": job.name if job else "",
        "targets": targets,
        "gaps": gaps,
    }


# ---------------------------------------------------------------- 培养计划
def _build_phases(gaps: list[dict], weeks: int, mentor: str) -> list[dict]:
    """周 1 固定为入职适应；其余周按缺口从大到小分配，每缺口一阶段。"""
    phases: list[dict] = [{"week": 1, "goal": "入职适应与环境熟悉", "dimension": "", "courses": []}]
    real = [g for g in gaps if g["gap"] > 0]
    if not real:
        real = gaps  # 无缺口时，也按最弱维度铺一版，保证计划可用
    for i, g in enumerate(real):
        week = i + 2
        if week > weeks:
            break
        phases.append({
            "week": week,
            "goal": f"补齐「{g['dimension']}」（当前 {g['current']}，目标 {g['target']}）",
            "dimension": g["dimension"],
            "courses": [c["id"] for c in g["recommended_courses"][:2]],
        })
    return phases


def generate_plan(db: Session, user: CurrentUser, candidate_id: int, job_id: int,
                  weeks: int = 4, mentor: str = "") -> dict:
    diag = diagnose(db, candidate_id, job_id)
    profile = db.execute(
        select(TalentProfile).where(TalentProfile.candidate_id == candidate_id)
    ).scalar_one()
    course_map = {c.id: c for c in db.execute(
        select(TrainingCourse).where(TrainingCourse.status == "active")
    ).scalars().all()}

    weeks = max(1, min(int(weeks), 12))
    phases = _build_phases(diag["gaps"], weeks, mentor)
    course_ids: list[int] = []
    for p in phases:
        course_ids.extend(p["courses"])

    # 幂等：作废该候选人同岗位的旧计划
    db.execute(update(PrejobPlan).where(
        PrejobPlan.candidate_id == candidate_id,
        PrejobPlan.position_name == diag["position_name"],
        PrejobPlan.status == "generated",
    ).values(status="superseded"))

    plan = PrejobPlan(
        candidate_id=candidate_id,
        candidate_name=profile.candidate_name,
        position_name=diag["position_name"],
        plan_title=f"{profile.candidate_name}·{diag['position_name'] or '通用'}培养方案",
        goal="；".join(f"{g['dimension']} {g['current']}→{g['target']}" for g in diag["gaps"] if g["gap"] > 0) or "各维已达标，做巩固",
        total_weeks=weeks,
        phases=[{k: v for k, v in p.items() if k != "courses"} for p in phases],
        course_ids=course_ids,
        mentor=mentor or profile.recommendation[:20] or "待指定",
        status="generated",
    )
    db.add(plan)
    db.flush()

    gap_by_dim = {g["dimension"]: g for g in diag["gaps"]}
    for p in phases:
        for cid in p["courses"]:
            course = course_map.get(cid)
            if course is None:
                continue
            g = gap_by_dim.get(p["dimension"], {})
            db.add(PrejobPlanTask(
                plan_id=plan.id,
                phase_index=p["week"],
                title=f"学习《{course.name}》",
                dimension=p["dimension"],
                course_id=course.id,
                exam_id=course.exam_id,
                required_minutes=max(MIN_REQUIRED_MINUTES, course.duration_hours * 60),
                status="pending",
                detail={"goal": p["goal"], "target": g.get("target", DEFAULT_TARGET), "current": g.get("current", 0)},
            ))
    db.commit()
    return get_plan(db, plan.id)


def _serialize_task(t: PrejobPlanTask) -> dict:
    return {
        "id": t.id, "phase_index": t.phase_index, "title": t.title, "dimension": t.dimension,
        "course_id": t.course_id, "exam_id": t.exam_id,
        "required_minutes": t.required_minutes, "study_minutes": t.study_minutes,
        "progress": t.progress, "status": t.status, "detail": t.detail or {},
        "last_active_at": t.last_active_at.isoformat(sep=" ", timespec="seconds") if t.last_active_at else "",
    }


def list_plans(db: Session, candidate_id: int | None, page: int, page_size: int) -> tuple[list[dict], int]:
    query = select(PrejobPlan).where(PrejobPlan.status == "generated")
    if candidate_id:
        query = query.where(PrejobPlan.candidate_id == candidate_id)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(query.order_by(PrejobPlan.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = []
    for p in rows:
        tasks = db.execute(
            select(PrejobPlanTask).where(PrejobPlanTask.plan_id == p.id).order_by(PrejobPlanTask.phase_index, PrejobPlanTask.id)
        ).scalars().all()
        done = sum(1 for t in tasks if t.status == "done")
        items.append({
            "id": p.id, "candidate_id": p.candidate_id, "candidate_name": p.candidate_name,
            "position_name": p.position_name, "plan_title": p.plan_title, "goal": p.goal,
            "total_weeks": p.total_weeks, "mentor": p.mentor, "status": p.status,
            "course_ids": p.course_ids or [],
            "task_total": len(tasks), "task_done": done,
            "progress": round(100 * done / len(tasks)) if tasks else 0,
        })
    return items, total


def get_plan(db: Session, plan_id: int) -> dict:
    plan = db.get(PrejobPlan, plan_id)
    if plan is None:
        raise ApiError(404, "培养计划不存在")
    tasks = db.execute(
        select(PrejobPlanTask).where(PrejobPlanTask.plan_id == plan_id).order_by(PrejobPlanTask.phase_index, PrejobPlanTask.id)
    ).scalars().all()
    return {
        "id": plan.id, "candidate_id": plan.candidate_id, "candidate_name": plan.candidate_name,
        "position_name": plan.position_name, "plan_title": plan.plan_title, "goal": plan.goal,
        "total_weeks": plan.total_weeks, "phases": plan.phases or [], "course_ids": plan.course_ids or [],
        "mentor": plan.mentor, "status": plan.status,
        "tasks": [_serialize_task(t) for t in tasks],
    }


# ---------------------------------------------------------------- 学习进度 / 防挂机
def progress_task(db: Session, task_id: int, minutes: int, progress: int) -> dict:
    task = db.get(PrejobPlanTask, task_id)
    if task is None:
        raise ApiError(404, "学习任务不存在")
    minutes = max(0, int(minutes))
    progress = max(0, min(100, int(progress)))
    task.study_minutes += minutes
    task.progress = max(task.progress, progress)
    task.last_active_at = datetime.now()
    if task.status == "pending":
        task.status = "learning"
    db.commit()
    return _serialize_task(task)


def complete_task(db: Session, task_id: int) -> dict:
    """完成任务：进度必须 100，且学时达标（防挂机）。"""
    task = db.get(PrejobPlanTask, task_id)
    if task is None:
        raise ApiError(404, "学习任务不存在")
    if task.progress < 100:
        raise ApiError(400, f"进度 {task.progress}%，未到 100%，不能标记完成")
    if task.study_minutes < task.required_minutes:
        raise ApiError(400, f"学时不足：已学 {task.study_minutes} 分钟，要求 {task.required_minutes} 分钟（防挂机）")
    task.status = "done"
    db.commit()
    return _serialize_task(task)


# ---------------------------------------------------------------- 课后考核 → 台账 / 画像
def assess_task(db: Session, task_id: int, submission_id: int) -> dict:
    task = db.get(PrejobPlanTask, task_id)
    if task is None:
        raise ApiError(404, "学习任务不存在")
    sub = db.get(ExamSubmission, submission_id)
    if sub is None:
        raise ApiError(404, "测评提交不存在")
    plan = db.get(PrejobPlan, task.plan_id)
    if plan is None or sub.parsed_resume_id != plan.candidate_id:
        raise ApiError(400, "测评提交未明确关联该计划对象")
    if task.exam_id is None or sub.exam_id != task.exam_id:
        raise ApiError(400, "测评提交与课程考核试卷不一致")
    if task.status == "done":
        # 幂等：同一任务重复考核不重复加分/写台账
        return _serialize_task(task)

    if sub.result == "passed":
        task.status = "done"
        # 通过 → 成长台账 + 画像能力提升（只补缺口，不无脑加分）
        profile = db.execute(
            select(TalentProfile).where(TalentProfile.candidate_id == plan.candidate_id)
        ).scalar_one_or_none()
        if profile is not None and task.dimension:
            abilities = profile.abilities if isinstance(profile.abilities, dict) else {}
            before = int(abilities.get(task.dimension, 0) or 0)
            target = int((task.detail or {}).get("target", DEFAULT_TARGET))
            if before < target:
                after = min(100, before + max(8, round((target - before) * 0.5)))
                profile.abilities = {**abilities, task.dimension: after}
                db.add(GrowthLedger(
                    candidate_id=profile.candidate_id, candidate_name=profile.candidate_name,
                    dimension=task.dimension, before_score=before, after_score=after,
                    delta=after - before, source="prejob_assessment", ref_id=submission_id,
                    note=f"{task.dimension} 考核通过，{before}→{after}",
                ))
    else:
        task.status = "failed"
        # 不通过：落到测评域已有错题/复习计划，这里只改任务状态

    db.commit()
    return _serialize_task(task)


def ledger(db: Session, candidate_id: int, page: int, page_size: int) -> tuple[list[dict], int]:
    query = select(GrowthLedger).where(GrowthLedger.candidate_id == candidate_id)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(query.order_by(GrowthLedger.id.desc()).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    items = [{
        "id": r.id, "candidate_id": r.candidate_id, "candidate_name": r.candidate_name,
        "dimension": r.dimension, "before_score": r.before_score, "after_score": r.after_score,
        "delta": r.delta, "source": r.source, "ref_id": r.ref_id, "note": r.note,
        "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
    } for r in rows]
    return items, total


def assert_task_owner(db: Session, user: CurrentUser, task_id: int) -> None:
    """员工只能操作自己的任务（授了 train:edit(self) 之后必须校验归属）。"""
    task = db.get(PrejobPlanTask, int(task_id))
    if task is None:
        raise ApiError(404, "学习任务不存在")
    my_training_service.assert_task_owner(db, user, task)


def is_self_scoped(user: CurrentUser) -> bool:
    """该账号对培训数据是否只有 self 范围（员工就是这种）。"""
    return user.scope_of("train") != "all" and "hr" not in (user.roles or [])


def self_candidate_id(db: Session, user: CurrentUser) -> int | None:
    return my_training_service.my_candidate_id(db, user)


def assert_candidate_scope(db: Session, user: CurrentUser, candidate_id: int) -> None:
    """self 范围的账号只能查自己的候选人数据。"""
    if not is_self_scoped(user):
        return
    own = self_candidate_id(db, user)
    if own is None or int(candidate_id) != int(own):
        raise ApiError(403, "无权查看该候选人的培训数据")


def assert_plan_scope(db: Session, user: CurrentUser, plan_id: int) -> None:
    if not is_self_scoped(user):
        return
    plan = db.get(PrejobPlan, int(plan_id))
    if plan is None:
        raise ApiError(404, "培养计划不存在")
    assert_candidate_scope(db, user, int(plan.candidate_id or 0))
