"""人才画像：从解析后的简历生成五维能力画像（规则为主，AI 可选润色）。

映射约定（MVP 简化）：`talent_profiles.candidate_id` 存 `parsed_resumes.id`，
因为候选人模块不在本期范围；`data_sources` 里写明来源，后续接候选人时再迁移。
"""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope
from app.core.response import ApiError
from app.infrastructure.ai_gateway import gateway
from app.models.orm import (
    ExamSubmission, GrowthLedger, JobProfile, Question,
    ParsedResume, ResumeFile, TalentProfile, TalentTag,
)
from app.infrastructure.skill_dict import SKILL_BOOK, canonical, category_of

DIMENSIONS = ["技术深度", "工程能力", "业务理解", "协作沟通", "成长性"]

ENG_SKILLS = {"Docker", "Kubernetes", "微服务", "分布式", "Celery", "模型部署", "向量数据库", "Redis", "Kafka", "RabbitMQ"}
PROD_SKILLS = {"需求分析", "产品设计", "项目管理", "Axure", "数据分析", "用户研究", "运营"}
SOFT_SKILLS = {"沟通", "团队协作", "英语"}
DOMAIN_WORDS = ["业务", "增长", "转化", "客户", "落地", "方案", "流程", "运营", "指标"]

EDU_SCORE = {"博士": 10, "硕士": 8, "本科": 6, "大专": 4, "高中": 2}


# 测评知识分类 → 画像五维：先命中先算，顺序有意义（"数据"在两个维度都会出现，技术深度优先）
CATEGORY_DIM_RULES: list[tuple[tuple[str, ...], str]] = [
    (("算法", "模型", "机器学习", "深度学习", "大模型", "nlp", "框架", "语言", "python", "向量"), "技术深度"),
    (("工程", "部署", "性能", "架构", "运维", "测试", "数据库", "后端", "并发", "容器"), "工程能力"),
    (("业务", "产品", "需求", "行业", "指标", "分析", "方案"), "业务理解"),
    (("沟通", "协作", "团队", "管理", "项目", "跨部门"), "协作沟通"),
    (("学习", "成长", "复盘", "反思", "规划"), "成长性"),
]

# 测评在画像里的权重：简历仍是主证据，测评为"验证性证据"
EXAM_WEIGHT = 0.30


def _dim_of_exam(category: str, point: str = "") -> str | None:
    text = f"{category} {point}".lower()
    for words, dim in CATEGORY_DIM_RULES:
        if any(w in text for w in words):
            return dim
    return None


def _exam_evidence(db: Session, parsed_resume_id: int) -> dict[str, Any]:
    """把明确关联简历的测评作答折成五维证据：各维得分率 = 该维已得 / 该维满分。

    只认有知识分类的题目；分类不属于任何维度时不硬塞，返回空字典。
    """
    subs = db.execute(
        select(ExamSubmission).where(ExamSubmission.parsed_resume_id == parsed_resume_id)
    ).scalars().all()
    if not subs:
        return {}

    qids: set[int] = set()
    for sub in subs:
        for item in (sub.detail or []):
            qid = item.get("question_id")
            if qid:
                qids.add(int(qid))
    questions: dict[int, Question] = {
        q.id: q for q in db.execute(select(Question).where(Question.id.in_(qids))).scalars()
    } if qids else {}

    got: dict[str, float] = {}
    full: dict[str, float] = {}
    count: dict[str, int] = {}
    for sub in subs:
        for item in (sub.detail or []):
            q = questions.get(int(item.get("question_id") or 0))
            if q is None:
                continue
            dim = _dim_of_exam(q.knowledge_category or "", q.knowledge_point or "")
            if dim is None:
                continue
            got[dim] = got.get(dim, 0.0) + float(item.get("score") or 0)
            full[dim] = full.get(dim, 0.0) + float(item.get("max_score") or 0)
            count[dim] = count.get(dim, 0) + 1

    detail: dict[str, dict[str, Any]] = {}
    for dim, max_score in full.items():
        if max_score <= 0:
            continue
        detail[dim] = {
            "score": round(100.0 * got.get(dim, 0.0) / max_score),
            "questions": count.get(dim, 0),
            "raw": f"{got.get(dim, 0):g}/{max_score:g}",
        }
    if not detail:
        return {}
    return {
        "type": "exam",
        "submissions": len(subs),
        "exam_ids": sorted({s_.exam_id for s_ in subs}),
        "detail": detail,
    }


