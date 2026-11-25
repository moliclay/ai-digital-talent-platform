"""匹配服务：一次匹配 = 一个事务内重建该岗位的全部结果（幂等）。

历史可复现：结果里带权重与阈值快照，改权重只影响下一次匹配。
"""
from __future__ import annotations

from typing import Iterable

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope, max_scope
from app.core.response import ApiError
from app.models.orm import (
    TalentProfile,
    JobProfile, MatchList, MatchResult, ParsedResume, ResumeFile,
)
from app.services.matcher_service import evaluate


def _job_dict(job: JobProfile) -> dict:
    return {
        "id": job.id,
        "name": job.name,
        "prompt": job.prompt,
        "conditions": job.conditions or [],
        "score_rules": job.score_rules or {},
        "passing_threshold": job.passing_threshold,
        "ability_requirements": job.ability_requirements or {},
    }


def run(db: Session, user: CurrentUser, job_id: int, resume_ids: Iterable[int] | None = None) -> dict:
    job = db.get(JobProfile, job_id)
    if job is None or job.status == "deleted":
        raise ApiError(404, "岗位条件不存在")

    query = (
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    )
    if max_scope(user, "resume", "match") != "all":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))
    if resume_ids:
        ids = list(resume_ids)
        if not ids:
            raise ApiError(400, "resume_ids 不能为空数组")
        query = query.where(ParsedResume.id.in_(ids))

    rows = db.execute(query.order_by(ParsedResume.id)).all()
    if not rows:
        raise ApiError(400, "没有可匹配的简历，请先上传并解析")

    job_dict = _job_dict(job)

    # 岗位设了能力基线时，需要候选人画像；没画像的按"未生成画像"处理（该维度不计分，退回档案完整度）
    profiles: dict[int, dict] = {}
    if job_dict.get("ability_requirements"):
        ids = [parsed.id for parsed, _f in rows]
        for prof in db.execute(select(TalentProfile).where(TalentProfile.candidate_id.in_(ids))).scalars():
            if prof.status != "deleted":
                profiles[prof.candidate_id] = prof.abilities or {}

    started = func.now()

    # 幂等：同一岗位的历史结果整批替换，避免重复行与新旧混杂
    db.execute(delete(MatchResult).where(MatchResult.job_profile_id == job_id))
    db.execute(delete(MatchList).where(MatchList.job_profile_id == job_id))

    passed = failed = 0
    results = []
    for parsed, file in rows:
        verdict = evaluate(job_dict, {
            "name": parsed.name,
            "education": parsed.education,
            "years_experience": parsed.years_experience,
            "skills": parsed.skills or [],
            "resume_content": parsed.resume_content or "",
            "phone": parsed.phone,
            "email": parsed.email,
            "major": parsed.major,
        }, abilities=profiles.get(parsed.id))
        if verdict.passed:
            passed += 1
        else:
            failed += 1

        db.add(MatchResult(
            parsed_resume_id=parsed.id,
            job_profile_id=job_id,
            condition_detail=verdict.detail,
            total_score=verdict.total_score,
            passed=verdict.passed,
        ))
        db.add(MatchList(
            resume_file_id=file.id,
            parsed_resume_id=parsed.id,
            job_profile_id=job_id,
            job_profile_name=job.name,
            attachment_url=file.attachment_url,
            photo_url=parsed.photo_url,
            name=parsed.name,
            phone=parsed.phone,
            email=parsed.email,
            gender=parsed.gender,
            age=parsed.age,
            education=parsed.education,
            major=parsed.major,
            skills=parsed.skills or [],
            years_experience=parsed.years_experience,
            strengths=parsed.strengths or "",
            total_score=verdict.total_score,
            passing_threshold=job.passing_threshold,
            passed=verdict.passed,
            reason=verdict.reason,
            candidate_id=None,
        ))
        results.append({
            "parsed_resume_id": parsed.id,
            "name": parsed.name,
            "total_score": verdict.total_score,
            "passed": verdict.passed,
        })

    db.commit()

    return {
        "job_profile_id": job_id,
        "job_profile_name": job.name,
        "scanned": len(rows),
        "passed": passed,
        "failed": failed,
        "threshold": job.passing_threshold,
        "weights": job_dict["score_rules"].get("weights") if isinstance(job_dict["score_rules"], dict) else None,
        "started_at": str(started),
        "items": results,
    }


