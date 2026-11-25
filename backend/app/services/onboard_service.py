"""转正建号：候选人 → 正式员工账号（需求⑤）。

规则（评审确认）：
- 用**手机号**做账号（`sys_users.username` 唯一）；缺手机号直接拒绝，不猜。
- 初始密码 `Emp` + 6 位随机数字，**只在本次响应里返回一次**，不落库明文、不写日志。
- 幂等：已转正返回 409 + 已有账号，不重复建。
- 关联：`parsed_resumes.employee_user_id` / `onboarded_at`，画像同步记 `employee_user_id`。
"""
from __future__ import annotations

import secrets
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser
from app.core.response import ApiError
from app.core.security import hash_password
from app.models.orm import (
    ParsedResume, ResumeFile, SysOperationLog, SysRole, SysUser, SysUserRole, TalentProfile,
)
from app.services.identity_service import normalize_phone

EMPLOYEE_ROLE_ID = 4          # seed 里 employee 的 role_id
DEFAULT_DEPT_NAME = "算法组"


def _visible(user: CurrentUser, file: ResumeFile | None) -> bool:
    if file is None:
        return False
    scope = user.scope_of("resume")
    if scope == "all":
        return True
    if scope == "dept":
        return file.dept_id == user.department_id
    return file.created_by == user.id


def _gen_password() -> str:
    """初始密码：Emp + 6 位随机数字（8 位，便于口头转述）。"""
    return f"Emp{secrets.randbelow(1_000_000):06d}"


def onboard(db: Session, user: CurrentUser, parsed_resume_id: int, payload: dict) -> dict:
    """把候选人转为正式员工：建 sys_users 账号 + 绑 employee 角色 + 回写关联。"""
    row = db.execute(
        select(ParsedResume, ResumeFile)
        .join(ResumeFile, ResumeFile.id == ParsedResume.resume_id)
        .where(ParsedResume.id == int(parsed_resume_id))
    ).first()
    if row is None:
        raise ApiError(404, "简历不存在")
    parsed, file = row
    if not _visible(user, file):
        raise ApiError(403, "无权操作该简历")

    # 幂等：已转正
    if parsed.employee_user_id:
        existing = db.get(SysUser, int(parsed.employee_user_id))
        raise ApiError(409, f"该候选人已转为正式员工，账号 {existing.username if existing else parsed.employee_user_id}")

    # 手机号必须存在且可归一化
    phone = normalize_phone(parsed.phone)
    if not phone or len(phone) < 11:
        raise ApiError(400, "缺少有效手机号，请先在简历详情补全 11 位手机号")

    # 占号检查
    taken = db.execute(select(SysUser).where(SysUser.username == phone)).scalar_one_or_none()
    if taken is not None:
        raise ApiError(409, f"手机号已被账号 {taken.username}（{taken.real_name}）占用")

    dept_id = payload.get("department_id")
    dept_id = int(dept_id) if dept_id else (file.dept_id or user.department_id or 0) or None
    dept_name = str(payload.get("department_name") or "").strip() or DEFAULT_DEPT_NAME

    raw_password = str(payload.get("initial_password") or "").strip()
    generated = False
    if not raw_password:
        raw_password = _gen_password()
        generated = True
    elif len(raw_password) < 6:
        raise ApiError(400, "初始密码至少 6 位")

    employee = SysUser(
        username=phone,
        real_name=parsed.name or "",
        password=hash_password(raw_password),
        email=parsed.email or None,
        phone=phone,
        department_id=dept_id,
        department_name=dept_name,
        status="active",
    )
    db.add(employee)
    db.flush()

    # 绑 employee 角色
    role = db.get(SysRole, EMPLOYEE_ROLE_ID)
    if role is None:
        raise ApiError(500, "employee 角色缺失，请先执行 init_db")
    exists = db.execute(
        select(SysUserRole).where(SysUserRole.user_id == employee.id,
                                   SysUserRole.role_id == EMPLOYEE_ROLE_ID)
    ).scalar_one_or_none()
    if exists is None:
        db.add(SysUserRole(user_id=employee.id, role_id=EMPLOYEE_ROLE_ID))

    # 回写关联
    parsed.employee_user_id = employee.id
    parsed.onboarded_at = datetime.now()

    profile = db.execute(
        select(TalentProfile).where(TalentProfile.candidate_id == parsed.id)
    ).scalar_one_or_none()
    if profile is not None:
        profile.employee_user_id = employee.id

    db.add(SysOperationLog(
        user_id=user.id, username=user.username,
        module="resume", action="onboard", method="POST",
        path=f"/api/resumes/{parsed.id}/onboard",
        params=f"候选人转正式员工：{parsed.name} → 账号 {phone}",
        status="success",
    ))
    db.commit()

    return {
        "parsed_resume_id": int(parsed.id),
        "employee_user_id": employee.id,
        "username": employee.username,
        "real_name": employee.real_name,
        "department_id": employee.department_id,
        "department_name": employee.department_name,
        # 密码只在这一次返回；generated=true 表示是系统生成的
        "initial_password": raw_password,
        "password_generated": generated,
        "onboarded_at": parsed.onboarded_at.isoformat(sep=" ", timespec="seconds"),
        "role": "employee",
        "note": "初始密码只显示这一次，请转告员工；员工登录后可用手机号作为账号。",
    }
