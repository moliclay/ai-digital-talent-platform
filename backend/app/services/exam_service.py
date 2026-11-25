"""智能测评：题库 → 出卷 → 作答 → 自动评分 → 错题 → 复习计划。

评分策略：
- 单选/多选/填空：精确或集合比对，确定可复现；
- 简答：先按标准答案关键词覆盖率给分；配置了 AI 网关时再让模型复核（上限严格控制，
  且模型失败时保留关键词分，不因 AI 不可用而丢分）。
"""
from __future__ import annotations

import json
import re
from collections import Counter
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope, max_scope
from app.core.response import ApiError
from app.infrastructure.ai_gateway import gateway
from app.models.orm import (
    Exam, ExamAssignment, ExamSubmission, ParsedResume, Question, QuestionBank,
    ResumeFile, ReviewPlan, TalentProfile, WrongQuestion,
)

DIFFICULTY_WEIGHT = {"easy": 1, "medium": 2, "hard": 3}


def _norm(text: str | None) -> str:
    return re.sub(r"\s+", "", (text or "")).strip().lower()


def _split_set(text: str | None) -> set[str]:
    return {_norm(x) for x in re.split(r"[,，、;；\s]+", text or "") if _norm(x)}


# ---------------------------------------------------------------- 题库
def list_banks(db: Session, audience: str = "") -> list[dict]:
    query = select(QuestionBank).where(QuestionBank.status != "deleted")
    if audience:
        query = query.where(QuestionBank.audience == audience)
    banks = db.execute(query.order_by(QuestionBank.id)).scalars().all()
    counts = dict(db.execute(
        select(Question.bank_id, func.count()).where(Question.status == "active").group_by(Question.bank_id)
    ).all())
    return [
        {"id": b.id, "name": b.name, "description": b.description,
         "total_questions": int(counts.get(b.id, 0)), "status": b.status,
         "audience": b.audience or "candidate"}
        for b in banks
    ]


VALID_AUDIENCE = {"candidate", "employee"}


