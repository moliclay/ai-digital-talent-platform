"""Read models used by the system administration endpoints."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.orm import SysOperationLog, SysRole, SysUser


def list_users(db: Session, page_no: int, page_size: int) -> tuple[list[dict], int]:
    total = db.execute(select(func.count()).select_from(SysUser)).scalar_one()
    rows = db.execute(
        select(SysUser).order_by(SysUser.id).offset((page_no - 1) * page_size).limit(page_size)
    ).scalars().all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "real_name": u.real_name,
            "department_name": u.department_name,
            "email": u.email,
            "status": u.status,
        }
        for u in rows
    ], int(total)


def list_roles(db: Session) -> list[dict]:
    rows = db.execute(select(SysRole).order_by(SysRole.id)).scalars().all()
    return [
        {"id": r.id, "code": r.code, "name": r.name, "data_scope": r.data_scope,
         "description": r.description}
        for r in rows
    ]


def list_operation_logs(db: Session, page_no: int, page_size: int) -> tuple[list[dict], int]:
    total = db.execute(select(func.count()).select_from(SysOperationLog)).scalar_one()
    rows = db.execute(
        select(SysOperationLog).order_by(SysOperationLog.id.desc())
        .offset((page_no - 1) * page_size).limit(page_size)
    ).scalars().all()
    return [
        {
            "id": r.id,
            "username": r.username,
            "module": r.module,
            "action": r.action,
            "method": r.method,
            "path": r.path,
            "status": r.status,
            "duration_ms": r.duration_ms,
            "created_at": r.created_at.isoformat(sep=" ", timespec="seconds") if r.created_at else "",
        }
        for r in rows
    ], int(total)
