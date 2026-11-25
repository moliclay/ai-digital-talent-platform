"""后端优化项 S1–S6 统一迁移脚本（一次跑完所有结构变更）。

幂等可重复执行。只动数据库结构与权限，不动业务数据。
不重启服务；新路由/新 ORM 列要等服务重启后才生效。

包含：
- S3 身份去重：parsed_resumes 加 identity_key / is_current / superseded_by /
  employee_user_id / onboarded_at + 索引
- S3 全量重算身份键
- S4 测评受众：question_banks.audience / exams.audience /
  exam_submissions.parsed_resume_id + 新表 exam_assignments
- S5 转正：talent_profiles.employee_user_id + 索引
- S5 员工权限：收回 dashboard/kb、授予 train:view|edit(self)

用法：python scripts/migrate_backend_v2.py
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

# (表, 列, DDL)
COLUMNS = [
    ("parsed_resumes", "identity_key", "VARCHAR(160) NOT NULL DEFAULT ''"),
    ("parsed_resumes", "is_current", "TINYINT NOT NULL DEFAULT 1"),
    ("parsed_resumes", "superseded_by", "INT NULL"),
    ("parsed_resumes", "employee_user_id", "INT NULL"),
    ("parsed_resumes", "onboarded_at", "DATETIME NULL"),
    ("question_banks", "audience", "VARCHAR(32) NOT NULL DEFAULT 'candidate'"),
    ("exams", "audience", "VARCHAR(32) NOT NULL DEFAULT 'candidate'"),
    ("exam_submissions", "parsed_resume_id", "INT NULL"),
    ("talent_profiles", "employee_user_id", "INT NULL"),
]

# (索引名, 表, 列)
INDEXES = [
    ("ix_parsed_resumes_identity_key", "parsed_resumes", "identity_key"),
    ("ix_parsed_resumes_is_current", "parsed_resumes", "is_current"),
    ("ix_parsed_resumes_employee_user_id", "parsed_resumes", "employee_user_id"),
    ("ix_exam_submissions_parsed_resume_id", "exam_submissions", "parsed_resume_id"),
    ("ix_talent_profiles_employee_user_id", "talent_profiles", "employee_user_id"),
]

ASSIGNMENT_TABLE = """
CREATE TABLE exam_assignments (
  id                INT AUTO_INCREMENT PRIMARY KEY,
  exam_id           INT NOT NULL,
  parsed_resume_id  INT NOT NULL,
  candidate_name    VARCHAR(128) NOT NULL DEFAULT '',
  status            VARCHAR(32) NOT NULL DEFAULT 'pending',
  submission_id     INT NULL,
  assigned_by       INT NULL,
  deadline          DATETIME NULL,
  note              TEXT NOT NULL,
  created_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX ix_exam_assignments_exam_id (exam_id),
  INDEX ix_exam_assignments_parsed_resume_id (parsed_resume_id),
  INDEX ix_exam_assignments_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

EMPLOYEE_ROLE = 4
MENU_DASHBOARD, MENU_TRAINING, MENU_KB = 1, 5, 7


def _columns(conn, table: str) -> set[str]:
    return {r[0] for r in conn.execute(text(f"SHOW COLUMNS FROM {table}"))}


def _indexes(conn, table: str) -> set[str]:
    # SHOW INDEX 第一列是 Table，第二列才是 Key_name
    return {row[2] for row in conn.execute(text(f"SHOW INDEX FROM {table}"))}


def step_structure() -> None:
    with engine.begin() as conn:
        for table, name, ddl in COLUMNS:
            if name not in _columns(conn, table):
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                print(f"  + {table}.{name}")
            else:
                print(f"  = {table}.{name} 已存在")

        for idx_name, table, col in INDEXES:
            if idx_name not in _indexes(conn, table):
                conn.execute(text(f"CREATE INDEX {idx_name} ON {table} ({col})"))
                print(f"  + 索引 {idx_name}")
            else:
                print(f"  = 索引 {idx_name} 已存在")

        if "exam_assignments" not in {r[0] for r in conn.execute(text("SHOW TABLES"))}:
            conn.execute(text(ASSIGNMENT_TABLE))
            print("  + 表 exam_assignments")
        else:
            print("  = 表 exam_assignments 已存在")


def step_identity() -> None:
    from app.services.identity_service import reconcile_all

    with SessionLocal() as db:
        r = reconcile_all(db)
        print(f"  身份重算：total={r['total']} keyed={r['keyed']} "
              f"unkeyed={r['unkeyed']} superseded={r['superseded']}")
        if r["suspected_groups"]:
            print(f"  疑似重复组 {len(r['suspected_groups'])} 个（只报不合并）：")
            for key, ids in r["suspected_groups"].items():
                print(f"    {key} → {ids}")


def step_employee_role() -> None:
    with SessionLocal() as db:
        revoked = granted = 0
        for menu_id in (MENU_DASHBOARD, MENU_KB):
            row = db.execute(select(SysRolePermission).where(
                SysRolePermission.role_id == EMPLOYEE_ROLE,
                SysRolePermission.menu_id == menu_id,
                SysRolePermission.action == "view",
            )).scalar_one_or_none()
            if row is not None:
                db.delete(row)
                revoked += 1
        for action in ("view", "edit"):
            exists = db.execute(select(SysRolePermission).where(
                SysRolePermission.role_id == EMPLOYEE_ROLE,
                SysRolePermission.menu_id == MENU_TRAINING,
                SysRolePermission.action == action,
            )).scalar_one_or_none()
            if exists is None:
                db.add(SysRolePermission(role_id=EMPLOYEE_ROLE, menu_id=MENU_TRAINING,
                                         action=action, data_scope="self"))
                granted += 1
        db.commit()
        print(f"  员工权限：收回 {revoked} / 授予 {granted}")
        rows = db.execute(select(SysRolePermission).where(
            SysRolePermission.role_id == EMPLOYEE_ROLE)).scalars().all()
        print("  role 4 现有：", ", ".join(f"menu{r.menu_id}:{r.action}({r.data_scope})" for r in rows))


def report() -> None:
    with engine.connect() as conn:
        print("\n=== 迁移后核对 ===")
        for t in ("parsed_resumes", "exam_assignments", "question_banks", "exams", "talent_profiles"):
            n = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar()
            print(f"  {t:20s} {n} 行")
        print("  现行简历：", conn.execute(text(
            "SELECT COUNT(*) FROM parsed_resumes WHERE is_current=1")).scalar())
        print("  受众分布：", dict(conn.execute(text(
            "SELECT audience, COUNT(*) FROM exams GROUP BY audience")).all()))


def migrate() -> None:
    print("=== 1. 结构变更 ===")
    step_structure()
    print("\n=== 2. 身份重算 ===")
    step_identity()
    print("\n=== 3. 员工权限 ===")
    step_employee_role()
    report()
    print("\n迁移完成。新路由与 ORM 列需重启后端后生效。")


if __name__ == "__main__":
    migrate()
