"""JD 文本 → 岗位条件（AI 抽取 + 规则兜底）。

设计原则：
- **只产出草稿**，不落库：HR 必须确认后走原有 `POST /job-profiles` 保存；
- **AI 不可用也能用**：规则版能抽出学历/年限/技能，权重与合格线给默认值；
- **字段受控**：条件 key / op / 权重范围都做白名单校验，模型写歪了直接丢弃并记 warning。
"""
from __future__ import annotations

import json
import re

from app.core.response import ApiError
from app.infrastructure.ai_gateway import gateway
from app.infrastructure.skill_dict import extract_skills

ALLOWED_KEYS = {"学历", "技能", "工作年限", "专业", "城市"}
ALLOWED_OPS = {">=", ">", "<=", "<", "==", "contains", "in"}
DEFAULT_WEIGHTS = {"education": 20, "skills": 40, "experience": 15, "project": 15, "other": 10}

_EDU_WORDS = ("博士", "硕士", "研究生", "本科", "学士", "大专", "专科", "高中")
_RE_EDU = re.compile(r"(博士|硕士|研究生|本科|学士|大专|专科|高中)(?:学历)?(?:及以上|以上|起)?")
_RE_YEARS = re.compile(r"(\d{1,2})\s*年(?:以上|及以上|起|\+)?")
_RE_TITLE = re.compile(r"(?:岗位|职位|岗位名称|招聘岗位)\s*[:：]\s*(.+)")
_EDU_NORM = {"研究生": "硕士", "学士": "本科", "专科": "大专"}


def _normalize_condition(raw: dict) -> dict | None:
    key = str(raw.get("key") or "").strip()
    op = str(raw.get("op") or "").strip()
    value = raw.get("value")
    if key not in ALLOWED_KEYS:
        return None
    if op not in ALLOWED_OPS:
        op = "contains" if key == "技能" else ">="
    if key == "技能":
        if isinstance(value, str):
            value = [v.strip() for v in re.split(r"[,，、;；/]", value) if v.strip()]
        if not isinstance(value, list) or not value:
            return None
        value = [str(v) for v in value][:12]
        op = "contains"
    elif key in ("工作年限",):
        try:
            value = int(float(value))
        except (TypeError, ValueError):
            return None
        value = max(0, min(30, value))
    elif key == "学历":
        value = str(value).strip()
        if value not in _EDU_WORDS:
            return None
        value = _EDU_NORM.get(value, value)
    else:
        value = str(value).strip()
        if not value:
            return None
    return {"key": key, "op": op, "value": value}


def _normalize_weights(raw: dict | None) -> dict[str, int]:
    weights = dict(DEFAULT_WEIGHTS)
    if isinstance(raw, dict):
        for k in weights:
            try:
                if k in raw:
                    weights[k] = max(0, min(100, int(float(raw[k]))))
            except (TypeError, ValueError):
                continue
    total = sum(weights.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    if total != 100:  # 归一化到 100，便于页面滑块直接显示
        weights = {k: round(v * 100 / total) for k, v in weights.items()}
        diff = 100 - sum(weights.values())
        if diff:
            top = max(weights, key=weights.get)
            weights[top] += diff
    return weights


def _rule_parse(text: str) -> dict:
    warnings: list[str] = []
    name = ""
    m = _RE_TITLE.search(text)
    if m:
        name = m.group(1).strip()[:60]
    if not name:
        first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
        name = first[:60]
        if name:
            warnings.append("岗位名取首行，请确认")

    conditions: list[dict] = []
    m = _RE_EDU.search(text)
    if m:
        conditions.append({"key": "学历", "op": ">=", "value": _EDU_NORM.get(m.group(1), m.group(1))})

    years = [int(x) for x in _RE_YEARS.findall(text)]
    if years:
        conditions.append({"key": "工作年限", "op": ">=", "value": max(years)})

    skills = extract_skills(text)
    if skills:
        conditions.append({"key": "技能", "op": "contains", "value": skills[:8]})
    else:
        warnings.append("未识别到技能要求，建议人工补充")

    return {
        "name": name,
        "conditions": conditions,
        "score_rules": {"weights": dict(DEFAULT_WEIGHTS)},
        "passing_threshold": 70,
        "warnings": warnings,
    }


def _ai_parse(text: str) -> tuple[dict | None, str]:
    if not gateway.available:
        return None, ""
    system = (
        "你是招聘需求结构化专家。从 JD 文本抽取岗位条件，只输出 JSON："
        '{"name":"岗位名","conditions":[{"key":"学历|技能|工作年限|专业|城市","op":">=|contains",'
        '"value":"值或技能数组"}],"weights":{"education":20,"skills":40,"experience":15,'
        '"project":15,"other":10},"passing_threshold":70,"notes":["不确定的点"]}。'
        "规则：学历只能取 博士/硕士/本科/大专/高中；技能用常见技术名词；权重合计 100；"
        "没写的项不要编，宁缺勿滥。"
    )
    res = gateway.chat(system, text[:4000], max_tokens=700, json_mode=True)
    if not res.ok:
        return None, res.error
    data = res.json()
    if not isinstance(data, dict):
        return None, "模型返回非 JSON"
    return data, ""


def parse_jd(text: str) -> dict:
    text = (text or "").strip()
    if len(text) < 10:
        raise ApiError(400, "JD 文本太短（至少 10 个字）")

    raw, ai_error = _ai_parse(text)
    warnings: list[str] = []
    source = "ai"
    if raw is None:
        raw = _rule_parse(text)
        source = "rule"
        warnings.extend(raw.get("warnings") or [])
        if ai_error:
            warnings.append(f"AI 不可用，已用规则解析：{ai_error[:80]}")

    conditions = []
    for c in (raw.get("conditions") or []):
        if isinstance(c, dict):
            norm = _normalize_condition(c)
            if norm:
                conditions.append(norm)
            else:
                warnings.append(f"丢弃无法识别的条件：{str(c)[:60]}")
    # AI 常漏项（实测：漏「5 年以上经验」）：用规则结果补齐 AI 没给出的 key，AI 的值优先
    if source == "ai":
        rule = _rule_parse(text)
        have = {c["key"] for c in conditions}
        filled = []
        for rc in rule["conditions"]:
            if rc["key"] not in have:
                conditions.append(rc)
                have.add(rc["key"])
                filled.append(rc["key"])
        if filled:
            warnings.append("规则补齐模型漏掉的项：" + "、".join(filled))
        if not conditions:
            conditions = rule["conditions"]
            source = "ai_rule"

    weights = _normalize_weights(raw.get("weights"))
    try:
        threshold = int(raw.get("passing_threshold") or 70)
    except (TypeError, ValueError):
        threshold = 70
    threshold = max(40, min(95, threshold))

    for note in (raw.get("notes") or [])[:5]:
        warnings.append(str(note)[:80])

    return {
        "source": source,
        "draft": {
            "name": str(raw.get("name") or "").strip()[:60] or "未命名岗位",
            "conditions": conditions,
            "score_rules": {"weights": weights},
            "passing_threshold": threshold,
            "ability_requirements": {},
        },
        "warnings": warnings,
        "ai_available": gateway.available,
    }
