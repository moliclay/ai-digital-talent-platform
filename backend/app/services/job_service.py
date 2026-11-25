"""岗位条件服务。岗位条件是全公司共享的配置，不按部门隔离；写操作由权限码控制。"""
from __future__ import annotations

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope, max_scope
from app.core.response import ApiError
from app.models.orm import (
    JobProfile, MatchList, MatchResult, ParsedResume, Position,
    ResumeFile, TalentProfile,
)
from app.services.matcher_service import DEFAULT_WEIGHTS, required_skills

ALLOWED_OPS = {">=", ">", "<=", "<", "==", "contains", "in"}
CONDITION_KEYS = {"学历", "技能", "工作年限", "专业", "城市"}


def _serialize(job: JobProfile) -> dict:
    return {
        "id": job.id,
        "name": job.name,
        "prompt": job.prompt,
        "conditions": job.conditions or [],
        "score_rules": job.score_rules or {},
        "ability_requirements": job.ability_requirements or {},
        "headcount": job.headcount,
        "passing_threshold": job.passing_threshold,
        "status": job.status,
        "required_skills": required_skills({"name": job.name, "conditions": job.conditions}),
        "created_at": job.created_at.isoformat(sep=" ", timespec="seconds") if job.created_at else "",
    }


def list_jobs(db: Session, keyword: str, page: int, page_size: int) -> tuple[list[dict], int]:
    query = select(JobProfile).where(JobProfile.status != "deleted")
    if keyword:
        query = query.where(JobProfile.name.like(f"%{keyword.strip()}%"))
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(JobProfile.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).scalars().all()
    return [_serialize(j) for j in rows], int(total)


def get_job(db: Session, job_id: int) -> JobProfile:
    job = db.get(JobProfile, job_id)
    if job is None or job.status == "deleted":
        raise ApiError(404, "岗位条件不存在")
    return job


def _validate(payload: dict) -> None:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ApiError(400, "岗位名称不能为空")

    conditions = payload.get("conditions") or []
    if not isinstance(conditions, list):
        raise ApiError(400, "conditions 必须是数组")
    for cond in conditions:
        if not isinstance(cond, dict):
            raise ApiError(400, "条件格式错误")
        key = str(cond.get("key") or "").strip()
        op = str(cond.get("op") or "").strip()
        if key not in CONDITION_KEYS:
            raise ApiError(400, f"不支持的条件字段：{key}")
        if op not in ALLOWED_OPS:
            raise ApiError(400, f"不支持的比较符：{op}")
        if cond.get("value") in (None, "", []):
            raise ApiError(400, f"条件「{key}」缺少取值")

    threshold = payload.get("passing_threshold", 70)
    try:
        threshold = int(threshold)
    except (TypeError, ValueError):
        raise ApiError(400, "合格线必须是整数")
    if not 0 <= threshold <= 100:
        raise ApiError(400, "合格线必须在 0–100 之间")

    weights = (payload.get("score_rules") or {}).get("weights") if isinstance(payload.get("score_rules"), dict) else None
    if weights:
        if not isinstance(weights, dict):
            raise ApiError(400, "weights 必须是对象")
        for k, v in weights.items():
            try:
                if float(v) < 0:
                    raise ValueError
            except (TypeError, ValueError):
                raise ApiError(400, f"权重 {k} 必须是非负数")


def create_job(db: Session, payload: dict) -> dict:
    _validate(payload)
    job = JobProfile(
        name=str(payload["name"]).strip(),
        prompt=str(payload.get("prompt") or ""),
        conditions=payload.get("conditions") or [],
        score_rules=payload.get("score_rules") or {"weights": DEFAULT_WEIGHTS},
        ability_requirements=_clean_abilities(payload.get("ability_requirements")),
        headcount=int(payload.get("headcount") or 1),
        passing_threshold=int(payload.get("passing_threshold", 70)),
        status="active",
    )
    db.add(job)
    _ensure_position(db, job.name)
    db.commit()
    return _serialize(job)


def update_job(db: Session, job_id: int, payload: dict) -> dict:
    job = get_job(db, job_id)
    _validate({**payload, "name": payload.get("name", job.name)})
    job.name = str(payload.get("name", job.name)).strip()
    if "prompt" in payload:
        job.prompt = str(payload.get("prompt") or "")
    if "conditions" in payload:
        job.conditions = payload["conditions"]
    if "score_rules" in payload:
        job.score_rules = payload["score_rules"] or {"weights": DEFAULT_WEIGHTS}
    if "ability_requirements" in payload:
        job.ability_requirements = _clean_abilities(payload.get("ability_requirements"))
    if "headcount" in payload:
        job.headcount = max(1, int(payload.get("headcount") or 1))
    if "passing_threshold" in payload:
        job.passing_threshold = int(payload["passing_threshold"])
    db.commit()
    return _serialize(job)


