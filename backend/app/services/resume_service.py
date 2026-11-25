"""简历域服务：上传 → 队列 → 解析 → 结果落库 → 人工修正。

并发与幂等（dev-god 后端规则）：
- 认领任务用 `FOR UPDATE SKIP LOCKED` 条件更新，检查影响行数，天然支持多消费者；
- 同一简历重复解析时覆盖 parsed_resumes 而不是插入新行，避免匹配出现重复候选人。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, apply_scope
from app.core.response import ApiError
from app.models.orm import (
    ParseLog, ParseTask, ParsedResume, ResumeFile,
)
from app.infrastructure.storage import get_storage
from app.services.identity_service import reconcile_identity, siblings_of
from app.services.parser_service import parse_resume

ALLOWED_SUFFIX = {"pdf", "docx", "doc", "txt", "md", "png", "jpg", "jpeg", "webp", "tif", "tiff"}


def _suffix(filename: str) -> str:
    return filename.lower().rsplit(".", 1)[-1] if "." in filename else ""


def upload(db: Session, user: CurrentUser, files: list[tuple[str, bytes, str]], job_profile_id: int | None,
           project_demand_id: int | None, project_name: str) -> dict:
    if not files:
        raise ApiError(400, "简历文件为空")

    storage = get_storage()
    accepted, rejected = [], []
    for filename, data, content_type in files:
        if _suffix(filename) not in ALLOWED_SUFFIX:
            rejected.append({"filename": filename, "reason": "不支持的格式"})
            continue
        if not data:
            rejected.append({"filename": filename, "reason": "空文件"})
            continue

        key, size = storage.save(filename, data)
        resume = ResumeFile(
            filename=filename,
            object_key=key,
            status="waiting",
            content_type=content_type or "",
            size_bytes=size,
            attachment_url=storage.url_of(key),
            project_demand_id=project_demand_id,
            job_profile_id=job_profile_id,
            project_name=project_name,
            position="",
            dept_id=user.department_id,
            created_by=user.id,
        )
        db.add(resume)
        db.flush()
        db.add(ParseTask(resume_id=resume.id, status="waiting", priority=0, attempts=0))
        accepted.append({"id": resume.id, "filename": filename, "size_bytes": size})

    db.commit()
    return {"accepted": len(accepted), "rejected": len(rejected), "items": accepted}


def queue_status(db: Session, user: CurrentUser) -> dict:
    query = apply_scope(select(ResumeFile), ResumeFile.dept_id, ResumeFile.created_by, user)
    sub = query.subquery()
    rows = db.execute(
        select(sub.c.status, func.count()).group_by(sub.c.status)
    ).all()
    counts = {"waiting": 0, "parsing": 0, "completed": 0, "failed": 0, "need_ocr": 0}
    for status, count in rows:
        counts[status] = counts.get(status, 0) + int(count)

    tasks = db.execute(
        select(ParseTask, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParseTask.resume_id)
        .where(ParseTask.status.in_(["waiting", "parsing", "failed", "need_ocr"]))
        .order_by(ParseTask.priority.desc(), ParseTask.id.asc())
        .limit(50)
    ).all()
    visible = [
        {
            "task_id": t.id,
            "resume_id": f.id,
            "filename": f.filename,
            "status": t.status,
            "attempts": t.attempts,
            "error": t.error_message,
            "created_at": t.created_at.isoformat(sep=" ", timespec="seconds") if t.created_at else "",
        }
        for t, f in tasks
        if _visible(user, f)
    ]
    return {"counts": counts, "tasks": visible}


def _visible(user: CurrentUser, file: ResumeFile) -> bool:
    scope = user.scope_of("resume")
    if scope == "all":
        return True
    if scope == "dept":
        return file.dept_id == user.department_id
    return file.created_by == user.id


def _filename_of(db: Session, parsed: ParsedResume) -> str:
    file = db.get(ResumeFile, parsed.resume_id)
    return file.filename if file else ""


def brief_of(parsed: ParsedResume, file: ResumeFile | None, user: CurrentUser | None = None) -> dict:
    """简历摘要：凡是"返回一份简历"的地方都用这个。

    - `parsed_resume_id` 是前端调 `GET /api/resumes/{id}` 的唯一入口；
    - `accessible=false` 表示当前用户无权打开详情（语义检索/查重会把越权项标出来而不是藏掉，
      否则用户会以为系统算错了）；
    - 技能拆成 `skills_top`（前 5）与 `skills_count`，列表里不必塞 20 多项。
    """
    skills = parsed.skills if isinstance(parsed.skills, list) else []
    return {
        "parsed_resume_id": int(parsed.id),
        "resume_file_id": int(parsed.resume_id),
        "name": parsed.name or "",
        "education": parsed.education or "",
        "major": parsed.major or "",
        "years_experience": int(parsed.years_experience or 0),
        "skills_top": [str(s) for s in skills[:5]],
        "skills_count": len(skills),
        "filename": file.filename if file else "",
        "created_at": parsed.created_at.isoformat(sep=" ", timespec="seconds") if parsed.created_at else "",
        "accessible": True if (user is None or file is None) else _visible(user, file),
    }


def briefs_by_ids(db: Session, ids: list[int], user: CurrentUser | None = None) -> dict[int, dict]:
    """批量版 `brief_of`：一次查询，避免逐条 N+1。返回 {parsed_resume_id: brief}。"""
    clean = [int(i) for i in ids if i]
    if not clean:
        return {}
    rows = db.execute(
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ParsedResume.id.in_(clean))
    ).all()
    return {int(p.id): brief_of(p, f, user) for p, f in rows}


def claim_next(db: Session, user: CurrentUser) -> int | None:
    """原子认领：只有把 status 从 waiting 改成 parsing 成功的那一个消费者能拿到任务。"""
    stmt = (
        select(ParseTask.id)
        .where(ParseTask.status == "waiting")
        .order_by(ParseTask.priority.desc(), ParseTask.id.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    task_id = db.execute(stmt).scalar_one_or_none()
    if task_id is None:
        return None

    affected = db.execute(
        ParseTask.__table__.update()
        .where(ParseTask.id == task_id, ParseTask.status == "waiting")
        .values(status="parsing", attempts=ParseTask.attempts + 1)
    ).rowcount
    if affected != 1:
        db.rollback()
        return None
    db.commit()
    return task_id


def process_task(db: Session, task_id: int) -> dict:
    task = db.get(ParseTask, task_id)
    if task is None:
        raise ApiError(404, "任务不存在")
    file = db.get(ResumeFile, task.resume_id)
    if file is None:
        task.status = "failed"
        task.error_message = "简历文件记录缺失"
        db.commit()
        raise ApiError(404, "简历文件记录缺失")

    started = datetime.now()
    try:
        data = get_storage().path_of(file.object_key).read_bytes()
    except Exception as exc:
        _fail(db, task, file, f"读取文件失败：{exc}", started)
        return {"task_id": task.id, "status": "failed", "reason": str(exc)}

    outcome = parse_resume(file.filename, data)

    if not outcome.ok:
        status = "need_ocr" if outcome.need_ocr else "failed"
        task.status = status
        task.error_message = outcome.reason
        file.status = status
        db.add(ParseLog(
            resume_id=file.id, task_id=task.id, status=status,
            message=outcome.reason, duration_ms=outcome.duration_ms,
        ))
        db.commit()
        return {"task_id": task.id, "status": status, "reason": outcome.reason}

    fields = outcome.fields
    parsed = db.execute(
        select(ParsedResume).where(ParsedResume.resume_id == file.id)
    ).scalar_one_or_none()
    if parsed is None:
        parsed = ParsedResume(resume_id=file.id)
        db.add(parsed)

    parsed.project_demand_id = file.project_demand_id or 0
    parsed.job_profile_id = file.job_profile_id or 0
    parsed.name = fields.get("name") or file.filename.rsplit(".", 1)[0][:60]
    parsed.phone = fields.get("phone") or None
    parsed.email = fields.get("email") or None
    parsed.gender = fields.get("gender") or None
    parsed.age = fields.get("age")
    parsed.education = fields.get("education") or None
    parsed.major = fields.get("major") or None
    parsed.skills = fields.get("skills") or []
    parsed.years_experience = int(fields.get("years_experience") or 0)
    parsed.strengths = fields.get("strengths") or ""
    parsed.attachment_url = file.attachment_url
    parsed.resume_content = outcome.text[:20000]
    parsed.raw_json = {
        "evidence": outcome.evidence,
        "confidence": outcome.confidence,
        "ai_fallback": outcome.ai_fallback,
        "parser": "rule-v1",
        "filename": file.filename,
    }

    task.status = "completed"
    task.error_message = None
    file.status = "completed"
    db.add(ParseLog(
        resume_id=file.id, task_id=task.id, status="completed",
        message=f"解析完成，置信度 {outcome.confidence}",
        duration_ms=outcome.duration_ms,
        extracted_summary={
            "name": parsed.name,
            "education": parsed.education,
            "years_experience": parsed.years_experience,
            "skills": parsed.skills[:10],
        },
    ))
    db.flush()

    # 身份去重：同一人的多份简历只留最新一份为现行（不物理删除）
    identity = reconcile_identity(db, parsed)
    if identity["superseded"]:
        db.add(ParseLog(
            resume_id=file.id, task_id=task.id, status="identity",
            message="身份去重：" + (
                f"本份被 {parsed.superseded_by} 替代" if not identity["is_current"]
                else f"替代了 {len(identity['superseded'])} 份旧简历"
            ),
            extracted_summary={"identity_key": identity["identity_key"],
                               "superseded": identity["superseded"]},
        ))
    db.commit()

    return {
        "task_id": task.id,
        "status": "completed",
        "resume_id": parsed.id,
        "fields": {k: fields.get(k) for k in ("name", "education", "years_experience", "skills")},
        "confidence": outcome.confidence,
        "duration_ms": outcome.duration_ms,
        "identity": identity,
    }


def _fail(db: Session, task: ParseTask, file: ResumeFile, message: str, started: datetime) -> None:
    task.status = "failed"
    task.error_message = message[:500]
    file.status = "failed"
    db.add(ParseLog(
        resume_id=file.id, task_id=task.id, status="failed", message=message[:500],
        duration_ms=int((datetime.now() - started).total_seconds() * 1000),
    ))
    db.commit()


def list_resumes(db: Session, user: CurrentUser, keyword: str, education: str,
                 page: int, page_size: int, include_superseded: bool = False) -> tuple[list[dict], int]:
    query = (
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
    )
    if not include_superseded:
        # 默认只看现行简历：同一人的旧简历已被更新的替代，等同"丢弃"但不删数据
        query = query.where(ParsedResume.is_current.is_(True))
    if user.scope_of("resume") != "all":
        query = apply_scope(query, ResumeFile.dept_id, ResumeFile.created_by, user)
    if keyword:
        like = f"%{keyword.strip()}%"
        query = query.where(
            (ParsedResume.name.like(like))
            | (ParsedResume.skills.cast(__import__("sqlalchemy").String).like(like))
            | (ParsedResume.major.like(like))
        )
    if education:
        query = query.where(ParsedResume.education == education)

    total = db.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    rows = db.execute(
        query.order_by(ParsedResume.id.desc()).offset((page - 1) * page_size).limit(page_size)
    ).all()
    # 测评状态：本页 N 条只查 2 次库（不逐条查）
    from app.services.assignment_service import summaries_for
    summaries = summaries_for(db, [int(p.id) for p, _f in rows])
    items = []
    for p, f in rows:
        item = _serialize(p, f)
        item["exam_summary"] = summaries.get(int(p.id)) or {
            "state": "none", "label": "未测评", "total": 0, "passed": 0, "items": []}
        items.append(item)
    return items, int(total)


def _serialize(p: ParsedResume, f: ResumeFile | None) -> dict:
    return {
        "id": p.id,
        "resume_file_id": p.resume_id,
        "name": p.name,
        "phone": p.phone,
        "email": p.email,
        "gender": p.gender,
        "age": p.age,
        "education": p.education,
        "major": p.major,
        "skills": p.skills or [],
        "years_experience": p.years_experience,
        "strengths": p.strengths,
        "manually_fixed": p.manually_fixed,
        "filename": f.filename if f else "",
        "status": f.status if f else "",
        "project_name": f.project_name if f else "",
        "created_at": p.created_at.isoformat(sep=" ", timespec="seconds") if p.created_at else "",
        "confidence": (p.raw_json or {}).get("confidence") if isinstance(p.raw_json, dict) else None,
        "is_current": bool(p.is_current),
        "superseded_by": p.superseded_by,
        "identity_key": p.identity_key or "",
        "employee_user_id": p.employee_user_id,
    }


def get_resume(db: Session, user: CurrentUser, resume_id: int) -> dict:
    row = db.execute(
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ParsedResume.id == resume_id)
    ).first()
    if row is None:
        raise ApiError(404, "简历不存在")
    parsed, file = row
    if not _visible(user, file):
        raise ApiError(403, "无权访问该简历")

    logs = db.execute(
        select(ParseLog).where(ParseLog.resume_id == file.id).order_by(ParseLog.id.desc()).limit(20)
    ).scalars().all()
    item = _serialize(parsed, file)
    from app.services.assignment_service import summaries_for
    item["exam_summary"] = summaries_for(db, [int(parsed.id)]).get(int(parsed.id)) or {
        "state": "none", "label": "未测评", "total": 0, "passed": 0, "items": []}
    # 同一人的简历链：现行 + 被替代的旧版本（只给 id/时间/文件名，避免详情页过重）
    siblings = siblings_of(db, parsed)
    item.update({
        "attachment_url": file.attachment_url,
        "resume_content": parsed.resume_content,
        "raw_json": parsed.raw_json,
        "identity": {
            "key": parsed.identity_key or "",
            "is_current": bool(parsed.is_current),
            "superseded_by": parsed.superseded_by,
            "siblings": [
                {
                    "parsed_resume_id": int(s.id),
                    "name": s.name,
                    "is_current": bool(s.is_current),
                    "created_at": s.created_at.isoformat(sep=" ", timespec="seconds") if s.created_at else "",
                    "filename": _filename_of(db, s),
                }
                for s in siblings
            ],
        },
        "logs": [
            {
                "status": lg.status,
                "message": lg.message,
                "duration_ms": lg.duration_ms,
                "created_at": lg.created_at.isoformat(sep=" ", timespec="seconds") if lg.created_at else "",
            }
            for lg in logs
        ],
    })
    return item


EDITABLE_FIELDS = ("name", "phone", "email", "gender", "age", "education", "major",
                   "skills", "years_experience", "strengths")


def patch_resume(db: Session, user: CurrentUser, resume_id: int, payload: dict) -> dict:
    parsed = db.get(ParsedResume, resume_id)
    if parsed is None:
        raise ApiError(404, "简历不存在")
    file = db.get(ResumeFile, parsed.resume_id)
    if file is None or not _visible(user, file):
        raise ApiError(403, "无权修改该简历")

    changed = {}
    for field in EDITABLE_FIELDS:
        if field in payload and payload[field] is not None:
            value: Any = payload[field]
            if field == "years_experience":
                try:
                    value = int(value)
                except (TypeError, ValueError):
                    raise ApiError(400, "工作年限必须是整数")
            if field == "skills":
                if isinstance(value, str):
                    value = [s.strip() for s in value.replace("，", ",").split(",") if s.strip()]
                if not isinstance(value, list):
                    raise ApiError(400, "技能必须是数组")
            setattr(parsed, field, value)
            changed[field] = value

    if not changed:
        raise ApiError(400, "没有可修改的字段")

    parsed.manually_fixed = True
    db.add(ParseLog(
        resume_id=file.id, task_id=None, status="manual_fix",
        message="人工修正：" + "、".join(changed.keys()),
        extracted_summary={"changed": changed},
    ))
    db.flush()

    # 手机号/邮箱被改 → 身份键可能变，重算去重关系
    identity = reconcile_identity(db, parsed)
    if {"phone", "email"} & set(changed.keys()):
        db.add(ParseLog(
            resume_id=file.id, task_id=None, status="identity",
            message=f"身份键重算：{identity['identity_key'] or '（无可靠身份）'}",
            extracted_summary={"identity_key": identity["identity_key"],
                               "superseded": identity["superseded"]},
        ))
    db.commit()
    return {"id": parsed.id, "changed": list(changed.keys())}


def delete_task(db: Session, user: CurrentUser, task_id: int) -> None:
    task = db.get(ParseTask, task_id)
    if task is None:
        raise ApiError(404, "任务不存在")
    file = db.get(ResumeFile, task.resume_id)
    if file is None or not _visible(user, file):
        raise ApiError(403, "无权删除该任务")
    if task.status == "parsing":
        raise ApiError(409, "任务正在解析中，无法删除")
    db.delete(task)
    db.commit()


def open_file(db: Session, user: CurrentUser, key: str):
    file = db.execute(select(ResumeFile).where(ResumeFile.object_key == key)).scalar_one_or_none()
    if file is None:
        raise ApiError(404, "文件不存在")
    if not _visible(user, file):
        raise ApiError(403, "无权访问该文件")
    return get_storage().path_of(key), file.filename
