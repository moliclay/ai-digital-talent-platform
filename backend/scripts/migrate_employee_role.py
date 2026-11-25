"""S5 迁移：员工权限调整（需求⑤）。

只做授权变更，不动业务数据：
- 收回 role 4（employee）的 dashboard / 知识库权限
- 授予 role 4 培训成长 view(self) + edit(self)

幂等可重复执行。

用法：python scripts/migrate_employee_role.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from sqlalchemy import select, text  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.models.orm import SysRolePermission  # noqa: E402

EMPLOYEE_ROLE = 4
MENU_DASHBOARD = 1
MENU_TRAINING = 5
MENU_KB = 7


def migrate() -> None:
    with SessionLocal() as db:
        print("=== 变更前：role 4 的权限 ===")
        for r in db.execute(select(SysRolePermission).where(SysRolePermission.role_id == EMPLOYEE_ROLE)).scalars():
            print(f"  menu={r.menu_id} action={r.action} scope={r.data_scope}")

        # 收回
        revoked = 0
        for menu_id in (MENU_DASHBOARD, MENU_KB):
            row = db.execute(
                select(SysRolePermission).where(
                    SysRolePermission.role_id == EMPLOYEE_ROLE,
                    SysRolePermission.menu_id == menu_id,
                    SysRolePermission.action == "view",
                )
            ).scalar_one_or_none()
            if row is not None:
                db.delete(row)
                revoked += 1
                print(f"  已收回 menu={menu_id} view")

        # 授予
        granted = 0
        for action in ("view", "edit"):
            exists = db.execute(
                select(SysRolePermission).where(
                    SysRolePermission.role_id == EMPLOYEE_ROLE,
                    SysRolePermission.menu_id == MENU_TRAINING,
                    SysRolePermission.action == action,
                )
            ).scalar_one_or_none()
            if exists is None:
                db.add(SysRolePermission(role_id=EMPLOYEE_ROLE, menu_id=MENU_TRAINING,
                                         action=action, data_scope="self"))
                granted += 1
                print(f"  已授予 train:{action} (self)")
        db.commit()

        print(f"\n收回 {revoked} 项 / 授予 {granted} 项")
        print("=== 变更后：role 4 的权限 ===")
        for r in db.execute(select(SysRolePermission).where(SysRolePermission.role_id == EMPLOYEE_ROLE)).scalars():
            print(f"  menu={r.menu_id} action={r.action} scope={r.data_scope}")

    with engine.connect() as conn:
        print("\n=== role 4 可见菜单（按 permission_code）===")
        rows = conn.execute(text("""
            SELECT m.id, m.name, m.path, m.permission_code
            FROM sys_menus m
            JOIN sys_role_permissions p ON p.menu_id = m.id
            WHERE p.role_id = 4 AND p.action = 'view' AND m.status = 'active'
            ORDER BY m.sort
        """))
        for r in rows:
            print(f"  {r[0]} {r[1]} {r[2]} {r[3]}")


if __name__ == "__main__":
    migrate()
