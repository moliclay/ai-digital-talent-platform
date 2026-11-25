"""登录 / 会话 / 菜单下发。会话落在 Redis（可降级为无状态 JWT）。"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.db import get_redis
from app.core.deps import CurrentUser, _resolve_permissions, _resolve_roles, has_perm
from app.core.response import ApiError
from app.core.security import create_access_token, verify_password
from app.models.orm import SysMenu, SysUser


def login(db: Session, username: str, password: str) -> dict:
    user = db.execute(select(SysUser).where(SysUser.username == username)).scalar_one_or_none()
    if user is None or not verify_password(password, user.password):
        raise ApiError(401, "用户名或密码错误")
    if user.status != "active":
        raise ApiError(403, "账号已停用")

    roles = _resolve_roles(db, user.id)
    perm_map = _resolve_permissions(db, roles)
    token, jti = create_access_token(user.id, user.username)

    redis = get_redis()
    if redis is not None:
        redis.setex(f"auth:session:{jti}", settings.jwt_ttl_minutes * 60, str(user.id))

    current = CurrentUser(
        id=user.id, username=user.username, real_name=user.real_name,
        department_id=user.department_id, department_name=user.department_name,
        roles=[r.code for r in roles], perm_map=perm_map,
    )

    return {
        "token": token,
        "expires_in": settings.jwt_ttl_minutes * 60,
        "user": {
            "id": user.id,
            "username": user.username,
            "real_name": user.real_name,
            "department_id": user.department_id,
            "department_name": user.department_name,
            "roles": [r.code for r in roles],
            "role_names": [r.name for r in roles],
            "data_scope": current.scope_of("resume"),
        },
        "menus": visible_menus(db, current),
    }


def logout(jti: str) -> None:
    redis = get_redis()
    if redis is not None and jti:
        redis.setex(f"auth:blacklist:{jti}", settings.jwt_ttl_minutes * 60, "1")
        redis.delete(f"auth:session:{jti}")


def visible_menus(db: Session, user: CurrentUser) -> list[dict]:
    menus = db.execute(
        select(SysMenu).where(SysMenu.status == "active", SysMenu.type == "menu").order_by(SysMenu.sort)
    ).scalars().all()
    result = []
    for m in menus:
        code = (m.permission_code or "").split(":")[0]
        if m.id == 9:  # 系统管理
            allowed = has_perm(user, "sys", "view")
        elif m.id == 3:
            allowed = has_perm(user, "exam", "view")
        elif m.id == 5:
            allowed = has_perm(user, "train", "view")
        elif m.id == 6:
            allowed = has_perm(user, "decision", "view")
        elif m.id == 7:
            allowed = has_perm(user, "kb", "view")
        elif m.id == 8:
            allowed = has_perm(user, "agent", "view")
        elif m.id == 4:
            allowed = has_perm(user, "match", "view") or has_perm(user, "job", "view")
        elif m.id == 2:
            allowed = has_perm(user, "resume", "view")
        else:
            allowed = has_perm(user, code or "dashboard", "view")
        result.append({
            "id": m.id,
            "name": m.name,
            "path": m.path,
            "icon": m.icon,
            "permission_code": m.permission_code,
            "allowed": allowed,
        })
    return result
