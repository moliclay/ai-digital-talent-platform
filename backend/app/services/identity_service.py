"""身份去重：判断两份简历是否属于同一个人，并决定谁是最新（现行）简历。

设计要点（评审确认的口径）：
1. **只有手机号 / 邮箱相同才自动合并**。姓名 + 学历 + 专业全同只标"疑似"，
   不自动合并——两个"张伟"都可能是硕士计算机，误合并会丢人。
2. **"最新"按入库时间**（`created_at` 晚的算新）。系统里没有"简历版本日期"字段，
   按"最近工作时间"判新旧需要给解析器加字段，属于额外一轮工作。
3. **不物理删除**：旧的置 `is_current=0` 并记 `superseded_by`，列表默认不显示，
   文件与解析结果保留可追溯。
"""
from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy import select, text, update
from sqlalchemy.orm import Session

from app.models.orm import ParsedResume

# 手机号：去掉 +86 前缀、空格、横线、括号后，保留 11 位数字
_PHONE_CLEAN = re.compile(r"[\s\-()（）]")
_PHONE_PREFIX = re.compile(r"^(?:\+?86|0086)")


def normalize_phone(raw: str | None) -> str:
    """归一化手机号：`+86 139-0000-0001` → `13900000001`。无效返回空串。"""
    if not raw:
        return ""
    value = _PHONE_CLEAN.sub("", str(raw).strip())
    value = _PHONE_PREFIX.sub("", value)
    digits = re.sub(r"\D", "", value)
    # 中国大陆手机号 11 位；少于 7 位视为无效（座机、分机不参与身份判定）
    return digits if len(digits) >= 7 else ""


def normalize_email(raw: str | None) -> str:
    """归一化邮箱：小写 + 去空白。无效返回空串。"""
    if not raw:
        return ""
    value = str(raw).strip().lower()
    return value if "@" in value and "." in value.split("@")[-1] else ""


def identity_key_of(parsed: ParsedResume) -> str:
    """身份键：手机号优先 → 邮箱 → 空串（空串表示无法可靠判定）。"""
    phone = normalize_phone(parsed.phone)
    if phone:
        return f"phone:{phone}"
    email = normalize_email(parsed.email)
    if email:
        return f"email:{email}"
    return ""


def _suspected_key_of(parsed: ParsedResume) -> str:
    """疑似键：姓名 + 学历 + 专业。只用于标记"疑似重复"，绝不自动合并。"""
    name = (parsed.name or "").strip()
    edu = (parsed.education or "").strip()
    major = (parsed.major or "").strip()
    if not name or not edu or not major:
        return ""
    return f"suspected:{name}|{edu}|{major}"


# 关联数据表 → 指向 parsed_resumes 的外键列名
# 身份去重把旧简历置为「非现行」后，这些数据必须跟着迁到新简历上，
# 否则画像/计划/台账/测评记录会「挂在一份列表里看不到的简历上」。
_LINKED_TABLES = (
    ("talent_profiles", "candidate_id"),
    ("prejob_plans", "candidate_id"),
    ("growth_ledger", "candidate_id"),
    ("exam_assignments", "parsed_resume_id"),
    ("exam_submissions", "parsed_resume_id"),
    ("exam_interview_results", "candidate_id"),
    ("match_lists", "candidate_id"),
    ("match_results", "parsed_resume_id"),
)


def migrate_links(db: Session, old_id: int, new_id: int) -> dict:
    """把挂在旧简历上的关联数据迁到新简历。不 commit。

    只迁移「新简历上还没有同类数据」的情况：
    - `talent_profiles` / `growth_ledger` 是一人一条的语义，若新简历已有则保留新的，
      旧的置为不可见（不删，留追溯）。
    - 其余（计划/测评/匹配）按行迁移，多条并存无冲突。
    - `parsed_resumes.employee_user_id` / `onboarded_at`（转正关系）单独迁：
      新简历还没绑账号才迁，否则保留新简历上的绑定。
    """
    moved: dict[str, int] = {}
    if old_id == new_id:
        return moved

    for table, col in _LINKED_TABLES:
        try:
            # 一人一条的表：新简历已有 → 不动旧的
            if table in ("talent_profiles", "growth_ledger"):
                has_new = db.execute(
                    text(f"select count(*) from {table} where {col}=:n"), {"n": new_id}
                ).scalar()
                if has_new:
                    continue
            # 用 savepoint 包住单表迁移：某张表失败只回滚这张表，不牵连已完成的迁移
            with db.begin_nested():
                n = db.execute(
                    update_table(table, col, old_id, new_id)
                ).rowcount
            if n:
                moved[table] = int(n)
        except Exception:
            # 表不存在或结构不符 → 跳过，不影响身份判定主流程
            continue

    # 转正关系：旧简历已建号、新简历还没绑 → 把账号与转正时间带过来，
    # 否则员工重新上传简历后 /my/training 会认为「未转正」。
    try:
        with db.begin_nested():
            n = db.execute(text(
                "update parsed_resumes set employee_user_id=("
                "  select employee_user_id from (select employee_user_id from parsed_resumes where id=:o) t"
                "), onboarded_at=("
                "  select onboarded_at from (select onboarded_at from parsed_resumes where id=:o) t"
                ") where id=:n and employee_user_id is null"
            ).bindparams(o=int(old_id), n=int(new_id))).rowcount
        if n:
            moved["parsed_resumes.employee_user_id"] = int(n)
    except Exception:
        pass

    return moved


def update_table(table: str, col: str, old_id: int, new_id: int):
    """构造 UPDATE 语句（表名/列名来自常量白名单，无注入风险）。"""
    return text(f"update {table} set {col}=:new where {col}=:old").bindparams(
        new=int(new_id), old=int(old_id)
    )


