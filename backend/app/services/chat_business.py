"""Fixed read-only HR query capabilities; model filters never become SQL text."""
from sqlalchemy import String, select, or_

from app.core.deps import apply_scope, has_perm
from app.core.response import ApiError
from app.models.orm import ParsedResume, ResumeFile, MatchResult, JobProfile, TalentProfile
from app.services import job_service, resume_service, talent_service, vector_service


FILTERS = {
    "search_talent": {"keyword", "education", "min_years", "name", "resume_id"},
    "semantic_search": {"query"},
    "match_explain": {"resume_id", "name", "job_id"},
    "talent_profile": {"resume_id", "name"},
    "vacancy": {"job_id"},
    "clarify": set(), "out_of_scope": set(),
}


def _require(user, *resources):
    if not all(has_perm(user, resource) for resource in resources):
        raise ApiError(403, "没有所需的业务查询权限")


def _resumes(user, resource="resume"):
    query = apply_scope(select(ParsedResume, ResumeFile).join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
                        .where(ParsedResume.is_current.is_(True), ResumeFile.status == "completed"),
                        ResumeFile.dept_id, ResumeFile.created_by, user, "resume")
    if resource != "resume":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, resource)
    return query


def _ref(kind, id_, label, path=None):
    return {"type": kind, "id": id_, "label": label, **({"path": path} if path else {})}


def _resume_ref(p):
    return _ref("resume", p.id, p.name, "/resumes")


def _scope_ref(user):
    return {"type": "scope", "id": user.id, "label": "当前授权范围", "department_id": user.department_id,
            "permissions": {k: v for k, v in user.perm_map.items() if k.endswith(":view")}}


def sources_allowed(db, user, refs):
    try:
        for ref in refs:
            kind, id_ = ref["type"], ref["id"]
            if kind == "scope":
                if ref != _scope_ref(user):
                    return False
            elif kind == "resume":
                _require(user, "resume")
                if db.execute(_resumes(user).where(ParsedResume.id == id_)).first() is None:
                    return False
            elif kind == "vacancy":
                _require(user, "job", "resume", "match")
                current = next((r for r in job_service.vacancy_alerts(db, user) if r["job_profile_id"] == id_), None)
                if current != ref.get("snapshot"):
                    return False
            elif kind == "job":
                _require(user, "job")
                if db.get(JobProfile, id_) is None:
                    return False
            elif kind == "match":
                _require(user, "match", "resume", "job")
                row = db.get(MatchResult, id_)
                if row is None or db.get(JobProfile, row.job_profile_id) is None or db.execute(
                    _resumes(user, "match").where(ParsedResume.id == row.parsed_resume_id)).first() is None:
                    return False
            elif kind == "profile":
                _require(user, "talent", "resume")
                row = db.get(TalentProfile, id_)
                if row is None or db.execute(_resumes(user, "talent").where(ParsedResume.id == row.candidate_id)).first() is None:
                    return False
            else:
                return False
        return True
    except (ApiError, KeyError, TypeError, ValueError):
        return False


def _result(intent, filters, facts, refs, answer):
    return {"facts": facts, "source_refs": refs, "context": {"intent": intent, "filters": filters,
            "resume_ids": [r["id"] for r in refs if r["type"] == "resume"],
            "job_ids": [r["id"] for r in refs if r["type"] in {"job", "vacancy"}]}, "answer": answer}


def _clarify(message="请补充明确的人才姓名、编号或岗位编号。"):
    return _result("clarify", {}, {}, [], message)


def _filters(intent, filters):
    if intent not in FILTERS or not isinstance(filters, dict) or set(filters) - FILTERS[intent]:
        raise ApiError(422, "查询条件不受支持，请重新描述问题")
    for key, value in filters.items():
        if key in {"resume_id", "job_id", "min_years"}:
            if type(value) is not int or not (0 if key == "min_years" else 1) <= value <= (80 if key == "min_years" else 2147483647):
                raise ApiError(422, "查询编号或年限不合法")
        elif not isinstance(value, str) or not value.strip() or len(value) > 300:
            raise ApiError(422, "查询文字不合法")
    return filters


def _brief(p, f, user):
    brief = resume_service.brief_of(p, f, user)
    return {k: brief[k] for k in ("parsed_resume_id", "name", "education", "major", "years_experience", "skills_top")}