def _blend(dims: dict[str, int], evidence: dict[str, Any]) -> tuple[dict[str, int], list[dict]]:
    """简历分 ×(1-w) + 测评分 ×w；证据越薄权重越低（单题不足以推翻简历）。

    w 上限是 EXAM_WEIGHT；按题量折算：0 题→0，1 题→1/3，3 题及以上→满额。
    """
    blended = dict(dims)
    rows: list[dict] = []
    for dim, ev in (evidence.get("detail") or {}).items():
        base = int(dims.get(dim, 60))
        exam = int(ev.get("score") or 0)
        n = int(ev.get("questions", 0) or 0)
        weight = round(EXAM_WEIGHT * min(1.0, n / 3), 2)
        merged = _clamp(base * (1 - weight) + exam * weight)
        blended[dim] = merged
        rows.append({"dim": dim, "resume": base, "exam": exam, "merged": merged,
                     "questions": n, "weight": weight})
    return blended, rows


def _clamp(v: float) -> int:
    return int(max(0, min(100, round(v))))


def _analyze(parsed: ParsedResume) -> dict[str, Any]:
    skills = [canonical(s) or s for s in (parsed.skills or [])]
    cats: dict[str, int] = {}
    for s in skills:
        cats[category_of(s)] = cats.get(category_of(s), 0) + 1

    text = (parsed.resume_content or "") + " " + (parsed.strengths or "")
    years = int(parsed.years_experience or 0)
    edu = EDU_SCORE.get(parsed.education or "", 3)
    n_skill = len(skills)
    eng_hits = len({s for s in skills if s in ENG_SKILLS})
    prod_hits = len({s for s in skills if s in PROD_SKILLS})
    soft_hits = len({s for s in skills if s in SOFT_SKILLS})
    domain_hits = sum(1 for w in DOMAIN_WORDS if w in text)

    dims = {
        "技术深度": _clamp(38 + 9 * cats.get("AI", 0) + 7 * cats.get("语言", 0) + min(12, years * 2)),
        "工程能力": _clamp(34 + 14 * eng_hits + 6 * cats.get("后端", 0) + min(10, years)),
        "业务理解": _clamp(32 + 12 * prod_hits + 5 * domain_hits + 4 * cats.get("产品", 0)),
        "协作沟通": _clamp(45 + 18 * soft_hits + (10 if years >= 3 else 0) + edu),
        "成长性": _clamp(34 + min(24, n_skill * 3) + min(20, years * 4) + edu),
    }
    return {"dims": dims, "skills": skills, "cats": cats, "years": years,
            "eng_hits": eng_hits, "prod_hits": prod_hits, "domain_hits": domain_hits}


def _tags(parsed: ParsedResume, info: dict) -> list[str]:
    tags: list[str] = []
    cats = info["cats"]
    if cats.get("AI"):
        tags.append("AI 算法")
    if cats.get("后端"):
        tags.append("后端工程")
    if cats.get("前端"):
        tags.append("前端开发")
    if cats.get("产品"):
        tags.append("产品能力")
    if info["years"] >= 5:
        tags.append("资深")
    elif info["years"] >= 3:
        tags.append("中坚")
    else:
        tags.append("新锐")
    if parsed.education in ("博士", "硕士"):
        tags.append("高学历")
    return tags[:5]


def _copy(parsed: ParsedResume, info: dict, ai_note: dict | None) -> dict:
    dims = info["dims"]
    ranked = sorted(dims.items(), key=lambda kv: -kv[1])
    top = ranked[:2]
    low = ranked[-1]
    skills = info["skills"]

    strengths = [f"{k} {v} 分" for k, v in top] + skills[:3]
    weaknesses = [f"{low[0]}相对偏弱（{low[1]} 分）"]
    if info["years"] < 3:
        weaknesses.append("工作年限偏短")

    summary = (
        f"{parsed.education or '学历未识别'}·{parsed.major or '专业未识别'}，"
        f"{info['years']} 年经验，技能覆盖 {len(skills)} 项；"
        f"强项为{top[0][0]}（{top[0][1]} 分）与{top[1][0]}（{top[1][1]} 分）。"
    )
    recommendation = (
        f"建议优先安排「{top[0][0]}」相关任务；"
        f"若岗位对{low[0]}要求高，需在面谈中重点验证。"
    )
    if ai_note:
        summary = ai_note.get("summary") or summary
        recommendation = ai_note.get("recommendation") or recommendation

    return {
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "recommendation": recommendation,
        "profile_title": f"{parsed.name} · {top[0][0]}型",
    }


