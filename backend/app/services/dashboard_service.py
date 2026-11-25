"""工作台：只回答一个问题——现在有多少简历卡住、匹配通过率多少。故意不做图表。"""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope, max_scope
from app.models.orm import (
    JobProfile, MatchList, ParseTask, ParsedResume, ResumeFile, SysOperationLog,
)


def overview(db: Session, user: CurrentUser) -> dict:
    file_query = apply_scope(select(ResumeFile), ResumeFile.dept_id, ResumeFile.created_by, user)
    files_sub = file_query.subquery()

    total_files = db.execute(select(func.count()).select_from(files_sub)).scalar_one()

    status_rows = db.execute(
        select(files_sub.c.status, func.count()).group_by(files_sub.c.status)
    ).all()
    by_status = {s: int(c) for s, c in status_rows}

    parsed_query = (
        select(func.count())
        .select_from(ParsedResume)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
    )
    if max_scope(user, "resume", "match") != "all":
        parsed_query = apply_scope(parsed_query, ResumeFile.dept_id, ResumeFile.created_by, user)
    parsed_total = db.execute(parsed_query).scalar_one()

    latest_job = db.execute(
        select(JobProfile).where(JobProfile.status == "active").order_by(JobProfile.id.desc()).limit(1)
    ).scalar_one_or_none()

    match_stats = {"job_profile_id": None, "job_profile_name": "", "passed": 0, "failed": 0, "avg_score": 0.0}
    if latest_job:
        rows = db.execute(
            select(MatchList.passed, func.count(), func.avg(MatchList.total_score))
            .where(MatchList.job_profile_id == latest_job.id)
            .group_by(MatchList.passed)
        ).all()
        passed = sum(int(c) for p, c, _ in rows if p)
        failed = sum(int(c) for p, c, _ in rows if not p)
        avg = 0.0
        if rows:
            total_cnt = sum(int(c) for _, c, _ in rows)
            avg = round(sum(float(a or 0) * int(c) for _, c, a in rows) / total_cnt, 1) if total_cnt else 0.0
        match_stats = {
            "job_profile_id": latest_job.id,
            "job_profile_name": latest_job.name,
            "passed": passed,
            "failed": failed,
            "avg_score": avg,
        }

    active_jobs = db.execute(
        select(func.count()).select_from(JobProfile).where(JobProfile.status == "active")
    ).scalar_one()

    queue_rows = db.execute(
        select(ParseTask.status, func.count())
        .join(ResumeFile, ResumeFile.id == ParseTask.resume_id)
        .group_by(ParseTask.status)
    ).all()
    queue = {s: int(c) for s, c in queue_rows}

    recent = db.execute(
        select(SysOperationLog).order_by(SysOperationLog.id.desc()).limit(8)
    ).scalars().all()

    return {
        "files": {"total": int(total_files), "by_status": by_status},
        "parsed_total": int(parsed_total),
        "queue": queue,
        "active_jobs": int(active_jobs),
        "match": match_stats,
        "recent_operations": [
            {
                "id": r.id,
                "username": r.username,
                "module": r.module,
                "action": r.action,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
            }
            for r in recent
        ],
    }
