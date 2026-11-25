"""规则解析器（MVP 不接大模型）。

输入 PDF/DOCX/TXT 文本层 → 结构化字段 + 命中证据。定位是"可核对 + 可人工修正"，
不承诺 PRD 的 99% 准确率（见方案 §11 风险 1）。图片/扫描件返回 need_ocr，不入匹配。
"""
from __future__ import annotations

import base64
import io
import re
import time
from dataclasses import dataclass, field

from app.core.config import settings
from app.infrastructure.ai_gateway import gateway
from app.infrastructure.skill_dict import extract_skills

EDU_LEVEL = {
    "博士": 5, "博士研究生": 5,
    "硕士": 4, "研究生": 4, "mba": 4,
    "本科": 3, "学士": 3, "bachelor": 3,
    "大专": 2, "专科": 2, "高职": 2,
    "高中": 1, "中专": 1,
}

_RE_PHONE = re.compile(r"(?<!\d)(1[3-9]\d{9})(?!\d)")
_RE_PHONE_LOOSE = re.compile(r"1[3-9]\d[\s\-]?\d{4}[\s\-]?\d{4}")
_RE_EMAIL = re.compile(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}")
_RE_NAME_LABEL = re.compile(r"(?:姓\s*名|Name)\s*[:：]\s*([\u4e00-\u9fa5]{2,4}|[A-Za-z][A-Za-z .]{1,28})")
_RE_CN_NAME = re.compile(r"^[\u4e00-\u9fa5]{2,4}$")
_RE_GENDER = re.compile(r"性\s*别\s*[:：]?\s*(男|女)")
_RE_AGE = re.compile(r"(?<!\d)(\d{2})\s*岁")
_RE_MAJOR = re.compile(r"专\s*业\s*[:：]\s*([^\s，,。;；|/]{2,20})")
_RE_MAJOR_TAIL = re.compile(r"([一-龥]{2,12})专业(?=[，,。;；、|/\s]|$)")
_RE_NAME_LEAD = re.compile(r"^\s*([一-龥]{2,4})\s*[，,（(]\s*(?:男|女)", re.M)
_RE_YEARS = [
    re.compile(r"(?:工作|从业|开发|算法|产品)?经[验历]\s*[:：]?\s*(\d{1,2})\s*年"),
    re.compile(r"(\d{1,2})\s*年(?:以上)?(?:工作|开发|从业|相关)?经[验历]"),
    re.compile(r"工作年限\s*[:：]?\s*(\d{1,2})"),
    re.compile(r"(\d{1,2})\s*年.{0,6}(?:经验|经历)"),
]

MAJOR_HINTS = [
    "计算机科学与技术", "软件工程", "人工智能", "数据科学", "信息管理", "电子信息",
    "数学与应用数学", "统计学", "自动化", "网络工程", "通信工程", "信息安全",
    "大数据", "物联网", "电子工程",
]

OCR_HINT = ("扫描件", "图片", "image/", "no text layer")


@dataclass
class ParseOutcome:
    ok: bool
    ai_fallback: bool = False
    ocr_used: bool = False
    need_ocr: bool = False
    reason: str = ""
    text: str = ""
    fields: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    duration_ms: int = 0
    confidence: float = 0.0


def extract_text(filename: str, data: bytes) -> tuple[str, bool]:
    """返回 (文本, 是否需要 OCR)。"""
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    if suffix == "pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(io.BytesIO(data))
            text = "\n".join((p.extract_text() or "") for p in reader.pages)
            return text.strip(), len(text.strip()) < 40
        except Exception as exc:  # 加密/损坏 PDF
            return "", True if "encrypt" in str(exc).lower() else False

    if suffix in ("docx", "doc"):
        if suffix == "doc":
            return "", True  # .doc 旧格式需 Word/OCR 链路，MVP 明确不支持
        try:
            import docx

            document = docx.Document(io.BytesIO(data))
            parts = [p.text for p in document.paragraphs]
            for table in document.tables:
                for row in table.rows:
                    parts.append("\t".join(c.text for c in row.cells))
            text = "\n".join(p for p in parts if p.strip())
            return text.strip(), len(text.strip()) < 20
        except Exception:
            return "", False

    if suffix in ("txt", "md", "csv"):
        for enc in ("utf-8", "gb18030", "utf-16"):
            try:
                return data.decode(enc).strip(), False
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore").strip(), False

    if suffix in ("png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"):
        return "", True

    return "", False


IMAGE_SUFFIX = {"png", "jpg", "jpeg", "bmp", "webp", "tif", "tiff"}
MAX_OCR_PAGES = 2

_OCR_PROMPT = (
    "这是一份简历的图片（可能是扫描件）。请做两件事："
    "1) 逐字转写可见文字；2) 抽取字段。只输出 JSON："
    '{"text":"简历全文","name":"","phone":"","email":"","gender":"男或女或空",'
    '"age":0,"education":"博士|硕士|本科|大专|高中","major":"",'
    '"years_experience":0,"skills":["技术名词"],"strengths":"一句话"}。'
    "要求：看不到的字段留空或 0，不要猜；education 只能取博士/硕士/本科/大专/高中；"
    "years_experience 是整数年。"
)