def delete_job(db: Session, job_id: int) -> None:
    job = get_job(db, job_id)
    job.status = "deleted"
    db.commit()


def _ensure_position(db: Session, name: str) -> None:
    base = name.split("(")[0].strip()
    exists = db.execute(select(Position).where(Position.name == base)).scalar_one_or_none()
    if exists is None and base:
        db.add(Position(name=base))


def list_positions(db: Session) -> list[dict]:
    return [{"id": p.id, "name": p.name} for p in db.execute(select(Position).order_by(Position.id)).scalars()]


def match_summary(db: Session, job_id: int) -> dict:
    rows = db.execute(
        select(MatchList.passed, func.count(), func.avg(MatchList.total_score), func.max(MatchList.total_score))
        .where(MatchList.job_profile_id == job_id)
        .group_by(MatchList.passed)
    ).all()
    passed = sum(int(c) for p, c, *_ in rows if p)
    failed = sum(int(c) for p, c, *_ in rows if not p)
    return {
        "job_profile_id": job_id,
        "passed": passed,
        "failed": failed,
        "avg_score": round(float(rows[0][2] or 0), 1) if rows else 0.0,
        "max_score": int(rows[0][3] or 0) if rows else 0,
    }


def _clean_abilities(raw) -> dict:
    """能力基线：只保留 0-100 的数值维度，0 表示该维不计。"""
    if not isinstance(raw, dict):
        return {}
    out: dict[str, float] = {}
    for k, v in raw.items():
        try:
            f = float(v)
        except (TypeError, ValueError):
            continue
        if 0 < f <= 100:
            out[str(k)] = round(f, 1)
    return out


def dry_run(db: Session, user, job_id: int) -> dict:
    """用当前条件对可见简历试算，不落库——回答"这套条件会不会太严/太松"。"""
    from app.core.deps import apply_scope
    from app.models.orm import ParsedResume, ResumeFile
    from app.services.matcher_service import evaluate

    job = get_job(db, job_id)
    query = (
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    )
    if user.scope_of("resume") != "all":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user)

    rows = db.execute(query).all()
    job_dict = {
        "name": job.name,
        "prompt": job.prompt,
        "conditions": job.conditions or [],
        "score_rules": job.score_rules or {},
        "passing_threshold": job.passing_threshold,
        "ability_requirements": job.ability_requirements or {},
    }

    profiles: dict[int, dict] = {}
    if job_dict.get("ability_requirements"):
        from app.models.orm import TalentProfile
        ids = [p_.id for p_, _f in rows]
        for prof in db.execute(select(TalentProfile).where(TalentProfile.candidate_id.in_(ids))).scalars():
            if prof.status != "deleted":
                profiles[prof.candidate_id] = prof.abilities or {}

    scored = []
    for parsed, _file in rows:
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
        scored.append({"name": parsed.name, "score": verdict.total_score, "passed": verdict.passed})

    buckets = [{"label": "0–59", "count": 0}, {"label": "60–69", "count": 0},
               {"label": "70–79", "count": 0}, {"label": "80–89", "count": 0},
               {"label": "90–100", "count": 0}]
    for item in scored:
        s = item["score"]
        idx = 0 if s < 60 else 1 if s < 70 else 2 if s < 80 else 3 if s < 90 else 4
        buckets[idx]["count"] += 1

    scored.sort(key=lambda x: -x["score"])
    return {
        "job_profile_id": job_id,
        "job_profile_name": job.name,
        "threshold": job.passing_threshold,
        "scanned": len(scored),
        "passed": sum(1 for x in scored if x["passed"]),
        "failed": sum(1 for x in scored if not x["passed"]),
        "avg_score": round(sum(x["score"] for x in scored) / len(scored), 1) if scored else 0.0,
        "buckets": buckets,
        "top": scored[:5],
    }


# ---------------------------------------------------------------- 空缺预警 / 储备推荐
RESERVE_MARGIN = 15  # 距合格线 N 分以内的未过者，视为储备


def _alert_level(passed: int, headcount: int) -> str:
    if passed >= max(1, headcount):
        return "none"
    if headcount > 1 and passed == headcount - 1:
        return "low"
    if passed >= 1:
        return "medium"
    return "high"