def reconcile_identity(db: Session, parsed: ParsedResume) -> dict:
    """单份简历落库/修正后调用：重算身份键，并把同一人的旧简历置为非现行。

    返回 {"identity_key", "is_current", "superseded": [被替代的 id 列表]}。
    不 commit，由调用方统一提交。
    """
    key = identity_key_of(parsed)
    parsed.identity_key = key
    superseded: list[int] = []

    if not key:
        # 没有可靠身份 → 它自己就是现行，且不替代任何人
        parsed.is_current = True
        parsed.superseded_by = None
        return {"identity_key": "", "is_current": True, "superseded": []}

    # 必须 flush：SessionLocal 是 autoflush=False，不 flush 的话下面按 identity_key 查库
    # 看不到刚设置的键，会把自己误判成"旧版"。
    db.flush()

    # 同一身份键的所有简历，按 id 倒序（自增 id 越大 = 越后插入 = 越新）
    # 不用 created_at 排序：server_default 的 now() 在 flush 后不会回填到 ORM 对象，
    # 新插入行的 created_at 在本次事务里是 None，会被误判成"最旧"。
    siblings = db.execute(
        select(ParsedResume)
        .where(ParsedResume.identity_key == key)
        .order_by(ParsedResume.id.desc())
    ).scalars().all()

    if not siblings:
        siblings = [parsed]

    # id 最大的那份是现行
    newest = siblings[0]
    newest.is_current = True
    newest.superseded_by = None

    for row in siblings[1:]:
        if row.is_current:
            row.is_current = False
            row.superseded_by = int(newest.id)
            superseded.append(int(row.id))

    if int(newest.id) != int(parsed.id):
        # 当前这份不是最新 → 自己也是被替代的
        parsed.is_current = False
        parsed.superseded_by = int(newest.id)
        if int(parsed.id) not in superseded:
            superseded.append(int(parsed.id))

    # 把旧简历上的画像/计划/台账/测评/匹配记录迁到现行简历，
    # 否则这些数据会「挂在一份列表里看不到的简历上」。
    moved: dict[str, int] = {}
    for old_id in superseded:
        if old_id != int(newest.id):
            moved.update(migrate_links(db, old_id, int(newest.id)))

    return {"identity_key": key, "is_current": bool(parsed.is_current),
            "superseded": superseded, "moved": moved}


def reconcile_all(db: Session) -> dict:
    """全量重算：迁移后跑一次，把历史数据的 identity_key 与 is_current 补齐。

    返回 {"total", "keyed", "unkeyed", "superseded", "suspected_groups"}。
    """
    rows = db.execute(select(ParsedResume).order_by(ParsedResume.created_at, ParsedResume.id)).scalars().all()
    keyed = unkeyed = superseded = 0

    # 先把所有行的 is_current 重置为 True，再按身份键逐组判定
    for row in rows:
        row.is_current = True
        row.superseded_by = None
        row.identity_key = identity_key_of(row)

    groups: dict[str, list[ParsedResume]] = {}
    for row in rows:
        if row.identity_key:
            groups.setdefault(row.identity_key, []).append(row)
        else:
            unkeyed += 1

    for key, members in groups.items():
        keyed += len(members)
        # 与 reconcile_identity 同口径：按 id 倒序（id 越大越新）
        members.sort(key=lambda r: int(r.id), reverse=True)
        newest = members[0]
        for row in members[1:]:
            row.is_current = False
            row.superseded_by = int(newest.id)
            superseded += 1

    # 先提交「谁是现行」，再迁关联数据（迁移要靠 is_current 状态判断新旧）
    db.commit()

    # 历史数据里旧简历挂着的画像/计划/台账/测评/匹配，统一迁到现行简历
    moved: dict[str, int] = {}
    for key, members in groups.items():
        if len(members) < 2:
            continue
        newest = members[0]
        for row in members[1:]:
            for table, n in migrate_links(db, int(row.id), int(newest.id)).items():
                moved[table] = moved.get(table, 0) + n
    db.commit()

    # 疑似重复（姓名+学历+专业全同但身份键不同）：只统计，不合并
    suspected: dict[str, list[int]] = {}
    for row in rows:
        skey = _suspected_key_of(row)
        if skey:
            suspected.setdefault(skey, []).append(int(row.id))
    suspected_groups = {k: v for k, v in suspected.items() if len(v) > 1}

    db.commit()
    return {"total": len(rows), "keyed": keyed, "unkeyed": unkeyed,
            "superseded": superseded, "suspected_groups": suspected_groups,
            "moved": moved}

def siblings_of(db: Session, parsed: ParsedResume) -> list[ParsedResume]:
    """同一身份的全部简历（含自己），按 id 倒序（越新在前）。"""
    if not parsed.identity_key:
        return [parsed]
    return list(db.execute(
        select(ParsedResume)
        .where(ParsedResume.identity_key == parsed.identity_key)
        .order_by(ParsedResume.id.desc())
    ).scalars().all())


def suspected_duplicates(db: Session) -> list[dict]:
    """疑似重复组（同名同校同专业但手机号/邮箱不同）——只报不合并。"""
    rows = db.execute(select(ParsedResume)).scalars().all()
    groups: dict[str, list[ParsedResume]] = {}
    for row in rows:
        skey = _suspected_key_of(row)
        if skey:
            groups.setdefault(skey, []).append(row)
    out = []
    for skey, members in groups.items():
        if len(members) < 2:
            continue
        out.append({
            "reason": "同名 + 同学历 + 同专业，但手机号/邮箱不同",
            "ids": [int(m.id) for m in members],
            "names": [m.name for m in members],
            "education": members[0].education or "",
            "major": members[0].major or "",
        })
    return out