def _pdf_pages_to_png(data: bytes, pages: int = MAX_OCR_PAGES) -> list[bytes]:
    """扫描版 PDF → PNG（PyMuPDF 渲染，2 倍缩放保证清晰度）。"""
    try:
        import fitz  # PyMuPDF
    except Exception:
        return []
    out: list[bytes] = []
    try:
        doc = fitz.open(stream=data, filetype="pdf")
        for i in range(min(pages, doc.page_count)):
            pix = doc.load_page(i).get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
            out.append(pix.tobytes("png"))
        doc.close()
    except Exception:
        return out
    return out


def _vision_ocr(filename: str, data: bytes) -> tuple[dict, str] | None:
    """把图片/扫描件交给多模态模型，返回 (字段, 全文)；不可用时返回 None。"""
    if not gateway.available:
        return None
    suffix = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""

    images: list[tuple[bytes, str]] = []
    if suffix in IMAGE_SUFFIX:
        mime = "image/jpeg" if suffix in ("jpg", "jpeg") else f"image/{'png' if suffix == 'png' else 'png'}"
        images.append((data, mime))
    elif suffix == "pdf":
        images.extend([(png, "image/png") for png in _pdf_pages_to_png(data)])
    if not images:
        return None

    text_parts: list[str] = []
    merged: dict = {}
    for raw, mime in images:
        b64 = base64.b64encode(raw).decode()
        res = gateway.chat_vision(b64, _OCR_PROMPT, mime=mime,
                                  max_tokens=1200, timeout=settings.ai_vision_timeout)
        if not res.ok:
            continue
        payload = res.json()
        if not isinstance(payload, dict):
            continue
        if payload.get("text"):
            text_parts.append(str(payload["text"]))
        for key in ("name", "phone", "email", "gender", "education", "major", "strengths"):
            if payload.get(key) and not merged.get(key):
                merged[key] = str(payload[key]).strip()
        for key in ("age", "years_experience"):
            try:
                if payload.get(key) and not merged.get(key):
                    merged[key] = int(payload[key])
            except (TypeError, ValueError):
                continue
        if payload.get("skills"):
            merged["skills"] = list(dict.fromkeys((merged.get("skills") or []) + [str(x) for x in payload["skills"]]))

    if not merged and not text_parts:
        return None
    text = "\n".join(text_parts).strip()
    # 用规则再过一遍 OCR 文本，补模型漏掉的字段
    rule_fields, _ev = _extract_fields(text) if text else ({}, {})
    for key, val in rule_fields.items():
        if val and not merged.get(key):
            merged[key] = val
    return merged, text


def parse_resume(filename: str, data: bytes) -> ParseOutcome:
    started = time.perf_counter()
    text, need_ocr = extract_text(filename, data)

    if not text:
        ocr = _vision_ocr(filename, data) if need_ocr or filename.lower().rsplit(".", 1)[-1] in IMAGE_SUFFIX else None
        if ocr:
            fields, ocr_text = ocr
            if fields.get("education") == "研究生":
                fields["education"] = "硕士"
            skills = [str(x) for x in (fields.get("skills") or [])]
            for s_ in extract_skills(ocr_text):
                if s_ not in skills:
                    skills.append(s_)
            fields["skills"] = skills
            filled = sum(1 for k in ("name", "education", "years_experience") if fields.get(k)) + (1 if skills else 0)
            return ParseOutcome(
                ok=True,
                ocr_used=True,
                need_ocr=False,
                reason="扫描件/图片：多模态 OCR + 字段抽取",
                text=ocr_text,
                fields=fields,
                evidence={"ocr": "多模态模型", "chars": len(ocr_text)},
                duration_ms=int((time.perf_counter() - started) * 1000),
                confidence=round(min(0.8, 0.4 + filled * 0.1), 2),
            )
        return ParseOutcome(
            ok=False,
            need_ocr=need_ocr,
            reason="无可提取文本层，需 OCR 或人工录入" if need_ocr else "文件为空或格式不支持",
            duration_ms=int((time.perf_counter() - started) * 1000),
        )

    fields, evidence = _extract_fields(text)
    filled = sum(1 for k in ("name", "education", "years_experience") if fields.get(k)) + (
        1 if fields.get("skills") else 0
    )
    confidence = filled / 4

    ai_used = False
    # 规则抽不全时让模型兜底：只补空字段，不覆盖规则已确认的值
    needs_ai = (not fields.get("education")) or not fields.get("years_experience") or confidence < 0.75
    if needs_ai and gateway.available:
        ai_fields = _ai_extract(text)
        if ai_fields:
            ai_used = True
            for key in ("name", "phone", "email", "gender", "age", "education", "major"):
                if not fields.get(key) and ai_fields.get(key):
                    fields[key] = ai_fields[key]
                    evidence[key] = f"AI 兜底：{ai_fields[key]}"
            if not fields.get("years_experience") and ai_fields.get("years_experience"):
                try:
                    fields["years_experience"] = int(ai_fields["years_experience"])
                    evidence["years_experience"] = f"AI 兜底：{fields['years_experience']} 年"
                except (TypeError, ValueError):
                    pass
            extra = [s for s in (ai_fields.get("skills") or []) if isinstance(s, str)]
            if extra:
                merged = list(dict.fromkeys(list(fields.get("skills") or []) + extract_skills(" ".join(extra))))
                fields["skills"] = merged
                evidence["skills"] = evidence.get("skills", "") + f"；AI 补充 {len(extra)} 项"
            if ai_fields.get("strengths") and not fields.get("strengths"):
                fields["strengths"] = str(ai_fields["strengths"])[:200]
            filled = sum(1 for k in ("name", "education", "years_experience") if fields.get(k)) + (
                1 if fields.get("skills") else 0
            )
            confidence = filled / 4

    return ParseOutcome(
        ok=True,
        text=text,
        fields=fields,
        evidence=evidence,
        duration_ms=int((time.perf_counter() - started) * 1000),
        confidence=round(confidence, 2),
        ai_fallback=ai_used,
    )