def vacancy_alerts(db: Session, user: CurrentUser) -> list[dict]:
    """按岗位统计（用户可见范围内）通过人数 vs 名额，给空缺预警。"""
    jobs = db.execute(select(JobProfile).where(JobProfile.status == "active")).scalars().all()
    if not jobs:
        return []
    job_ids = [j.id for j in jobs]

    query = (
        select(
            MatchList.job_profile_id,
            func.count().label("matched"),
            func.sum(case((MatchList.passed.is_(True), 1), else_=0)).label("passed"),
        )
        .join(ResumeFile, ResumeFile.id == MatchList.resume_file_id)
        .where(MatchList.job_profile_id.in_(job_ids))
        .group_by(MatchList.job_profile_id)
    )
    if max_scope(user, "resume", "match") != "all":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))

    stat: dict[int, tuple[int, int]] = {}
    for job_id, matched, passed in db.execute(query).all():
        stat[job_id] = (int(matched), int(passed or 0))

    alerts = []
    for job in jobs:
        matched, passed = stat.get(job.id, (0, 0))
        headcount = max(1, job.headcount)
        alerts.append({
            "job_profile_id": job.id,
            "job_name": job.name,
            "headcount": headcount,
            "matched": matched,
            "passed": passed,
            "vacancy": max(0, headcount - passed),
            "pass_rate": round(passed / matched * 100, 1) if matched else 0.0,
            "alert": _alert_level(passed, headcount),
            "threshold": job.passing_threshold,
        })
    # 预警优先：high → medium → low → none
    order = {"high": 0, "medium": 1, "low": 2, "none": 3}
    alerts.sort(key=lambda a: order.get(a["alert"], 9))
    return alerts


def reserve_pool(db: Session, user: CurrentUser, job_id: int) -> dict:
    """储备推荐 = 接近合格线但未过的 + 画像达标但未投递该岗位的。"""
    job = get_job(db, job_id)
    threshold = job.passing_threshold

    # 1) 接近合格线的未过者
    near_query = (
        select(MatchList, ResumeFile)
        .join(ResumeFile, ResumeFile.id == MatchList.resume_file_id)
        .where(
            MatchList.job_profile_id == job_id,
            MatchList.passed.is_(False),
            MatchList.total_score >= threshold - RESERVE_MARGIN,
        )
    )
    if max_scope(user, "resume", "match") != "all":
        near_query = apply_scope(near_query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))

    parsed_ids = []
    near = []
    for m, _f in db.execute(near_query.order_by(MatchList.total_score.desc())).all():
        parsed_ids.append(m.parsed_resume_id)
        snap = db.execute(
            select(MatchResult).where(
                MatchResult.parsed_resume_id == m.parsed_resume_id,
                MatchResult.job_profile_id == job_id,
            )
        ).scalar_one_or_none()
        detail = snap.condition_detail if snap and isinstance(snap.condition_detail, dict) else {}
        near.append({
            "parsed_resume_id": m.parsed_resume_id,
            "name": m.name,
            "total_score": m.total_score,
            "threshold": threshold,
            "gap": threshold - m.total_score,
            "hard_failed": detail.get("hard_failed", False),
            "fail_items": detail.get("fail_items") or [],
            "missing_skills": detail.get("missing_skills") or [],
            "reason": m.reason,
        })

    # 2) 画像达标但未投递该岗位（能力基线全维达标）
    baseline = job.ability_requirements or {}
    qualified = []
    if baseline:
        matched_ids = set(db.execute(
            select(MatchList.parsed_resume_id).where(MatchList.job_profile_id == job_id)
        ).scalars())
        prof_query = (
            select(TalentProfile, ResumeFile)
            .join(ParsedResume, ParsedResume.id == TalentProfile.candidate_id)
            .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
            .where(TalentProfile.status == "active")
        )
        if matched_ids:
            prof_query = prof_query.where(TalentProfile.candidate_id.notin_(matched_ids))
        if max_scope(user, "resume", "match") != "all":
            prof_query = apply_scope(prof_query, ResumeFile.dept_id, ResumeFile.created_by, user, ("resume", "match"))
        for prof, _f in db.execute(prof_query).all():
            abilities = prof.abilities if isinstance(prof.abilities, dict) else {}
            if all(abilities.get(dim, 0) >= int(base) for dim, base in baseline.items()):
                qualified.append({
                    "parsed_resume_id": prof.candidate_id,
                    "name": prof.candidate_name,
                    "abilities": {d: abilities.get(d) for d in baseline},
                })

    return {
        "job_profile_id": job_id,
        "job_name": job.name,
        "threshold": threshold,
        "margin": RESERVE_MARGIN,
        "near_miss": near,
        "qualified_pool": qualified,
    }
