"""S3 身份去重迁移：给 parsed_resumes 补列 + 全量重算身份键。

幂等可重复执行。不重启服务，只动数据库结构；新列要等服务重启后 ORM 才认。

用法：python scripts/migrate_identity.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
sys.path.insert(0, str(BACKEND_DIR / "scripts"))

from sqlalchemy import text  # noqa: E402

from app.core.db import SessionLocal, engine  # noqa: E402

# (列名, DDL 片段)
COLUMNS = [
    ("identity_key", "VARCHAR(160) NOT NULL DEFAULT ''"),
    ("is_current", "TINYINT NOT NULL DEFAULT 1"),
    ("superseded_by", "INT NULL"),
    ("employee_user_id", "INT NULL"),
    ("onboarded_at", "DATETIME NULL"),
]


def migrate() -> None:
    with engine.begin() as conn:
        cols = {r[0]: r for r in conn.execute(text("SHOW COLUMNS FROM parsed_resumes"))}
        for name, ddl in COLUMNS:
            if name not in cols:
                conn.execute(text(f"ALTER TABLE parsed_resumes ADD COLUMN {name} {ddl}"))
                print(f"parsed_resumes.{name} 已加")
            else:
                print(f"parsed_resumes.{name} 已存在，跳过")

        # 索引：身份键与现行标记都要走索引（列表默认按 is_current 过滤）
        # 注意：SHOW INDEX 第一列是 Table，第二列才是 Key_name，别取错列
        indexes = {row[2] for row in conn.execute(text("SHOW INDEX FROM parsed_resumes"))}
        for idx_name, col in (("ix_parsed_resumes_identity_key", "identity_key"),
                              ("ix_parsed_resumes_is_current", "is_current"),
                              ("ix_parsed_resumes_employee_user_id", "employee_user_id")):
            if idx_name not in indexes:
                conn.execute(text(f"CREATE INDEX {idx_name} ON parsed_resumes ({col})"))
                print(f"索引 {idx_name} 已建")
            else:
                print(f"索引 {idx_name} 已存在，跳过")

    # 全量重算身份键（历史数据 identity_key 为空）
    from app.services.identity_service import reconcile_all  # noqa: E402

    with SessionLocal() as db:
        result = reconcile_all(db)
        print(f"重算完成：total={result['total']} keyed={result['keyed']} "
              f"unkeyed={result['unkeyed']} superseded={result['superseded']}")
        if result["suspected_groups"]:
            print(f"疑似重复组 {len(result['suspected_groups'])} 个（只报不合并）")
            for key, ids in result["suspected_groups"].items():
                print(f"  {key} → ids={ids}")

    with engine.connect() as conn:
        cols = [r[0] for r in conn.execute(text("SHOW COLUMNS FROM parsed_resumes"))]
        print("\nparsed_resumes 现有列：", ", ".join(cols))


if __name__ == "__main__":
    migrate()