def summary(db: Session, job_id: int) -> dict:
    rows = db.execute(
        select(MatchList.total_score).where(MatchList.job_profile_id == job_id)
    ).scalars().all()
    if not rows:
        return {"job_profile_id": job_id, "total": 0, "passed": 0, "failed": 0,
                "avg_score": 0.0, "max_score": 0, "min_score": 0}
    scores = [int(s) for s in rows]
    passed = db.execute(
        select(func.count()).select_from(MatchList).where(
            MatchList.job_profile_id == job_id, MatchList.passed.is_(True)
        )
    ).scalar_one()
    return {
        "job_profile_id": job_id,
        "total": len(scores),
        "passed": int(passed),
        "failed": len(scores) - int(passed),
        "avg_score": round(sum(scores) / len(scores), 1),
        "max_score": max(scores),
        "min_score": min(scores),
    }


def lists(db: Session, user: CurrentUser, job_id: int | None, passed: bool | None,
          keyword: str, page: int, page_size: int) -> tuple[list[dict], int]:
    query = (
        select(MatchList, ResumeFile)
        .join(ResumeFile, ResumeFile.id == MatchList.resume_file_id)
    )
    if max_scope(user, "resume", "match") != "all":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))
    if job_id:
        query = query.where(MatchList.job_profile_id == job_id)
    if passed is not None:
        query = query.where(MatchList.passed.is_(passed))
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.where((MatchList.name.like(like)) | (MatchList.skills.cast(__import__("sqlalchemy").String).like(like)))

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(MatchList.total_score.desc(), MatchList.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).all()

    parsed_ids = [m.parsed_resume_id for m, _f in rows]
    detail_map: dict[int, MatchResult] = {}
    if parsed_ids and job_id:
        for d in db.execute(
            select(MatchResult).where(
                MatchResult.parsed_resume_id.in_(parsed_ids),
                MatchResult.job_profile_id == job_id,
            )
        ).scalars():
            detail_map[d.parsed_resume_id] = d

    items = []
    for m, f in rows:
        snap = detail_map.get(m.parsed_resume_id)
        snapshot = snap.condition_detail if snap and isinstance(snap.condition_detail, dict) else {}
        checks = snapshot.get("conditions") or []
        hit = snapshot.get("hit_skills") or []
        req = snapshot.get("required_skills") or []
        items.append({
            "id": m.id,
            "parsed_resume_id": m.parsed_resume_id,
            "job_profile_id": m.job_profile_id,
            "job_profile_name": m.job_profile_name,
            "name": m.name,
            "education": m.education,
            "major": m.major,
            "skills": m.skills or [],
            "years_experience": m.years_experience,
            "total_score": m.total_score,
            "passing_threshold": m.passing_threshold,
            "passed": m.passed,
            "reason": m.reason,
            "filename": f.filename if f else "",
            "checks": [
                {"key": c.get("key"), "ok": bool(c.get("ok"))}
                for c in checks if isinstance(c, dict)
            ],
            "skill_hit": len(hit),
            "skill_required": len(req),
        })
    return items, int(total)


def detail(db: Session, user: CurrentUser, match_id: int) -> dict:
    row = db.execute(
        select(MatchList, ResumeFile)
        .join(ResumeFile, ResumeFile.id == MatchList.resume_file_id)
        .where(MatchList.id == match_id)
    ).first()
    if row is None:
        raise ApiError(404, "匹配记录不存在")
    m, f = row
    scope = max_scope(user, "resume", "match")
    if scope != "all":
        if scope == "dept" and f.dept_id != user.department_id:
            raise ApiError(403, "无权访问该匹配记录")
        if scope == "self" and f.created_by != user.id:
            raise ApiError(403, "无权访问该匹配记录")

    result = db.execute(
        select(MatchResult).where(
            MatchResult.parsed_resume_id == m.parsed_resume_id,
            MatchResult.job_profile_id == m.job_profile_id,
        ).order_by(MatchResult.id.desc())
    ).scalars().first()

    parsed = db.get(ParsedResume, m.parsed_resume_id)
    detail = result.condition_detail if result else {}
    if isinstance(detail, list):  # 兼容 seed 里的旧格式
        detail = {"conditions": detail, "dimensions": [], "weights": {}, "threshold": m.passing_threshold}

    return {
        "id": m.id,
        "name": m.name,
        "phone": m.phone,
        "email": m.email,
        "education": m.education,
        "major": m.major,
        "skills": m.skills or [],
        "years_experience": m.years_experience,
        "strengths": m.strengths,
        "total_score": m.total_score,
        "passing_threshold": m.passing_threshold,
        "passed": m.passed,
        "reason": m.reason,
        "job_profile_name": m.job_profile_name,
        "filename": f.filename if f else "",
        "attachment_url": m.attachment_url,
        "resume_content": parsed.resume_content if parsed else "",
        "manually_fixed": bool(parsed.manually_fixed) if parsed else False,
        "detail": detail,
    }
