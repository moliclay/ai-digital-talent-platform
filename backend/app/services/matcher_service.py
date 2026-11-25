"""可解释匹配引擎（MVP 核心）。

设计要点（方案 §6）：
1. 五维加权，权重取自 job_profiles.score_rules，缺省用默认值；
2. 硬条件有任何一条不满足 → 分数折算到合格线下，但**不隐藏分数**，逐条点名差在哪；
3. 每次匹配把当时的权重与阈值快照写进 condition_detail，保证历史结果永久可复现。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from app.infrastructure.skill_dict import SKILL_BOOK, canonical, skills_overlap

DEFAULT_WEIGHTS = {"education": 0.20, "skills": 0.40, "experience": 0.15, "project": 0.15, "other": 0.10}

DIM_LABEL = {
    "education": "学历",
    "skills": "技能",
    "experience": "工作年限",
    "project": "项目/成果",
    "other": "档案完整度",
    "ability": "画像契合",
}

EDU_LEVEL = {
    "博士": 5, "硕士": 4, "研究生": 4, "本科": 3, "学士": 3,
    "大专": 2, "专科": 2, "高职": 2, "高中": 1, "中专": 1,
}

# 岗位名 → 隐含技能要求（显式条件只写 1 条时，光看那 1 条会算出虚高分）
IMPLIED_BY_POSITION: dict[str, list[str]] = {
    "算法": ["机器学习", "深度学习", "Python", "PyTorch", "大模型"],
    "产品经理": ["需求分析", "产品设计", "项目管理", "数据分析"],
    "前端": ["JavaScript", "React", "Vue", "CSS"],
    "数据工程": ["SQL", "Python", "数据分析"],
    "测试": ["Python", "Shell"],
    "运维": ["Docker", "Kubernetes", "Shell"],
}

# 领域关键词：用于"项目/成果"维度，看简历全文与岗位语境的贴合度
DOMAIN_KEYWORDS = [
    "算法", "模型", "大模型", "推理", "训练", "推荐", "搜索", "广告", "风控",
    "平台", "中台", "SaaS", "B端", "C端", "增长", "转化", "需求", "原型",
    "架构", "并发", "性能", "数据", "报表", "bi", "工程化", "落地",
]

DIM_MAX = {"education": 100.0, "skills": 100.0, "experience": 100.0, "project": 100.0, "other": 100.0}


@dataclass
class Verdict:
    total_score: int
    passed: bool
    reason: str
    detail: dict[str, Any] = field(default_factory=dict)


def _norm_weights(job: dict) -> dict[str, float]:
    raw = (job.get("score_rules") or {}).get("weights") if isinstance(job.get("score_rules"), dict) else None
    if not raw:
        return dict(DEFAULT_WEIGHTS)
    weights: dict[str, float] = {}
    for k, v in raw.items():
        key = _norm_dim_key(k)
        if key:
            try:
                weights[key] = float(v)
            except (TypeError, ValueError):
                continue
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    # 归一化，避免甲方手填 3 / 4 这类非百分比权重把总分放大
    return {k: round(v / total, 4) for k, v in weights.items()}


def _norm_dim_key(key: str) -> str | None:
    mapping = {
        "education": "education", "学历": "education",
        "skills": "skills", "skill": "skills", "技能": "skills",
        "experience": "experience", "years": "experience", "工作年限": "experience", "年限": "experience",
        "project": "project", "项目": "project", "成果": "project",
        "other": "other", "完整度": "other", "其他": "other",
        "ability": "ability", "画像": "ability", "画像契合": "ability", "能力": "ability",
    }
    return mapping.get(str(key).strip())


def required_skills(job: dict) -> list[str]:
    """显式条件里的技能 ∪ 岗位名隐含技能。"""
    explicit: list[str] = []
    for cond in job.get("conditions") or []:
        if not isinstance(cond, dict):
            continue
        if str(cond.get("key", "")).strip() in ("技能", "skill", "skills"):
            val = cond.get("value")
            for v in (val if isinstance(val, list) else str(val).split(",")):
                v = str(v).strip()
                if v:
                    explicit.append(canonical(v) or v)

    implied: list[str] = []
    name = str(job.get("name") or "")
    for keyword, skills in IMPLIED_BY_POSITION.items():
        if keyword in name:
            implied.extend(skills)
    if not implied and not explicit:
        implied = ["Python"]
    return list(dict.fromkeys(explicit + implied))


def _edu_level(text: str | None) -> int:
    if not text:
        return 0
    for word, level in sorted(EDU_LEVEL.items(), key=lambda kv: -len(kv[0])):
        if word in text:
            return level
    return 0


def _score_education(req_level: int, got_level: int) -> tuple[float, str]:
    if req_level == 0:
        return 100.0, "岗位未设学历要求"
    if got_level >= req_level:
        gap = got_level - req_level
        value = min(100.0, 92.0 + gap * 4)
        return value, f"学历 {_level_name(got_level)} 达到要求 {_level_name(req_level)}"
    deficit = req_level - got_level
    value = max(0.0, 92.0 - deficit * 37)
    return value, f"学历 {_level_name(got_level) or '未识别'} 低于要求 {_level_name(req_level)}"


def _level_name(level: int) -> str:
    return {5: "博士", 4: "硕士", 3: "本科", 2: "大专", 1: "高中"}.get(level, "未识别")


def _score_skills(req_skills: list[str], cand_skills: list[str], text: str) -> tuple[float, list[str], list[str]]:
    hits = skills_overlap(req_skills, cand_skills)
    # 简历正文里出现也算命中（技能栏常漏写）
    for s in req_skills:
        if s in hits:
            continue
        canon = canonical(s) or s
        entry = SKILL_BOOK.get(canon)
        needles = [canon] + (entry[0] if entry else [])
        if any(n.lower() in text.lower() for n in needles if n):
            hits.append(canon)
    hits = list(dict.fromkeys(hits))
    missing = [s for s in req_skills if (canonical(s) or s) not in hits]

    coverage = len(hits) / len(req_skills) if req_skills else 1.0
    extra = [c for c in cand_skills if (canonical(c) or c) not in {canonical(r) or r for r in req_skills}]
    bonus = min(10.0, 10.0 * len(extra) / 3)
    return round(min(100.0, 90.0 * coverage + bonus), 1), hits, missing


def _score_experience(req_years: int, got_years: int) -> tuple[float, str]:
    if req_years <= 0:
        return 100.0, f"工作年限 {got_years} 年（岗位未设年限门槛）"
    if got_years >= req_years:
        over = got_years / req_years
        value = min(100.0, 88.0 + min(12.0, (over - 1) * 8))
        return round(value, 1), f"工作年限 {got_years} 年，满足 ≥{req_years} 年"
    ratio = got_years / req_years
    return round(max(0.0, 85.0 * ratio), 1), f"工作年限 {got_years} 年，低于 ≥{req_years} 年"


def _score_project(job: dict, text: str) -> tuple[float, list[str]]:
    context = " ".join([str(job.get("name") or ""), str(job.get("prompt") or "")])
    keywords = [k for k in DOMAIN_KEYWORDS if k in context.lower()] or ["项目", "经验"]
    hits = [k for k in keywords if k in text.lower()]
    value = min(100.0, 45.0 + 15.0 * len(hits)) if hits else 40.0
    return round(value, 1), hits


def _score_other(parsed: dict) -> tuple[float, int]:
    checks = [
        bool(parsed.get("phone")),
        bool(parsed.get("email")),
        bool(parsed.get("education")),
        bool(parsed.get("major")),
        bool(parsed.get("skills")),
        bool(parsed.get("years_experience")),
    ]
    return round(100.0 * sum(checks) / len(checks), 1), sum(checks)


def score_ability(requirements: dict[str, Any] | None, abilities: dict[str, Any] | None) -> tuple[float | None, list[dict]]:
    """画像契合：逐维看"实际能力 / 基线"，超过基线按 100 封顶，再取平均。

    返回 (分数, 明细)；岗位没设基线或候选人没画像时返回 (None, [])。
    """
    if not requirements or not abilities:
        return None, []
    rows: list[dict] = []
    ratios: list[float] = []
    for dim, base in requirements.items():
        try:
            base_f = float(base)
        except (TypeError, ValueError):
            continue
        if base_f <= 0:
            continue
        actual = abilities.get(dim)
        if actual is None:
            rows.append({"dim": dim, "baseline": base_f, "actual": None, "ratio": 0.0})
            ratios.append(0.0)
            continue
        actual_f = float(actual)
        ratio = min(1.0, actual_f / base_f)
        rows.append({"dim": dim, "baseline": base_f, "actual": round(actual_f, 1), "ratio": round(ratio, 3)})
        ratios.append(ratio)
    if not ratios:
        return None, []
    return round(100.0 * sum(ratios) / len(ratios), 1), rows


def _hard_fail(job: dict, parsed: dict, hits: list[str], missing: list[str]) -> tuple[bool, list[str]]:
    """返回 (是否硬失败, 未满足条件的中文名)。"""
    fails: list[str] = []
    for cond in job.get("conditions") or []:
        if not isinstance(cond, dict):
            continue
        key = str(cond.get("key", "")).strip()
        op = str(cond.get("op", ">=")).strip()
        value = cond.get("value")

        if key in ("学历", "education"):
            req = _edu_level(str(value))
            got = _edu_level(parsed.get("education"))
            if op in (">=", ">") and got < req:
                fails.append(f"学历（{parsed.get('education') or '未识别'} < {value}）")
        elif key in ("技能", "skills", "skill"):
            wanted = [str(v).strip() for v in (value if isinstance(value, list) else [value]) if str(v).strip()]
            for w in wanted:
                canon = canonical(w) or w
                if canon in missing:
                    fails.append(f"技能（未命中 {w}）")
        elif key in ("工作年限", "experience", "年限"):
            try:
                req = int(float(value))
            except (TypeError, ValueError):
                continue
            if op in (">=", ">") and int(parsed.get("years_experience") or 0) < req:
                fails.append(f"工作年限（{parsed.get('years_experience') or 0} 年 < {req} 年）")
    return bool(fails), fails


def evaluate(job: dict, parsed: dict, abilities: dict[str, Any] | None = None) -> Verdict:
    weights = _norm_weights(job)
    threshold = int(job.get("passing_threshold") or 70)

    req_skills = required_skills(job)
    cand_skills = [str(s) for s in (parsed.get("skills") or [])]
    text = str(parsed.get("resume_content") or "")

    # 学历门槛：显式条件优先，否则不设限
    req_edu = 0
    for cond in job.get("conditions") or []:
        if isinstance(cond, dict) and str(cond.get("key", "")).strip() in ("学历", "education"):
            req_edu = _edu_level(str(cond.get("value")))
            break
    req_years = 0
    for cond in job.get("conditions") or []:
        if isinstance(cond, dict) and str(cond.get("key", "")).strip() in ("工作年限", "experience", "年限"):
            try:
                req_years = int(float(cond.get("value")))
            except (TypeError, ValueError):
                req_years = 0
            break

    edu_score, edu_note = _score_education(req_edu, _edu_level(parsed.get("education")))
    skill_score, hits, missing = _score_skills(req_skills, cand_skills, text)
    exp_score, exp_note = _score_experience(req_years, int(parsed.get("years_experience") or 0))
    proj_score, proj_hits = _score_project(job, text)
    other_score, filled = _score_other(parsed)
    ability_score, ability_rows = score_ability(job.get("ability_requirements"), abilities)

    dims = {
        "education": edu_score,
        "skills": skill_score,
        "experience": exp_score,
        "project": proj_score,
        "other": other_score,
    }
    if ability_score is not None:
        # 画像契合占用"档案完整度"的权重席位：岗位一旦设了基线，就该按能力判，不该按填得全不全判
        seat = weights.get("ability", weights.get("other", 0.0))
        weights["ability"] = seat
        weights["other"] = 0.0
        dims["ability"] = ability_score
    base = sum(dims[k] * weights.get(k, 0.0) for k in dims)

    hard_failed, fail_items = _hard_fail(job, parsed, hits, missing)
    if hard_failed:
        final = min(int(round(base * 0.55)), threshold - 1)
        final = max(final, 0)
    else:
        final = int(round(base))
    passed = final >= threshold and not hard_failed

    reason = _build_reason(
        passed=passed,
        final=final,
        threshold=threshold,
        fail_items=fail_items,
        edu_note=edu_note,
        edu_score=edu_score,
        hits=hits,
        req_skills=req_skills,
        skill_score=skill_score,
        exp_note=exp_note,
        exp_score=exp_score,
        proj_hits=proj_hits,
        filled=filled,
        ability_score=ability_score,
        ability_rows=ability_rows,
    )

    detail = {
        "conditions": [
            {
                "key": str(c.get("key")),
                "op": str(c.get("op", ">=")),
                "value": c.get("value"),
                "ok": not any(str(c.get("key")) in f for f in fail_items),
            }
            for c in (job.get("conditions") or [])
            if isinstance(c, dict)
        ],
        "dimensions": [
            {"key": k, "label": DIM_LABEL[k], "score": dims[k], "weight": weights.get(k, 0.0)}
            for k in dims
        ],
        "weights": weights,
        "threshold": threshold,
        "required_skills": req_skills,
        "hit_skills": hits,
        "missing_skills": missing,
        "hard_failed": hard_failed,
        "fail_items": fail_items,
        "base_score": round(base, 1),
        "ability_detail": ability_rows,
        "ability_used": ability_score is not None,
    }
    return Verdict(total_score=final, passed=passed, reason=reason, detail=detail)


def _build_reason(
    *,
    passed: bool,
    final: int,
    threshold: int,
    fail_items: list[str],
    edu_note: str,
    edu_score: float,
    hits: list[str],
    req_skills: list[str],
    skill_score: float,
    exp_note: str,
    exp_score: float,
    proj_hits: list[str],
    filled: int,
    ability_score: float | None = None,
    ability_rows: list[dict] | None = None,
) -> str:
    if not passed:
        parts = ["不匹配：" + "；".join(fail_items)] if fail_items else ["不匹配：综合分未达合格线"]
        if hits:
            parts.append(f"已命中技能 {'、'.join(hits[:4])}")
        if edu_note:
            parts.append(edu_note)
        parts.append(f"综合 {final} 分，未达合格线 {threshold}")
        return "；".join(parts) + "。"

    coverage = f"{len(hits)}/{len(req_skills)}" if req_skills else "—"
    pieces = [
        f"{edu_note}（{edu_score:.0f} 分）",
        f"技能命中 {'、'.join(hits[:4]) if hits else '无'}，覆盖率 {coverage}（{skill_score:.0f} 分）",
        f"{exp_note}（{exp_score:.0f} 分）",
    ]
    if proj_hits:
        pieces.append(f"简历出现岗位关键词 {'、'.join(proj_hits[:3])}")
    if ability_score is not None and ability_rows:
        weak = [r for r in ability_rows if r["ratio"] < 1][:2]
        tail = "、".join(f"{r['dim']} {r['actual']}/{r['baseline']:g}" for r in weak)
        pieces.append(f"画像契合 {ability_score:.0f} 分" + (f"（未达基线：{tail}）" if tail else "（各维均达基线）"))
    pieces.append(f"档案完整度 {filled}/6")
    return "；".join(pieces) + f"。综合 {final} 分，达到合格线 {threshold}。"


def keyword_tokens(text: str) -> list[str]:
    return re.findall(r"[\u4e00-\u9fa5]{2,4}|[A-Za-z]{2,}", text or "")