def query_business(db, user, intent, filters):
    filters = _filters(intent, filters)
    if intent == "clarify":
        return _clarify()
    if intent == "out_of_scope":
        return _result(intent, {}, {}, [], "我可以查询人才、解释已有匹配和画像信息，并统计岗位缺口。请提出相关的只读问题。")
    if intent == "vacancy":
        _require(user, "job", "resume", "match")
        # Recheck scoped aggregates on history recovery as they may have changed.
        rows = job_service.vacancy_alerts(db, user)
        rows = [r for r in rows if not filters.get("job_id") or r["job_profile_id"] == filters["job_id"]][:10]
        refs = [_scope_ref(user)] + [{**_ref("vacancy", r["job_profile_id"], r["job_name"], "/vacancy"), "snapshot": r} for r in rows]
        return _result(intent, filters, {"jobs": rows}, refs, "\n".join(f"{r['job_name']}：名额 {r['headcount']}，已有匹配通过 {r['passed']}，缺口 {r['vacancy']}。" for r in rows) or "暂无可用岗位数据。")
    _require(user, "resume")
    query = _resumes(user)
    if intent == "semantic_search":
        if not filters.get("query"):
            return _clarify("请描述要检索的技能或相关经历。")
        result = vector_service.semantic_search_resumes(db, user, filters["query"], 10)
        if not result.get("available"):
            raise ApiError(503, "语义检索服务不可用")
        ids = [r["parsed_resume_id"] for r in result["items"] if r.get("accessible")]
        rows = {p.id: (p, f) for p, f in db.execute(query.where(ParsedResume.id.in_(ids))).all()}
        pairs = [rows[i] for i in ids if i in rows]
    elif intent == "search_talent":
        if not filters:
            return _clarify("请提供技能、学历、姓名或工作年限等查询条件。")
        if filters.get("keyword"):
            k = filters["keyword"]
            query = query.where(or_(ParsedResume.name.contains(k, autoescape=True),
                ParsedResume.major.contains(k, autoescape=True), ParsedResume.skills.cast(String).contains(k, autoescape=True)))
        if "education" in filters:
            query = query.where(ParsedResume.education == filters["education"])
        if "min_years" in filters:
            query = query.where(ParsedResume.years_experience >= filters["min_years"])
        pairs = None
    else:
        _require(user, "match", "job") if intent == "match_explain" else _require(user, "talent")
        query = _resumes(user, "match" if intent == "match_explain" else "talent")
        if not filters.get("name") and not filters.get("resume_id"):
            return _clarify()
        pairs = None
    if pairs is None:
        if "name" in filters:
            query = query.where(ParsedResume.name == filters["name"])
        if "resume_id" in filters:
            query = query.where(ParsedResume.id == filters["resume_id"])
        pairs = db.execute(query.order_by(ParsedResume.id.desc()).limit(10)).all()
    if not pairs:
        return _result(intent, filters, {}, [], "当前授权范围内没有符合条件的记录。")
    if intent in {"search_talent", "semantic_search"}:
        facts = [_brief(p, f, user) for p, f in pairs]
        return _result(intent, filters, {"talents": facts}, [_resume_ref(p) for p, _ in pairs],
                       "当前查询返回以下人才（最多 10 条）：\n" + "\n".join(f"{i['name']}（编号 {i['parsed_resume_id']}）：{i['years_experience']} 年经验，{i['education']}，技能 {'、'.join(i['skills_top'])}" for i in facts))
    if len(pairs) != 1:
        return _clarify("存在同名人才，请提供唯一的简历编号。")
    p, f = pairs[0]
    refs = [_resume_ref(p)]
    if intent == "match_explain":
        if not filters.get("job_id"):
            return _clarify("请提供要解释的岗位编号。")
        job = db.get(JobProfile, filters["job_id"])
        result = db.scalar(select(MatchResult).where(MatchResult.parsed_resume_id == p.id,
            MatchResult.job_profile_id == filters["job_id"]).order_by(MatchResult.id.desc()).limit(1))
        if job is None or result is None:
            return _result(intent, filters, {}, refs, "暂无该人才与岗位的已有匹配记录。")
        refs += [_ref("job", job.id, job.name, "/job-profiles"), _ref("match", result.id, "已有匹配记录", "/matching")]
        detail = result.condition_detail if isinstance(result.condition_detail, dict) else {}
        threshold = detail.get("threshold", job.passing_threshold)
        if type(threshold) not in (int, float):
            threshold = job.passing_threshold
        facts = {"talent": _brief(p, f, user), "job": job.name, "score": result.total_score,
                 "threshold": threshold, "passed": result.passed, "hard_failed": detail.get("hard_failed") is True}
        answer = f"{p.name}与{job.name}的已有匹配得分为 {result.total_score}，记录阈值为 {threshold}。"
        answer += "存在硬性条件未满足。" if facts["hard_failed"] else "该结果仅供业务核查。"
        return _result(intent, filters, facts, refs, answer)
    profile = db.scalar(select(TalentProfile).where(TalentProfile.candidate_id == p.id).order_by(TalentProfile.id.desc()).limit(1))
    if profile is None:
        return _result(intent, filters, {}, refs, "该人才暂无已生成人才画像。")
    # Legacy profile evidence may link exams by name, so only use verified resume facts here.
    refs.append(_ref("profile", profile.id, "已有画像", "/talent-profiles"))
    facts = {"talent": _brief(p, f, user), "profile_exists": True}
    has_exam = any(isinstance(s, dict) and s.get("type") == "exam" for s in (profile.data_sources or []))
    if not has_exam and isinstance(profile.abilities, dict):
        facts["abilities"] = {d: profile.abilities[d] for d in talent_service.DIMENSIONS
                              if type(profile.abilities.get(d)) in (int, float) and 0 <= profile.abilities[d] <= 100}
    answer = f"{p.name}已有画像。简历记录显示 {p.years_experience} 年经验。"
    if has_exam:
        answer += "画像的测评身份关联需要在原页面核实。"
    elif facts.get("abilities"):
        answer += "画像已保存的维度分数：" + "、".join(f"{d} {v} 分" for d, v in facts["abilities"].items())
    return _result(intent, filters, facts, refs, answer)