def _ai_polish(parsed: ParsedResume, info: dict) -> dict | None:
    if not gateway.available:
        return None
    prompt = {
        "name": parsed.name,
        "education": parsed.education,
        "major": parsed.major,
        "years": info["years"],
        "skills": info["skills"][:12],
        "dimensions": info["dims"],
        "resume_excerpt": (parsed.resume_content or "")[:1200],
    }
    res = gateway.chat(
        "你是资深 HR 人才评估专家。基于给定的结构化字段写人才画像，只输出 JSON："
        '{"summary": "两句话以内", "recommendation": "一句话用人建议"}。'
        "不要编造字段里没有的经历，不要用夸张形容词。",
        json.dumps(prompt, ensure_ascii=False),
        max_tokens=400,
        json_mode=True,
    )
    return res.json() if res.ok else None


def _ensure_tags(db: Session, names: list[str]) -> list[int]:
    ids: list[int] = []
    for name in names:
        tag = db.execute(select(TalentTag).where(TalentTag.name == name)).scalar_one_or_none()
        if tag is None:
            tag = TalentTag(name=name, description=f"画像自动生成：{name}", category="自动", status="active")
            db.add(tag)
            db.flush()
        ids.append(tag.id)
    return ids


def _load_parsed(db: Session, user: CurrentUser, resume_id: int | None) -> list[ParsedResume]:
    query = (
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ResumeFile.status == "completed", ParsedResume.is_current.is_(True))
    )
    query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user, resource=("resume", "match"))
    if resume_id:
        query = query.where(ParsedResume.id == resume_id)
    return [p for p, _f in db.execute(query.order_by(ParsedResume.id)).all()]


def generate(db: Session, user: CurrentUser, resume_id: int | None = None,
             use_ai: bool = True, use_exam: bool = True) -> dict:
    rows = _load_parsed(db, user, resume_id)
    if not rows:
        raise ApiError(400, "没有可生成画像的已解析简历")

    created, updated, ai_used, exam_used = 0, 0, 0, 0
    for parsed in rows:
        info = _analyze(parsed)
        evidence = _exam_evidence(db, parsed.id) if use_exam else {}
        blended_rows: list[dict] = []
        if evidence:
            info["dims"], blended_rows = _blend(info["dims"], evidence)
            exam_used += 1
        ai_note = _ai_polish(parsed, info) if use_ai else None
        if ai_note:
            ai_used += 1
        content = _copy(parsed, info, ai_note)
        tag_ids = _ensure_tags(db, _tags(parsed, info))

        profile = db.execute(
            select(TalentProfile).where(TalentProfile.candidate_id == parsed.id)
        ).scalar_one_or_none()
        if profile is None:
            profile = TalentProfile(candidate_id=parsed.id)
            db.add(profile)
            created += 1
        else:
            updated += 1

        profile.candidate_name = parsed.name
        profile.position = ""
        profile.project_name = ""
        profile.profile_title = content["profile_title"]
        profile.summary = content["summary"]
        profile.strengths = content["strengths"]
        profile.weaknesses = content["weaknesses"]
        profile.abilities = info["dims"]
        profile.dimensions = DIMENSIONS
        profile.tag_ids = tag_ids
        profile.tag_quantify = {str(t): 1.0 for t in tag_ids}
        sources: list[Any] = [
            "resume", "match",
            {"resume_id": parsed.id, "generated_at": datetime.now().isoformat(timespec="seconds"),
             "ai": bool(ai_note)},
        ]
        if evidence:
            sources.append({
                "type": "exam",
                "submissions": evidence.get("submissions", 0),
                "exam_ids": evidence.get("exam_ids", []),
                "weight": EXAM_WEIGHT,
                "rows": blended_rows,
            })
        profile.data_sources = sources
        profile.recommendation = content["recommendation"]
        profile.status = "active"

    db.commit()
    return {"total": len(rows), "created": created, "updated": updated,
            "ai_used": ai_used, "ai_available": gateway.available,
            "exam_used": exam_used, "exam_weight": EXAM_WEIGHT}


