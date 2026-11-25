"""题库文件导入：文件 → 文本 → AI/规则抽取 → 草稿 → 人工确认落库（需求⑥）。

三段式设计（不做"上传即入库"）：
1. `extract()`   —— 读文件成文本（txt/md/csv/docx/pdf/xlsx）
2. `draft()`     —— AI 优先、规则补空，产出草稿 + warnings，**不落库**
3. `confirm()`   —— 前端改过的草稿批量落库

为什么必须人工确认：AI 抽题一定会出错（漏答案、选项错位、多出题），
错了要能改；直接入库等于把脏数据写进生产题库。

降级：AI 不可用时 `source=rule`，格式规整的题库仍能导入。
"""
from __future__ import annotations

import io
import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.response import ApiError
from app.infrastructure.ai_gateway import gateway
from app.models.orm import Question, QuestionBank
from app.services.exam_service import create_question

MAX_TEXT = 60000            # 送模型的文本上限（分批后每批仍有字符保护，整体放宽到 6 万字）
MAX_QUESTIONS = 200         # 单次导入上限

SUPPORTED = {"txt", "md", "csv", "docx", "pdf", "xlsx"}

# 题型关键词 → 题型
TYPE_HINTS = {
    "single_choice": ("单选", "单项选择", "单选题"),
    "multi_choice": ("多选", "多项选择", "多选题"),
    "fill_blank": ("填空", "填空题"),
    "essay": ("简答", "问答", "论述", "简答题", "问答题"),
}

# 知识分类关键词 → 五维（与测评反哺同一套映射）
CATEGORY_HINTS = {
    "技术深度": ("算法", "模型", "深度学习", "框架", "transformer", "神经网络", "推理"),
    "工程能力": ("工程", "部署", "性能", "架构", "数据库", "并发", "缓存", "k8s", "容器"),
    "业务理解": ("业务", "产品", "需求", "指标", "分析", "转化", "漏斗", "客户"),
    "协作沟通": ("沟通", "协作", "团队", "管理", "项目", "冲突", "会议"),
    "成长性": ("学习", "成长", "复盘", "规划", "职业", "反思"),
}

_AI_PROMPT = (
    "你是题库录入助手。只做「结构化」，不新增、不改写、不补题。\n"
    "原文有几道题就输出几道。找不到答案就 answer 留空，不要猜。\n"
    "只输出 JSON：\n"
    '{"questions":[{"question_type":"single_choice|multi_choice|fill_blank|essay",'
    '"content":"题干原文","options":["A. ...","B. ..."],"answer":"A 或 A,B 或填空文本",'
    '"score":0,"knowledge_point":"","knowledge_category":"","difficulty":"easy|medium|hard",'
    '"analysis":""}]}'
)


