"""鉴权依赖：Token → 用户 → 角色 → 权限码 → 数据范围。

设计原则（dev-god 后端规则）：认证之后仍要校验对象归属与数据范围，
不能只信任客户端传来的用户 ID；范围判断收敛到这里，DAO 统一消费。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from fastapi import Depends, Header
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db, get_redis
from app.core.response import ApiError
from app.core.security import decode_token
from app.models.orm import SysMenu, SysRole, SysRolePermission, SysUser, SysUserRole

SCOPE_RANK = {"self": 1, "dept": 2, "all": 3}


@dataclass
class CurrentUser:
    id: int
    username: str
    real_name: str
    department_id: int | None
    department_name: str
    roles: list[str] = field(default_factory=list)
    perm_map: dict[str, str] = field(default_factory=dict)  # "resume:view" -> "dept"

    def scope_of(self, resource: str = "resume") -> str:
        """按资源解析数据范围：HR 对简历是 dept，对岗位条件可能是 all。"""
        best = "self"
        for key, scope in self.perm_map.items():
            code, _, _action = key.partition(":")
            if code in (resource, "*"):
                if SCOPE_RANK.get(scope, 1) > SCOPE_RANK.get(best, 1):
                    best = scope
        return best

    @property
    def permissions(self) -> list[str]:
        return sorted(self.perm_map)

    @property
    def scope(self) -> str:
        best = "self"
        for scope in self.perm_map.values():
            if SCOPE_RANK.get(scope, 1) > SCOPE_RANK.get(best, 1):
                best = scope
        return best

    @property
    def is_admin(self) -> bool:
        return "admin" in self.roles


def _load_user(db: Session, user_id: int) -> SysUser:
    user = db.get(SysUser, user_id)
    if user is None or user.status != "active":
        raise ApiError(401, "账号不存在或已停用")
    return user


def _resolve_roles(db: Session, user_id: int) -> list[SysRole]:
    rows = db.execute(
        select(SysRole)
        .join(SysUserRole, SysUserRole.role_id == SysRole.id)
        .where(SysUserRole.user_id == user_id, SysRole.status == "active")
    ).scalars().all()
    return list(rows)


def _resolve_permissions(db: Session, roles: list[SysRole]) -> dict[str, str]:
    """返回 {"权限码:动作": 数据范围}。menu_id 为 NULL 表示该角色对该动作全模块生效。"""
    if not roles:
        return {}

    role_ids = [r.id for r in roles]
    perms = db.execute(
        select(SysRolePermission).where(SysRolePermission.role_id.in_(role_ids))
    ).scalars().all()
    menus = {m.id: m for m in db.execute(select(SysMenu)).scalars().all()}

    result: dict[str, str] = {}
    for p in perms:
        if p.menu_id is None:
            keys = [f"*:{p.action}"]
        else:
            menu = menus.get(p.menu_id)
            if not menu or not menu.permission_code:
                continue
            keys = [f"{menu.permission_code.split(':')[0]}:{p.action}"]
        for key in keys:
            current = result.get(key)
            if current is None or SCOPE_RANK.get(p.data_scope, 1) > SCOPE_RANK.get(current, 1):
                result[key] = p.data_scope
    return result


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise ApiError(401, "未登录或令牌缺失")

    token = authorization.split(" ", 1)[1].strip()
    try:
        payload = decode_token(token)
    except Exception:
        raise ApiError(401, "令牌无效或已过期")

    jti = payload.get("jti", "")
    r = get_redis()
    if r is not None and jti and r.get(f"auth:blacklist:{jti}"):
        raise ApiError(401, "令牌已失效，请重新登录")

    user = _load_user(db, int(payload["sub"]))
    roles = _resolve_roles(db, user.id)

    return CurrentUser(
        id=user.id,
        username=user.username,
        real_name=user.real_name,
        department_id=user.department_id,
        department_name=user.department_name,
        roles=[r.code for r in roles],
        perm_map=_resolve_permissions(db, roles),
    )


def has_perm(user: CurrentUser, perm: str, action: str = "view") -> bool:
    return f"*:{action}" in user.permissions or f"{perm}:{action}" in user.permissions


def require_perm(perm: str, action: str = "view") -> Callable[[CurrentUser], CurrentUser]:
    """用法：user: CurrentUser = Depends(require_perm("resume", "view"))"""

    def _dep(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if not has_perm(user, perm, action):
            raise ApiError(403, f"无权限：{perm}:{action}")
        return user

    return _dep


def max_scope(user: CurrentUser, *resources: str) -> str:
    best = "self"
    for resource in resources:
        scope = user.scope_of(resource)
        if SCOPE_RANK.get(scope, 1) > SCOPE_RANK.get(best, 1):
            best = scope
    return best


def apply_scope(query, column_dept, column_owner, user: CurrentUser, resource="resume"):
    """把 data_scope 注入查询。all 不过滤；dept 按归属部门；self 按创建人。

    resource 可以是单个资源名或资源名元组——匹配场景同时受"简历"和"匹配"两个权限影响，
    取其中更大的范围，避免出现"能进匹配页却一条看不到"的死区。
    column_dept / column_owner 必须是 ORM 列对象（受控映射，禁止拼接字符串）。
    """
    resources = (resource,) if isinstance(resource, str) else tuple(resource)
    scope = max_scope(user, *resources)
    if scope == "all":
        return query
    if scope == "dept":
        if user.department_id is None:
            raise ApiError(403, "当前账号未分配部门，无法按部门范围查询")
        return query.where(column_dept == user.department_id)
    return query.where(column_owner == user.id)
