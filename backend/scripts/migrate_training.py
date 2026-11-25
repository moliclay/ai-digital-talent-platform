"""培训模块迁移：建表 + 补列 + 授权，幂等可重复执行。

不重启服务，只动数据库结构。新的路由与 ORM 要等服务重启后才会生效。
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402
from app.models.orm import Base  # noqa: E402
from init_db import ensure_permissions  # noqa: E402


def migrate() -> None:
    # 1) 建新表（prejob_plan_tasks / growth_ledger），已存在则跳过
    Base.metadata.create_all(bind=engine)

    with engine.begin() as conn:
        # 2) training_courses 补 exam_id（课后考核试卷）
        cols = [r[0] for r in conn.execute(text("SHOW COLUMNS FROM training_courses"))]
        if "exam_id" not in cols:
            conn.execute(text("ALTER TABLE training_courses ADD COLUMN exam_id INT NULL"))
            print("training_courses.exam_id 已加")

    # 3) 补齐 hr / 业务负责人的培训权限
    with SessionLocal() as db:
        ensure_permissions(db)

    with engine.connect() as conn:
        tables = [r[0] for r in conn.execute(text("SHOW TABLES"))]
        print("prejob_plan_tasks:", "prejob_plan_tasks" in tables,
              "| growth_ledger:", "growth_ledger" in tables)


if __name__ == "__main__":
    migrate()