def _suffix(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


# ---------------------------------------------------------------- 1. 抽取文本
def extract(filename: str, data: bytes) -> tuple[str, str]:
    """返回 (文本, 警告)。不支持的类型抛 400。"""
    suffix = _suffix(filename)
    if suffix not in SUPPORTED:
        raise ApiError(400, f"不支持的格式：.{suffix}（支持 {'/'.join(sorted(SUPPORTED))}）")

    if suffix in ("txt", "md", "csv"):
        for enc in ("utf-8", "gb18030", "utf-16"):
            try:
                return data.decode(enc).strip(), ""
            except UnicodeDecodeError:
                continue
        return data.decode("utf-8", errors="ignore").strip(), "编码无法识别，已按 UTF-8 忽略错误字符"

    if suffix == "docx":
        try:
            import docx
        except ImportError:
            raise ApiError(500, "缺少 python-docx")
        document = docx.Document(io.BytesIO(data))
        parts = [p.text for p in document.paragraphs]
        for table in document.tables:
            for row in table.rows:
                parts.append("\t".join(c.text for c in row.cells))
        text = "\n".join(p for p in parts if p.strip())
        return text, "" if text else "文档里没有可读文本"

    if suffix == "pdf":
        try:
            from pypdf import PdfReader
        except ImportError:
            raise ApiError(500, "缺少 pypdf")
        reader = PdfReader(io.BytesIO(data))
        text = "\n".join((p.extract_text() or "") for p in reader.pages).strip()
        warn = ""
        if len(text) < 40:
            warn = "PDF 没有文本层（可能是扫描件），本期不支持扫描件题库导入"
        return text, warn

    if suffix == "xlsx":
        try:
            import openpyxl
        except ImportError:
            raise ApiError(500, "缺少 openpyxl（请先 pip install openpyxl）")
        wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
        lines: list[str] = []
        for ws in wb.worksheets:
            for row in ws.iter_rows(values_only=True):
                cells = ["" if c is None else str(c).strip() for c in row]
                if any(cells):
                    lines.append("\t".join(cells))
        text = "\n".join(lines)
        return text, "xlsx 已按行转成制表符分隔文本，AI 抽取效果取决于表头是否清晰"

    return "", ""


# ---------------------------------------------------------------- 2a. AI 抽取
# 单次 AI 调用的输出 token 与耗时成正比（实测 deepseek-v4.1-flash：
# 20 题 ≈ 2700 tokens / 30s，200 题 ≈ 14000 tokens / 120s，必然超时）。
# 因此按题号把长文本切成小批，逐批调用再合并——单批失败只影响那一批。
AI_BATCH_QUESTIONS = 20     # 每批最多多少题
AI_BATCH_CHARS = 3000       # 每批最多多少字符（防止无题号的超长文本）
AI_BATCH_MAX_TOKENS = 3000  # 单批输出上限（20 题 JSON 约 2700 tokens）


def _split_into_batches(text: str) -> list[str]:
    """按「1. / 2. / 3.」题号把文本切成多批，每批不超过 AI_BATCH_QUESTIONS 题。

    找不到题号时（格式不规范），退化为按字符数硬切，并尽量在换行处断开。
    """
    # 题号行：行首可选「第」，1-3 位数字，后跟 . 、 ． )
    num_re = re.compile(r"^\s*(?:第\s*)?(\d{1,3})\s*[.、．)]", re.M)
    marks = [m.start() for m in num_re.finditer(text)]

    if len(marks) >= 2:
        # 有题号：按题号边界切
        batches, start, count = [], marks[0], 0
        # 题号之前的开头内容（说明文字）并入第一批
        head = text[:marks[0]].strip()
        for i, pos in enumerate(marks):
            count += 1
            if count >= AI_BATCH_QUESTIONS or i == len(marks) - 1:
                end = marks[i + 1] if i + 1 < len(marks) else len(text)
                chunk = text[start:end].strip()
                if chunk:
                    batches.append((head + "\n" + chunk).strip() if start == marks[0] and head else chunk)
                start = end
                count = 0
        return batches

    # 无题号：按字符数硬切，尽量在换行处断
    batches, pos = [], 0
    while pos < len(text):
        end = min(pos + AI_BATCH_CHARS, len(text))
        if end < len(text):
            nl = text.rfind("\n", pos, end)
            if nl > pos + AI_BATCH_CHARS // 2:
                end = nl + 1
        chunk = text[pos:end].strip()
        if chunk:
            batches.append(chunk)
        pos = end
    return batches


def _ai_draft(text: str) -> tuple[list[dict] | None, str]:
    """分批调用 AI 抽取题目。全部批次失败才返回 None；部分失败在错误信息里说明。"""
    if not gateway.available:
        return None, "AI 未启用"

    batches = _split_into_batches(text[:MAX_TEXT])
    if not batches:
        return None, "没有可送入模型的文本"

    collected: list[dict] = []
    errors: list[str] = []
    for idx, batch in enumerate(batches, 1):
        res = gateway.chat(_AI_PROMPT, batch, max_tokens=AI_BATCH_MAX_TOKENS, json_mode=True)
        if not res.ok:
            errors.append(f"第{idx}批：{res.error or 'AI 调用失败'}")
            continue
        body = res.json()
        if not isinstance(body, dict):
            errors.append(f"第{idx}批：AI 返回不是 JSON 对象")
            continue
        items = body.get("questions")
        if not isinstance(items, list):
            errors.append(f"第{idx}批：AI 返回缺少 questions 数组")
            continue
        collected.extend(i for i in items if isinstance(i, dict))

    if not collected:
        return None, "；".join(errors) if errors else "AI 未返回任何题目"

    note = ""
    if errors:
        note = f"（{len(errors)}/{len(batches)} 批失败：" + "；".join(errors[:3]) + "）"
    return collected, note


# ---------------------------------------------------------------- 2b. 规则抽取
_NUM = re.compile(r"^\s*(?:第?\s*)?(\d{1,3})\s*[.、．)]\s*(.*)$")
_OPTION = re.compile(r"^\s*([A-Ha-h])\s*[.、．)]\s*(.*)$")
_ANSWER = re.compile(r"^\s*(?:答案|参考答案|正确答案)\s*[:：]\s*(.+)$")
_ANALYSIS = re.compile(r"^\s*(?:解析|说明)\s*[:：]\s*(.+)$")
_TYPE_LINE = re.compile(r"^\s*[【\[]?\s*(单选|多选|填空|简答|问答|论述)(?:题)?\s*[】\]]?\s*$")


def _rule_draft(text: str) -> list[dict]:
    """按「1. 题干 / A. 选项 / 答案：X」切分。格式不规整时尽力而为。"""
    lines = [ln.rstrip() for ln in text.splitlines()]
    items: list[dict] = []
    cur: dict | None = None
    pending_type = ""

    def flush() -> None:
        nonlocal cur
        if cur and cur.get("content"):
            items.append(cur)
        cur = None

    for raw in lines:
        line = raw.strip()
        if not line:
            continue

        m_type = _TYPE_LINE.match(line)
        if m_type:
            word = m_type.group(1)
            pending_type = next(
                (k for k, hints in TYPE_HINTS.items() if any(w in word for w in hints)),
                "single_choice",
            )
            continue

        m_num = _NUM.match(line)
        if m_num:
            # 题号行一律开新题：即使题干为空也要 flush，否则空题号会被并进上一题
            flush()
            cur = {"question_type": pending_type or "single_choice", "content": m_num.group(2).strip(),
                   "options": [], "answer": "", "score": 0, "analysis": "",
                   "knowledge_point": "", "knowledge_category": ""}
            pending_type = ""
            continue

        if cur is None:
            continue

        m_opt = _OPTION.match(line)
        if m_opt:
            cur["options"].append(f"{m_opt.group(1).upper()}. {m_opt.group(2).strip()}")
            continue

        m_ans = _ANSWER.match(line)
        if m_ans:
            cur["answer"] = m_ans.group(1).strip()
            continue

        m_ana = _ANALYSIS.match(line)
        if m_ana:
            cur["analysis"] = m_ana.group(1).strip()
            continue

        # 续行：并入题干
        cur["content"] = (cur["content"] + " " + line).strip()

    flush()
    return items


# ---------------------------------------------------------------- 2c. 校验
_DEFAULT_SCORE = {"single_choice": 10, "multi_choice": 10, "fill_blank": 10, "essay": 20}
_ANSWER_LETTER = re.compile(r"\b([A-H])\b")


def _guess_category(text: str) -> str:
    lowered = (text or "").lower()
    best, best_hits = "", 0
    for dim, words in CATEGORY_HINTS.items():
        hits = sum(1 for w in words if w in lowered)
        if hits > best_hits:
            best, best_hits = dim, hits
    return best


def _validate(raw_items: list[dict]) -> tuple[list[dict], list[str]]:
    """统一校验：丢空题干、降级选项不足、标 needs_review、补默认分与分类。"""
    out: list[dict] = []
    warnings: list[str] = []

    for idx, item in enumerate(raw_items[:MAX_QUESTIONS], start=1):
        content = str(item.get("content") or "").strip()
        if not content:
            warnings.append(f"第 {idx} 题题干为空，已丢弃")
            continue

        qtype = str(item.get("question_type") or "single_choice").strip()
        if qtype not in _DEFAULT_SCORE:
            qtype = "single_choice"
            warnings.append(f"第 {idx} 题题型无法识别，按单选题处理")

        options = item.get("options")
        options = [str(o).strip() for o in options] if isinstance(options, list) else []
        options = [o for o in options if o]

        if qtype in ("single_choice", "multi_choice") and len(options) < 2:
            qtype = "fill_blank"
            warnings.append(f"第 {idx} 题选项少于 2 个，已按填空题处理")

        answer = str(item.get("answer") or "").strip()
        needs_review = False
        if qtype in ("single_choice", "multi_choice") and answer:
            valid = {chr(65 + i) for i in range(len(options))}
            letters = {m.upper() for m in _ANSWER_LETTER.findall(answer)}
            if letters:
                # 有字母但不在选项范围内 → 标人工核对
                if not (letters & valid):
                    needs_review = True
                    warnings.append(f"第 {idx} 题答案「{answer}」不在选项范围内，请人工核对")
            elif answer:
                # 完全没有字母（如 "Z" / 中文）→ 也标人工核对
                needs_review = True
                warnings.append(f"第 {idx} 题答案「{answer}」不是选项字母，请人工核对")

        score = item.get("score")
        try:
            score = int(score or 0)
        except (TypeError, ValueError):
            score = 0
        if score <= 0:
            score = _DEFAULT_SCORE[qtype]

        difficulty = str(item.get("difficulty") or "medium").strip()
        if difficulty not in ("easy", "medium", "hard"):
            difficulty = "medium"

        category = str(item.get("knowledge_category") or "").strip()
        if not category:
            category = _guess_category(content + " " + " ".join(options))

        out.append({
            "question_type": qtype,
            "content": content,
            "options": options,
            "answer": answer,
            "score": score,
            "knowledge_point": str(item.get("knowledge_point") or "").strip(),
            "knowledge_category": category,
            "difficulty": difficulty,
            "analysis": str(item.get("analysis") or "").strip(),
            "needs_review": needs_review,
        })

    return out, warnings


def _xlsx_rows(data: bytes) -> list[list[str]]:
    """读 xlsx 成二维字符串数组。"""
    try:
        import openpyxl
    except ImportError:
        raise ApiError(500, "缺少 openpyxl（请先 pip install openpyxl）")
    wb = openpyxl.load_workbook(io.BytesIO(data), data_only=True)
    rows: list[list[str]] = []
    for ws in wb.worksheets:
        for row in ws.iter_rows(values_only=True):
            cells = ["" if c is None else str(c).strip() for c in row]
            if any(cells):
                rows.append(cells)
    return rows


# 表头别名 → 字段
_HEADER_ALIASES = {
    "question_type": ("题型", "类型", "type"),
    "content": ("题干", "题目", "问题", "content", "question"),
    "answer": ("答案", "正确答案", "answer"),
    "score": ("分值", "分数", "score"),
    "difficulty": ("难度", "difficulty"),
    "knowledge_category": ("分类", "知识分类", "维度", "category"),
    "knowledge_point": ("知识点", "考点", "knowledge_point"),
    "analysis": ("解析", "说明", "analysis"),
}
_OPTION_HEADERS = ("选项a", "选项b", "选项c", "选项d", "选项e", "选项f",
                   "a", "b", "c", "d", "e", "f", "optiona", "optionb")


def _type_from_word(word: str) -> str:
    word = (word or "").strip()
    for qtype, hints in TYPE_HINTS.items():
        if any(h in word for h in hints):
            return qtype
    return "single_choice"


def _xlsx_draft(rows: list[list[str]]) -> list[dict]:
    """按表头识别列，把表格转成题目列表。表头认不出时退回按行拼文本。"""
    if not rows:
        return []

    header = [c.strip().lower() for c in rows[0]]
    col_map: dict[str, int] = {}
    option_cols: list[tuple[str, int]] = []   # (字母, 列号)

    for idx, name in enumerate(header):
        for field, aliases in _HEADER_ALIASES.items():
            if any(alias.lower() in name for alias in aliases):
                col_map.setdefault(field, idx)
                break
        for letter in "abcdef":
            if name in (f"选项{letter}", letter, f"option{letter}"):
                option_cols.append((letter.upper(), idx))
                break

    # 表头里没有「题干」列 → 认不出结构，退回按行拼接
    if "content" not in col_map:
        lines = ["\t".join(r) for r in rows]
        return _rule_draft("\n".join(lines))

    items: list[dict] = []
    for row in rows[1:]:
        def cell(field: str) -> str:
            idx = col_map.get(field)
            return row[idx].strip() if idx is not None and idx < len(row) else ""

        content = cell("content")
        if not content:
            continue

        options = []
        for letter, idx in sorted(option_cols, key=lambda x: x[0]):
            if idx < len(row) and row[idx].strip():
                options.append(f"{letter}. {row[idx].strip()}")

        answer = cell("answer")
        # 答案若写成 "A" / "A,B" 原样保留；若写成选项文本，转成字母
        if answer and not re.fullmatch(r"[A-Ha-h](?:\s*[,，、]\s*[A-Ha-h])*", answer):
            hit = next((letter for letter, _i in option_cols
                        if any(o.endswith(answer) for o in options if o.startswith(letter))), "")
            if hit:
                answer = hit

        score_raw = cell("score")
        try:
            score = int(float(score_raw)) if score_raw else 0
        except ValueError:
            score = 0

        items.append({
            "question_type": _type_from_word(cell("question_type")),
            "content": content,
            "options": options,
            "answer": answer,
            "score": score,
            "knowledge_point": cell("knowledge_point"),
            "knowledge_category": cell("knowledge_category"),
            "difficulty": cell("difficulty") or "medium",
            "analysis": cell("analysis"),
        })
    return items


# ---------------------------------------------------------------- 2. 生成草稿
def draft(db: Session, bank_id: int, filename: str, data: bytes) -> dict:
    bank = db.get(QuestionBank, int(bank_id))
    if bank is None:
        raise ApiError(404, "题库不存在")

    suffix = _suffix(filename)
    if suffix not in SUPPORTED:
        raise ApiError(400, f"不支持的格式：.{suffix}（支持 {'/'.join(sorted(SUPPORTED))}）")

    # xlsx 走结构化解析（表格是「列」结构，按行切分读不懂）
    if suffix == "xlsx":
        rows = _xlsx_rows(data)
        text = "\n".join("\t".join(r) for r in rows)
        ai_items, ai_error = _ai_draft(text)
        table_items = _xlsx_draft(rows)
        rule_items = table_items
        warn = "xlsx 已按表头识别列结构" if table_items else "xlsx 表头无法识别，已退回按行解析"
    else:
        text, warn = extract(filename, data)
        ai_items, ai_error = _ai_draft(text) if text.strip() else (None, "文件为空")
        rule_items = _rule_draft(text)

    if not text.strip():
        raise ApiError(400, warn or "文件里没有可读文本")

    if ai_items:
        source = "ai"
        items = ai_items
    elif rule_items:
        source = "rule"
        items = rule_items
    else:
        source = "rule"
        items = []
        warn = (warn + "；" if warn else "") + "未能识别出任何题目，请检查文件格式（建议「1. 题干 / A. B. C. D. / 答案：X」）"

    validated, warnings = _validate(items)
    if warn:
        warnings.insert(0, warn)
    if ai_error:
        if ai_items:
            # 部分批次失败：AI 仍参与了，但要让用户知道有几批没成功
            warnings.insert(0, f"AI 分批抽取{ai_error}")
        else:
            warnings.insert(0, f"AI 未参与（{ai_error}），已用规则解析")

    return {
        "source": source,
        "bank_id": int(bank_id),
        "bank_name": bank.name,
        "filename": filename,
        "parsed_count": len(validated),
        "draft": validated,
        "warnings": warnings,
        "text_preview": text[:200],
        "text_length": len(text),
        "ai_available": gateway.available,
    }


# ---------------------------------------------------------------- 3. 确认落库
def confirm(db: Session, bank_id: int, items: list[dict]) -> dict:
    bank = db.get(QuestionBank, int(bank_id))
    if bank is None:
        raise ApiError(404, "题库不存在")
    if not isinstance(items, list) or not items:
        raise ApiError(400, "草稿为空，没有可导入的题目")

    created, skipped, failed = 0, 0, []
    existing = {
        q.content.strip()
        for q in db.execute(select(Question).where(Question.bank_id == int(bank_id))).scalars()
    }

    for idx, item in enumerate(items, start=1):
        content = str(item.get("content") or "").strip()
        if not content:
            skipped += 1
            continue
        if content in existing:
            skipped += 1     # 同题库内题干重复 → 跳过（幂等）
            continue
        try:
            create_question(db, {
                "bank_id": int(bank_id),
                "question_type": item.get("question_type") or "single_choice",
                "content": content,
                "options": item.get("options") or [],
                "answer": item.get("answer") or "",
                "score": item.get("score") or _DEFAULT_SCORE.get(item.get("question_type"), 10),
                "difficulty": item.get("difficulty") or "medium",
                "knowledge_point": item.get("knowledge_point") or "",
                "knowledge_category": item.get("knowledge_category") or "",
                "analysis": item.get("analysis") or "",
            })
            existing.add(content)
            created += 1
        except Exception as exc:  # 单题失败不影响其余
            failed.append({"index": idx, "content": content[:40], "reason": str(exc)[:120]})

    bank.total_questions = len(db.execute(
        select(Question).where(Question.bank_id == int(bank_id), Question.status == "active")
    ).scalars().all())
    db.commit()
    return {"created": created, "skipped": skipped, "failed": failed,
            "failed_count": len(failed), "bank_total": bank.total_questions}