RATING_BANDS = ((85, "A"), (70, "B"), (0, "C"))  # A≥85 / B≥70 / C 其余


def _rate(score: float) -> str:
    for floor, letter in RATING_BANDS:
        if score >= floor:
            return letter
    return "C"


def ability_rating(abilities: dict[str, Any]) -> dict:
    """把五维分数映射为 A/B/C 评级，并给整体评级（五维均值）。"""
    dims = [d for d in DIMENSIONS if d in abilities]
    ratings = {d: _rate(float(abilities.get(d, 0) or 0)) for d in dims}
    avg = sum(float(abilities.get(d, 0) or 0) for d in dims) / len(dims) if dims else 0.0
    return {"per_dimension": ratings, "overall": _rate(avg), "overall_score": round(avg, 1)}


def serialize(profile: TalentProfile, tag_names: dict[int, str]) -> dict:
    abilities = profile.abilities if isinstance(profile.abilities, dict) else {}
    return {
        "id": profile.id,
        "resume_id": profile.candidate_id,
        "name": profile.candidate_name,
        "title": profile.profile_title,
        "summary": profile.summary,
        "strengths": profile.strengths or [],
        "weaknesses": profile.weaknesses or [],
        "abilities": abilities,
        "dimensions": profile.dimensions or DIMENSIONS,
        "tags": [tag_names.get(t, str(t)) for t in (profile.tag_ids or [])],
        "recommendation": profile.recommendation,
        "data_sources": profile.data_sources or [],
        "exam_evidence": next(
            (x for x in (profile.data_sources or [])
             if isinstance(x, dict) and x.get("type") == "exam"), None),
        "rating": ability_rating(abilities),
    }


def list_profiles(db: Session, user: CurrentUser, keyword: str, page: int, page_size: int):
    # 只列「现行简历」对应的画像：同一人被新版替代后，旧画像不该再出现在列表里
    current_ids = {p.id for p in _load_parsed(db, user, None)}
    rows = db.execute(select(TalentProfile).order_by(TalentProfile.id.desc())).scalars().all()
    tag_names = {t.id: t.name for t in db.execute(select(TalentTag)).scalars()}
    items = [serialize(p, tag_names) for p in rows
             if int(p.candidate_id or 0) in current_ids]
    if keyword:
        kw = keyword.strip()
        items = [i for i in items if kw in i["name"] or kw in "、".join(i["tags"]) or kw in i["title"]]
    total = len(items)
    start = (page - 1) * page_size
    return items[start : start + page_size], total


def _visible_profile(db: Session, user: CurrentUser, profile_id: int) -> TalentProfile:
    profile = db.get(TalentProfile, profile_id)
    if profile is None:
        raise ApiError(404, "画像不存在")
    if not _load_parsed(db, user, profile.candidate_id):
        raise ApiError(403, "无权访问该画像")
    return profile


def get_profile(db: Session, user: CurrentUser, profile_id: int) -> dict:
    profile = _visible_profile(db, user, profile_id)
    tag_names = {t.id: t.name for t in db.execute(select(TalentTag)).scalars()}
    return serialize(profile, tag_names)


def ability_trend(db: Session, user: CurrentUser, profile_id: int) -> dict:
    """某候选人能力变化轨迹：当前五维 + 台账里的前后变化，供趋势图使用。"""
    profile = _visible_profile(db, user, profile_id)
    abilities = profile.abilities if isinstance(profile.abilities, dict) else {}
    rows = db.execute(
        select(GrowthLedger).where(GrowthLedger.candidate_id == profile.candidate_id)
        .order_by(GrowthLedger.id)
    ).scalars().all()
    history = [{
        "id": r.id, "dimension": r.dimension, "before_score": r.before_score,
        "after_score": r.after_score, "delta": r.delta, "source": r.source,
        "note": r.note,
        "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
    } for r in rows]
    return {
        "candidate_id": profile.candidate_id,
        "candidate_name": profile.candidate_name,
        "current": abilities,
        "rating": ability_rating(abilities),
        "history": history,
    }