def _ai_extract(text: str) -> dict | None:
    """让模型从简历正文抽字段，只输出 JSON。失败静默返回 None（由规则结果兜底）。"""
    snippet = text[:4000]
    res = gateway.chat(
        "你是简历解析器。从给定简历正文提取字段，只输出 JSON，不要解释、不要编造："
        '{"name":"","phone":"","email":"","gender":"","age":0,"education":"",'
        '"major":"","years_experience":0,"skills":[],"strengths":""}。'
        "education 只能是 博士/硕士/本科/大专/高中 之一；years_experience 是整数年；"
        "skills 最多 15 个，用简历里出现的原词。找不到的字段留空字符串或 0。",
        snippet,
        max_tokens=600,
        json_mode=True,
    )
    return res.json() if res.ok else None


def _extract_fields(text: str) -> tuple[dict, dict]:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    evidence: dict = {}

    # 姓名
    name = ""
    m = _RE_NAME_LABEL.search(text)
    if m:
        name = m.group(1).strip()
        evidence["name"] = m.group(0)[:40]
    if not name:
        for ln in lines[:6]:
            if _RE_CN_NAME.match(ln):
                name = ln
                evidence["name"] = f"首行姓名：{ln}"
                break
    if not name:
        m = _RE_NAME_LEAD.search(text[:200])
        if m:
            name = m.group(1)
            evidence["name"] = m.group(0)[:40]

    # 手机 / 邮箱
    phone = ""
    m = _RE_PHONE.search(text) or _RE_PHONE_LOOSE.search(text)
    if m:
        phone = re.sub(r"\D", "", m.group(0))[:11]
        evidence["phone"] = m.group(0)

    email = ""
    m = _RE_EMAIL.search(text)
    if m:
        email = m.group(0)
        evidence["email"] = email

    # 性别 / 年龄
    gender = ""
    m = _RE_GENDER.search(text)
    if m:
        gender = m.group(1)
        evidence["gender"] = m.group(0)
    age = None
    m = _RE_AGE.search(text)
    if m:
        age = int(m.group(1))
        evidence["age"] = m.group(0)

    # 学历：取出现过的最高学历
    edu, edu_level = "", 0
    low = text.lower()
    for word, level in EDU_LEVEL.items():
        if word in low and level > edu_level:
            edu, edu_level = word, level
            evidence["education"] = word
    if edu == "研究生":
        edu = "硕士"
    if edu == "博士研究生":
        edu = "博士"

    # 专业
    major = ""
    m = _RE_MAJOR.search(text) or _RE_MAJOR_TAIL.search(text)
    if m:
        major = m.group(1)
        evidence["major"] = m.group(0)
    if not major:
        for hint in MAJOR_HINTS:
            if hint in text:
                major = hint
                evidence["major"] = f"词表命中：{hint}"
                break

    # 工作年限：取所有命中里的最大值（简历常按段落重复描述）
    years = 0
    explicit = False
    for pattern in _RE_YEARS:
        for mm in pattern.finditer(text):
            val = int(mm.group(1))
            if 0 <= val <= (age or 60):
                explicit = True
                years = max(years, val)
                evidence["years_experience"] = mm.group(0)
    # 只有完全没写明年限时才用年龄估算；写"0 年"的应届生不能被估成 6 年
    if not explicit and age:
        years = max(0, min(age - 22, 20))
        evidence["years_experience"] = f"按年龄估算：{age} 岁"

    # 技能
    skills = extract_skills(text)
    if skills:
        evidence["skills"] = f"词典命中 {len(skills)} 项"

    # 优势：优先"优势/擅长/精通"所在行
    strengths = ""
    for ln in lines:
        if any(k in ln for k in ("优势", "擅长", "精通", "熟悉")):
            strengths = ln[:120]
            break
    if not strengths:
        strengths = "、".join(skills[:3]) + (f"，{years} 年相关经验" if years else "")

    return (
        {
            "name": name,
            "phone": phone,
            "email": email,
            "gender": gender,
            "age": age,
            "education": edu,
            "major": major,
            "skills": skills,
            "years_experience": years,
            "strengths": strengths,
        },
        evidence,
    )