def create_bank(db: Session, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ApiError(400, "题库名称不能为空")
    audience = str(payload.get("audience") or "candidate").strip()
    if audience not in VALID_AUDIENCE:
        raise ApiError(400, f"受众只能是 {' / '.join(sorted(VALID_AUDIENCE))}")
    bank = QuestionBank(name=name, description=str(payload.get("description") or ""),
                        status="active", audience=audience)
    db.add(bank)
    db.commit()
    return {"id": bank.id, "name": bank.name, "audience": bank.audience}


def list_questions(db: Session, bank_id: int | None, page: int, page_size: int):
    query = select(Question).where(Question.status == "active")
    if bank_id:
        query = query.where(Question.bank_id == bank_id)
    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(query.order_by(Question.id).offset((page - 1) * page_size).limit(page_size)).scalars().all()
    return [
        {"id": q.id, "bank_id": q.bank_id, "type": q.question_type, "content": q.content,
         "options": q.options or [], "score": q.score, "difficulty": q.difficulty,
         "knowledge_point": q.knowledge_point, "knowledge_category": q.knowledge_category,
         "answer": q.answer}
        for q in rows
    ], int(total)


VALID_TYPES = {"single_choice", "multi_choice", "fill_blank", "essay"}


def create_question(db: Session, payload: dict) -> dict:
    bank_id = payload.get("bank_id")
    if not bank_id or db.get(QuestionBank, int(bank_id)) is None:
        raise ApiError(400, "题库不存在")
    qtype = str(payload.get("question_type") or "single_choice")
    if qtype not in VALID_TYPES:
        raise ApiError(400, f"不支持的题型：{qtype}")
    content = str(payload.get("content") or "").strip()
    if not content:
        raise ApiError(400, "题干不能为空")
    answer = str(payload.get("answer") or "").strip()
    if not answer:
        raise ApiError(400, "标准答案不能为空")
    try:
        score = int(payload.get("score") or 10)
    except (TypeError, ValueError):
        raise ApiError(400, "分值必须是整数")
    if not 1 <= score <= 100:
        raise ApiError(400, "分值需在 1–100 之间")

    q = Question(
        bank_id=int(bank_id),
        serial_no=str(payload.get("serial_no") or ""),
        question_type=qtype,
        content=content,
        options=payload.get("options") or [],
        answer=answer,
        score=score,
        scoring_standard=str(payload.get("scoring_standard") or ""),
        analysis=str(payload.get("analysis") or ""),
        knowledge_point=str(payload.get("knowledge_point") or ""),
        knowledge_category=str(payload.get("knowledge_category") or ""),
        knowledge_base_category=str(payload.get("knowledge_base_category") or ""),
        difficulty=str(payload.get("difficulty") or "medium"),
        subjective=qtype == "essay",
        operator=payload.get("operator") or "system",
        status="active",
    )
    db.add(q)
    db.flush()
    db.query(QuestionBank).filter(QuestionBank.id == q.bank_id).update(
        {QuestionBank.total_questions: int(db.execute(
            select(func.count()).select_from(Question).where(Question.bank_id == q.bank_id)
        ).scalar_one())}
    )
    db.commit()
    return {"id": q.id, "content": q.content, "score": q.score}


# ---------------------------------------------------------------- 出卷
def create_exam(db: Session, payload: dict) -> dict:
    name = str(payload.get("name") or "").strip()
    if not name:
        raise ApiError(400, "试卷名称不能为空")
    bank_ids = payload.get("bank_ids") or []
    if not isinstance(bank_ids, list) or not bank_ids:
        raise ApiError(400, "至少要选一个题库")
    try:
        want = int(payload.get("question_count") or 5)
        pass_score = int(payload.get("pass_score") or 60)
        duration = int(payload.get("duration_minutes") or 60)
    except (TypeError, ValueError):
        raise ApiError(400, "题数/合格分/时长必须是整数")

    pool = db.execute(
        select(Question).where(Question.bank_id.in_([int(b) for b in bank_ids]), Question.status == "active")
    ).scalars().all()
    if not pool:
        raise ApiError(400, "所选题库没有题目")
    # 确定式选题：按难度从易到难铺开，再按 id 补齐，便于复现
    ordered = sorted(pool, key=lambda q: (DIFFICULTY_WEIGHT.get(q.difficulty, 2), q.id))
    picked = ordered[:want]

    # 受众：显式传入优先，否则从第一个题库继承
    audience = str(payload.get("audience") or "").strip()
    if not audience:
        first_bank = db.get(QuestionBank, int(bank_ids[0]))
        audience = (first_bank.audience if first_bank else "candidate") or "candidate"
    if audience not in VALID_AUDIENCE:
        raise ApiError(400, f"受众只能是 {' / '.join(sorted(VALID_AUDIENCE))}")

    exam = Exam(
        name=name,
        category=str(payload.get("category") or "内测"),
        description=str(payload.get("description") or ""),
        bank_ids=[int(b) for b in bank_ids],
        question_ids=[q.id for q in picked],
        total_questions=len(picked),
        total_score=sum(q.score for q in picked),
        pass_score=pass_score,
        duration_minutes=duration,
        status="published",
        audience=audience,
    )
    db.add(exam)
    db.commit()
    return {
        "id": exam.id, "name": exam.name, "total_questions": exam.total_questions,
        "total_score": exam.total_score, "pass_score": exam.pass_score,
        "audience": exam.audience,
    }


def list_exams(db: Session, audience: str = "") -> list[dict]:
    query = select(Exam).order_by(Exam.id.desc())
    if audience:
        query = query.where(Exam.audience == audience)
    exams = db.execute(query).scalars().all()
    submitted = dict(db.execute(
        select(ExamSubmission.exam_id, func.count()).group_by(ExamSubmission.exam_id)
    ).all())
    return [
        {"id": e.id, "name": e.name, "category": e.category, "total_questions": e.total_questions,
         "total_score": e.total_score, "pass_score": e.pass_score, "duration_minutes": e.duration_minutes,
         "status": e.status, "submissions": int(submitted.get(e.id, 0)),
         "audience": e.audience or "candidate"}
        for e in exams
    ]


def get_paper(db: Session, exam_id: int) -> dict:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ApiError(404, "试卷不存在")
    ids = exam.question_ids or []
    questions = db.execute(select(Question).where(Question.id.in_(ids))).scalars().all()
    by_id = {q.id: q for q in questions}
    return {
        "id": exam.id, "name": exam.name, "total_score": exam.total_score,
        "pass_score": exam.pass_score, "duration_minutes": exam.duration_minutes,
        "questions": [
            {"id": q.id, "type": q.question_type, "content": q.content,
             "options": q.options or [], "score": q.score, "difficulty": q.difficulty}
            for q in (by_id[i] for i in ids if i in by_id)
        ],
    }


# ---------------------------------------------------------------- 评分
def _grade_objective(q: Question, answer: str) -> tuple[int, str]:
    if q.question_type == "single_choice":
        ok = _norm(answer) == _norm(q.answer)
    elif q.question_type == "multi_choice":
        ok = _split_set(answer) == _split_set(q.answer)
    elif q.question_type == "fill_blank":
        ok = _norm(q.answer) in _norm(answer) if _norm(answer) else False
    else:
        ok = False
    return (q.score if ok else 0), ("答案正确" if ok else f"标准答案：{q.answer}")


def _grade_essay(q: Question, answer: str) -> tuple[int, str]:
    keywords = [k for k in re.split(r"[，,、；;\s]+", q.answer or "") if len(k) >= 1]
    if not keywords:
        return 0, "缺少评分要点"
    hit = [k for k in keywords if k in (answer or "")]
    ratio = len(hit) / len(keywords)
    score = int(round(q.score * ratio))

    if gateway.available:
        res = gateway.chat(
            "你是严谨的阅卷老师。按评分要点给分，只输出 JSON："
            '{"score": 整数, "comment": "一句话点评"}。分数必须在 0 到满分之间。',
            json.dumps({
                "题干": q.content,
                "评分要点": q.answer,
                "考生答案": answer,
                "满分": q.score,
                "关键词命中": hit,
            }, ensure_ascii=False),
            max_tokens=200,
            json_mode=True,
        )
        data = res.json() if res.ok else None
        if data and isinstance(data.get("score"), (int, float)):
            ai_score = max(0, min(q.score, int(data["score"])))
            # 关键词与模型分取平均，避免模型给分虚高或离谱
            score = (score + ai_score) // 2
            return score, str(data.get("comment") or f"命中要点 {len(hit)}/{len(keywords)}")

    return score, f"命中要点 {len(hit)}/{len(keywords)}：{'、'.join(hit) or '无'}"


def submit(db: Session, user: CurrentUser, exam_id: int, candidate_name: str, answers: list[dict],
           assignment_id: int | None = None, parsed_resume_id: int | None = None) -> dict:
    exam = db.get(Exam, exam_id)
    if exam is None:
        raise ApiError(404, "试卷不存在")
    if not candidate_name.strip():
        raise ApiError(400, "考生姓名不能为空")

    # 绑定校验（需求④）：带了 assignment_id 就必须属于本卷且仍是 pending
    assignment = None
    if assignment_id:
        assignment = db.get(ExamAssignment, int(assignment_id))
        if assignment is None:
            raise ApiError(404, "测评任务不存在")
        if int(assignment.exam_id) != int(exam_id):
            raise ApiError(400, "测评任务与试卷不匹配")
        if assignment.status != "pending":
            raise ApiError(409, f"该测评任务已是 {assignment.status} 状态，不能重复提交")
        parsed_resume_id = parsed_resume_id or assignment.parsed_resume_id
        candidate_name = candidate_name.strip() or assignment.candidate_name

    ids = exam.question_ids or []
    questions = {q.id: q for q in db.execute(select(Question).where(Question.id.in_(ids))).scalars()}
    answer_map = {int(a.get("question_id")): str(a.get("answer") or "") for a in answers if a.get("question_id")}

    detail, total = [], 0
    for qid in ids:
        q = questions.get(qid)
        if q is None:
            continue
        raw = answer_map.get(qid, "")
        score, comment = _grade_essay(q, raw) if q.question_type == "essay" else _grade_objective(q, raw)
        total += score
        detail.append({
            "question_id": qid, "type": q.question_type, "content": q.content,
            "score": score, "max_score": q.score, "answer": raw,
            "standard": q.answer, "comment": comment, "analysis": q.analysis,
        })

    passed = total >= exam.pass_score
    submission = ExamSubmission(
        exam_id=exam_id,
        candidate_name=candidate_name.strip(),
        answers=answers,
        score=total,
        max_score=exam.total_score,
        pass_score=exam.pass_score,
        result="passed" if passed else "failed",
        recommendation="基础扎实，建议进入下一轮。" if passed else "存在明显缺口，建议复习后重考。",
        detail=detail,
        parsed_resume_id=parsed_resume_id,
    )
    db.add(submission)
    db.flush()

    # 回填绑定状态（需求④）
    if assignment is not None:
        assignment.status = "submitted"
        assignment.submission_id = submission.id

    wrong_count = 0
    for item in detail:
        if item["score"] >= item["max_score"]:
            continue
        wrong_count += 1
        wrong = WrongQuestion(
            exam_id=exam_id, submission_id=submission.id, question_id=item["question_id"],
            bank_id=questions[item["question_id"]].bank_id if item["question_id"] in questions else None,
            candidate_name=candidate_name.strip(),
            content=item["content"], question_type=item["type"],
            user_answer=item["answer"], standard_answer=item["standard"],
            analysis=item["analysis"], score=item["score"], max_score=item["max_score"],
            status="active",
        )
        db.add(wrong)
        db.flush()
        db.add(ReviewPlan(
            wrong_question_id=wrong.id, question_id=item["question_id"],
            candidate_name=candidate_name.strip(), content=item["content"],
            question_type=item["type"],
            review_time=datetime.now() + timedelta(days=1),
            reminder=True, status="scheduled",
        ))

    db.commit()
    return {
        "submission_id": submission.id, "score": total, "max_score": exam.total_score,
        "pass_score": exam.pass_score, "passed": passed, "wrong_count": wrong_count,
        "detail": detail,
    }


def list_submissions(db: Session, exam_id: int | None) -> list[dict]:
    query = select(ExamSubmission)
    if exam_id:
        query = query.where(ExamSubmission.exam_id == exam_id)
    subs = db.execute(query.order_by(ExamSubmission.id.desc()).limit(100)).scalars().all()
    exams = {e.id: e.name for e in db.execute(select(Exam)).scalars()}
    return [
        {"id": s.id, "exam_id": s.exam_id, "exam_name": exams.get(s.exam_id, ""),
         "candidate_name": s.candidate_name, "score": s.score, "max_score": s.max_score,
         "pass_score": s.pass_score, "result": s.result,
         "recommendation": s.recommendation}
        for s in subs
    ]


def get_submission(db: Session, submission_id: int) -> dict:
    s = db.get(ExamSubmission, submission_id)
    if s is None:
        raise ApiError(404, "答卷不存在")
    exam = db.get(Exam, s.exam_id)
    return {
        "id": s.id, "exam_name": exam.name if exam else "",
        "candidate_name": s.candidate_name, "score": s.score, "max_score": s.max_score,
        "pass_score": s.pass_score, "result": s.result, "recommendation": s.recommendation,
        "detail": s.detail or [],
        # 需求④：答卷归属哪份简历（NULL 表示历史数据，只按姓名）
        "parsed_resume_id": s.parsed_resume_id,
        "audience": (exam.audience if exam else "candidate") or "candidate",
    }


def list_wrong(db: Session, candidate_name: str | None) -> list[dict]:
    query = select(WrongQuestion).where(WrongQuestion.status == "active")
    if candidate_name:
        query = query.where(WrongQuestion.candidate_name == candidate_name)
    rows = db.execute(query.order_by(WrongQuestion.id.desc()).limit(200)).scalars().all()
    return [
        {"id": w.id, "candidate_name": w.candidate_name, "content": w.content,
         "type": w.question_type, "user_answer": w.user_answer, "standard_answer": w.standard_answer,
         "score": w.score, "max_score": w.max_score, "analysis": w.analysis}
        for w in rows
    ]


def list_review_plans(db: Session, candidate_name: str | None) -> list[dict]:
    query = select(ReviewPlan)
    if candidate_name:
        query = query.where(ReviewPlan.candidate_name == candidate_name)
    rows = db.execute(query.order_by(ReviewPlan.id.desc()).limit(200)).scalars().all()
    return [
        {"id": r.id, "candidate_name": r.candidate_name, "content": r.content, "type": r.question_type,
         "review_time": r.review_time.isoformat(sep=" ", timespec="minutes") if r.review_time else "",
         "status": r.status}
        for r in rows
    ]


# ---------------------------------------------------------------- 自适应组卷（千人千卷）
DIM_OF_CATEGORY = [
    (("算法", "模型", "机器学习", "深度学习", "大模型", "nlp", "框架", "python", "向量"), "技术深度"),
    (("工程", "部署", "性能", "架构", "运维", "测试", "数据库", "后端", "并发", "容器"), "工程能力"),
    (("业务", "产品", "需求", "行业", "指标", "分析", "方案"), "业务理解"),
    (("沟通", "协作", "团队", "管理", "项目", "跨部门"), "协作沟通"),
    (("学习", "成长", "复盘", "反思", "规划"), "成长性"),
]


def _dim_of(category: str, point: str = "") -> str | None:
    text = f"{category} {point}".lower()
    for words, dim in DIM_OF_CATEGORY:
        if any(w in text for w in words):
            return dim
    return None


def adaptive_paper(db: Session, payload: dict) -> dict:
    """按「错题知识点 + 画像最弱维度」组一份千人千卷，并给出选题理由。

    排序规则（可复现，无随机）：
      1) 出过错的知识点 +3；2) 属于画像最弱两维的题 +2；3) 没做过的题 +1；4) 难度阶梯补位。
    """
    name = str(payload.get("candidate_name") or "").strip()
    if not name:
        raise ApiError(400, "考生姓名不能为空")
    bank_ids = payload.get("bank_ids") or [b.id for b in db.execute(
        select(QuestionBank).where(QuestionBank.status == "active")).scalars()]
    bank_ids = [int(b) for b in bank_ids if str(b).isdigit()] or None
    if not bank_ids:
        raise ApiError(400, "没有可用题库")
    try:
        count = max(3, min(30, int(payload.get("count") or 8)))
        pass_score = int(payload.get("pass_score") or 60)
        duration = int(payload.get("duration_minutes") or 40)
    except (TypeError, ValueError):
        raise ApiError(400, "题数/合格分/时长必须是整数")

    pool = db.execute(
        select(Question).where(Question.bank_id.in_(bank_ids), Question.status == "active")
    ).scalars().all()
    if not pool:
        raise ApiError(400, "所选题库没有题目")

    # 1) 历史错题 → 薄弱知识点
    wrongs = db.execute(
        select(WrongQuestion).where(WrongQuestion.candidate_name == name, WrongQuestion.status == "active")
    ).scalars().all()
    wrong_qids = {w.question_id for w in wrongs if w.question_id}
    q_of_wrong = {q.id: q for q in db.execute(
        select(Question).where(Question.id.in_(wrong_qids))).scalars()} if wrong_qids else {}
    weak_points = Counter(
        q_of_wrong[qid].knowledge_point for qid in wrong_qids
        if qid in q_of_wrong and q_of_wrong[qid].knowledge_point
    )

    # 2) 画像最弱两维
    profile = db.execute(
        select(TalentProfile).where(TalentProfile.candidate_name == name)
    ).scalars().first()
    abilities = profile.abilities if profile and isinstance(profile.abilities, dict) else {}
    weak_dims = [d for d, _ in sorted(abilities.items(), key=lambda kv: kv[1])[:2]] if abilities else []

    scored = []
    for q in pool:
        score = 0
        reasons = []
        if q.knowledge_point and q.knowledge_point in weak_points:
            score += 3
            reasons.append(f"错题知识点「{q.knowledge_point}」")
        dim = _dim_of(q.knowledge_category or "", q.knowledge_point or "")
        if dim and dim in weak_dims:
            score += 2
            reasons.append(f"画像弱项「{dim}」")
        if q.id not in wrong_qids:
            score += 1
            reasons.append("未练过")
        scored.append((score, DIFFICULTY_WEIGHT.get(q.difficulty, 2), q, reasons))

    scored.sort(key=lambda x: (-x[0], x[1], x[2].id))
    picked = scored[:count]
    # 展示顺序：由易到难
    picked.sort(key=lambda x: (x[1], x[2].id))

    total_score = sum(q.score for _, _, q, _ in picked)
    exam = Exam(
        name=f"{name}·自适应测评（{datetime.now():%m-%d %H:%M}）",
        category=str(payload.get("category") or "自适应"),
        description="按错题知识点与画像弱项自动组卷",
        bank_ids=bank_ids,
        question_ids=[q.id for _, _, q, _ in picked],
        total_questions=len(picked),
        total_score=total_score,
        pass_score=min(pass_score, total_score) if total_score else pass_score,
        duration_minutes=duration,
        status="published",
    )
    db.add(exam)
    db.commit()

    rationale = {
        "weak_points": [{"point": p, "wrong_times": n} for p, n in weak_points.most_common(5)],
        "weak_dimensions": weak_dims,
        "rule": "错题知识点+3 / 画像弱项+2 / 未练过+1，同分按难度与题号排序",
        "covered": sum(1 for _, _, q, _ in picked if q.knowledge_point and q.knowledge_point in weak_points),
    }
    return {
        "exam": {
            "id": exam.id, "name": exam.name, "total_questions": exam.total_questions,
            "total_score": exam.total_score, "pass_score": exam.pass_score,
            "duration_minutes": exam.duration_minutes,
        },
        "rationale": rationale,
        "questions": [{
            "id": q.id, "content": q.content, "question_type": q.question_type,
            "score": q.score, "difficulty": q.difficulty,
            "knowledge_category": q.knowledge_category, "knowledge_point": q.knowledge_point,
            "reasons": reasons,
        } for _, _, q, reasons in picked],
    }