def _fallback_report(facts: dict) -> dict:
    """不依赖模型的结构化结论：所有句子都由数字直接生成，不编造。"""
    ab = facts["abilities"]
    ranked = sorted(ab.items(), key=lambda kv: -kv[1])
    top, low = ranked[:2], ranked[-1]
    risks = [f"{d} 仅 {v} 分" for d, v in ranked if v < 70]
    gaps = facts.get("job_gaps") or []
    risks += [f"距「{g['job_name']}」基线 {g['dimension']} 差 {g['gap']} 分" for g in gaps]
    actions = []
    for d, v in ranked:
        if v < 70:
            actions.append(f"针对{d}安排一次专项测评，验证是能力缺口还是简历未体现")
    if facts.get("exam_rows"):
        actions.append("复核测评证据里被拉低的维度，判断是否需要重考")
    if not actions:
        actions.append("各维均达标，建议进入面试验证实战能力")
    return {
        "headline": f"{facts['candidate_name']}：{top[0][0]} {top[0][1]} 分最突出，{low[0]} {low[1]} 分最弱",
        "structure": (
            f"五维均分 {facts['rating']['overall_score']}，整体评级 {facts['rating']['overall']}；"
            f"强项为 {top[0][0]}({top[0][1]}) 与 {top[1][0]}({top[1][1]})，"
            f"弱项为 {low[0]}({low[1]})。"
        ),
        "strengths": [f"{d} {v} 分（{facts['rating']['per_dimension'].get(d, 'C')} 级）" for d, v in top],
        "risks": risks or ["未发现明显短板"],
        "actions": actions[:4],
        "verdict": f"整体 {facts['rating']['overall']} 级，{facts['rating']['overall_score']} 分",
    }


def analysis_report(db: Session, user: CurrentUser, profile_id: int, job_id: int | None = None) -> dict:
    """AI 能力结构分析：先把事实算出来，再让模型只在这些事实上做归纳。"""
    profile = _visible_profile(db, user, profile_id)
    abilities = profile.abilities if isinstance(profile.abilities, dict) else {}
    rating = ability_rating(abilities)

    ledger_rows = db.execute(
        select(GrowthLedger).where(GrowthLedger.candidate_id == profile.candidate_id)
        .order_by(GrowthLedger.id.desc()).limit(5)
    ).scalars().all()
    exam_ev = next((x for x in (profile.data_sources or [])
                    if isinstance(x, dict) and x.get("type") == "exam"), None)
    exam_rows = (exam_ev or {}).get("rows") or []

    job_gaps = []
    if job_id:
        job = db.get(JobProfile, job_id)
        if job is not None:
            baseline = job.ability_requirements or {}
            for dim, base in baseline.items():
                cur = int(abilities.get(dim, 0) or 0)
                if cur < int(base):
                    job_gaps.append({"job_name": job.name, "dimension": dim,
                                     "current": cur, "baseline": int(base), "gap": int(base) - cur})

    facts = {
        "candidate_name": profile.candidate_name,
        "abilities": abilities,
        "rating": rating,
        "exam_rows": exam_rows,
        "ledger": [{"dimension": r.dimension, "before": r.before_score, "after": r.after_score}
                   for r in ledger_rows],
        "job_gaps": job_gaps,
        "resume_summary": (profile.summary or "")[:300],
    }

    report, source = None, "rule"
    if gateway.available:
        res = gateway.chat(
            "你是人才评估专家。只能使用给定 JSON 里的数字与事实，不得编造经历或分数。"
            "输出 JSON：{\"headline\":\"一句话结论\",\"structure\":\"能力结构两句话\","
            "\"strengths\":[\"…\"],\"risks\":[\"…\"],\"actions\":[\"可执行建议\"],"
            "\"verdict\":\"一句话用人判断\"}。每条不超过 40 字。",
            json.dumps(facts, ensure_ascii=False)[:3000],
            max_tokens=700, json_mode=True,
        )
        if res.ok:
            data = res.json()
            if isinstance(data, dict) and data.get("headline"):
                report = {
                    "headline": str(data.get("headline"))[:80],
                    "structure": str(data.get("structure") or "")[:400],
                    "strengths": [str(x)[:60] for x in (data.get("strengths") or [])][:4],
                    "risks": [str(x)[:60] for x in (data.get("risks") or [])][:4],
                    "actions": [str(x)[:80] for x in (data.get("actions") or [])][:4],
                    "verdict": str(data.get("verdict") or "")[:80],
                }
                source = "ai"

    if report is None:
        report = _fallback_report(facts)

    return {"source": source, "report": report, "facts": facts, "ai_available": gateway.available}


def skill_catalog() -> list[dict]:
    return [{"name": k, "category": v[1]} for k, v in SKILL_BOOK.items()]
