"""一键初始化：建库 → 建表 → 加载 seed_data.sql → 引导演示账号与缺失权限。

用法：
    python scripts/init_db.py             # 幂等：已有数据则只做引导
    python scripts/init_db.py --reset     # 危险：删库重建
    python scripts/init_db.py --check     # 只打印核对结果
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pymysql
from sqlalchemy import func, select, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import settings  # noqa: E402
from app.core.db import SessionLocal, engine  # noqa: E402
from app.core.security import hash_password  # noqa: E402
from app.models.orm import (  # noqa: E402
    Base, MatchList, ParsedResume, ResumeFile, SysMenu, SysRolePermission, SysUser,
)

SEED_PATH = BACKEND_DIR.parent / "tests" / "seed_data.sql"
DEMO_PASSWORD = "123456"


def parse_db_url(url: str) -> dict:
    body = url.split("://", 1)[1]
    creds, hostpart = body.split("@", 1)
    user, password = creds.split(":", 1)
    hostport, dbname = hostpart.split("/", 1)
    host, port = (hostport.split(":", 1) + ["3306"])[:2]
    return {
        "user": user, "password": password, "host": host,
        "port": int(port), "database": dbname.split("?")[0],
    }


def ensure_database(cfg: dict) -> None:
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                           password=cfg["password"], charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS `{cfg['database']}` "
                "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


def drop_database(cfg: dict) -> None:
    conn = pymysql.connect(host=cfg["host"], port=cfg["port"], user=cfg["user"],
                           password=cfg["password"], charset="utf8mb4")
    try:
        with conn.cursor() as cur:
            cur.execute(f"DROP DATABASE IF EXISTS `{cfg['database']}`")
        conn.commit()
    finally:
        conn.close()


def load_seed() -> int:
    if not SEED_PATH.exists():
        raise SystemExit(f"找不到种子文件：{SEED_PATH}")

    raw = SEED_PATH.read_text(encoding="utf-8")
    statements: list[str] = []
    buffer: list[str] = []
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("--"):
            continue
        buffer.append(line)
        if stripped.endswith(";"):
            statements.append("\n".join(buffer).rstrip(";").strip())
            buffer = []

    executed = 0
    with engine.begin() as conn:
        for stmt in statements:
            if not stmt:
                continue
            # 必须用 exec_driver_sql：seed 里的 JSON 含 ":0.3"、":3"，text() 会误当成绑定参数
            conn.exec_driver_sql(stmt)
            executed += 1
    return executed


def ensure_permissions(db) -> None:
    """补齐 seed 未覆盖的权限点（岗位条件、匹配执行、简历写操作）。

    这是 MVP 对夹具的**显式扩展**，不改既有行，只在缺失时新增，可重复执行。
    """
    extras = [
        (10, "岗位条件", "/job-profiles", "sliders", "job:view", 3),
        (11, "人才画像", "/talent-profiles", "user", "talent:view", 4),
    ]
    for menu_id, name, path, icon, code, sort in extras:
        if db.get(SysMenu, menu_id) is None:
            db.add(SysMenu(
                id=menu_id, parent_id=None, name=name, path=path, icon=icon,
                permission_code=code, type="menu", hidden=False, sort=sort, status="active",
            ))
    db.commit()

    grants = [
        # (role_id, menu_id, action, data_scope)
        (2, 1, "view", "dept"),      # hr 需要工作台作为落地页
        (2, 10, "view", "all"), (2, 10, "create", "all"), (2, 10, "edit", "all"),
        (3, 10, "view", "all"),
        (2, 2, "create", "dept"), (2, 2, "edit", "dept"), (2, 2, "delete", "dept"),
        (2, 4, "view", "dept"), (2, 4, "create", "dept"),
        (3, 4, "create", "dept"),
        # 人才画像与测评：本期闭环所需
        (2, 11, "view", "dept"), (2, 11, "create", "dept"), (3, 11, "view", "dept"),
        (2, 3, "view", "dept"), (2, 3, "create", "dept"), (3, 3, "view", "dept"),
        # 培训成长：HR 全权、业务负责人只读
        (2, 5, "view", "dept"), (2, 5, "create", "dept"), (2, 5, "edit", "dept"),
        (3, 5, "view", "dept"),
        # 需求⑤：普通员工只保留培训成长（收回工作台与知识库）
        (4, 5, "view", "self"), (4, 5, "edit", "self"),
    ]
    for role_id, menu_id, action, scope in grants:
        exists = db.execute(
            select(SysRolePermission).where(
                SysRolePermission.role_id == role_id,
                SysRolePermission.menu_id == menu_id,
                SysRolePermission.action == action,
            )
        ).scalar_one_or_none()
        if exists is None:
            db.add(SysRolePermission(role_id=role_id, menu_id=menu_id, action=action, data_scope=scope))
    db.commit()

    # 需求⑤：员工「只保留培训成长」——收回 seed 给的 dashboard / kb 权限
    revoke = [
        (4, 1, "view"),   # 智能工作台
        (4, 7, "view"),   # 知识库（无接口，留着只会进空态）
    ]
    for role_id, menu_id, action in revoke:
        row = db.execute(
            select(SysRolePermission).where(
                SysRolePermission.role_id == role_id,
                SysRolePermission.menu_id == menu_id,
                SysRolePermission.action == action,
            )
        ).scalar_one_or_none()
        if row is not None:
            db.delete(row)
    db.commit()


def bootstrap_accounts(db) -> None:
    password = hash_password(DEMO_PASSWORD)
    for username in ("admin", "hr_zhao", "pm_wang", "emp_chen"):
        user = db.execute(select(SysUser).where(SysUser.username == username)).scalar_one_or_none()
        if user is None:
            continue
        # seed 里的占位密文没有可用密码，统一覆盖为演示密码
        if not user.password.startswith("pbkdf2_sha256$"):
            user.password = password
    db.commit()


def backfill_ownership(db) -> None:
    """seed 未提供归属列：把示例简历挂到 HR 部门，才能演示 dept 隔离。"""
    for file_id in (1, 2):
        file = db.get(ResumeFile, file_id)
        if file is not None and file.dept_id is None:
            file.dept_id = 4
            file.created_by = 2
    db.commit()


def report(db) -> None:
    checks = [
        ("sys_users", select(func.count()).select_from(SysUser)),
        ("sys_menus", select(func.count()).select_from(SysMenu)),
        ("sys_role_permissions", select(func.count()).select_from(SysRolePermission)),
        ("resume_files", select(func.count()).select_from(ResumeFile)),
        ("parsed_resumes", select(func.count()).select_from(ParsedResume)),
        ("match_lists", select(func.count()).select_from(MatchList)),
    ]
    print("\n=== 核对 ===")
    for label, stmt in checks:
        print(f"{label:24s} {db.execute(stmt).scalar_one()}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true", help="删库重建（会丢数据）")
    parser.add_argument("--check", action="store_true", help="只核对")
    args = parser.parse_args()

    cfg = parse_db_url(settings.db_url)
    print(f"目标库：{cfg['host']}:{cfg['port']}/{cfg['database']}")

    if args.check:
        with SessionLocal() as db:
            report(db)
        return

    if args.reset:
        drop_database(cfg)
        print("已删除旧库")

    ensure_database(cfg)
    Base.metadata.create_all(engine)
    print("表结构已就绪")

    with SessionLocal() as db:
        user_count = db.execute(select(func.count()).select_from(SysUser)).scalar_one()
        if user_count == 0:
            executed = load_seed()
            print(f"seed_data.sql 已加载：{executed} 条语句")
        else:
            print(f"已存在 {user_count} 个用户，跳过 seed 加载")

        ensure_permissions(db)
        bootstrap_accounts(db)
        backfill_ownership(db)
        report(db)
        print(f"\n演示账号密码统一为 {DEMO_PASSWORD}：admin / hr_zhao / pm_wang / emp_chen")


if __name__ == "__main__":
    main()
