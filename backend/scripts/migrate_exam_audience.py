"""S4 迁移：测评受众 + 绑定表 + 答卷归属简历。

幂等可重复执行。不重启服务，只动数据库结构。

用法：python scripts/migrate_exam_audience.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import text  # noqa: E402

from app.core.db import engine  # noqa: E402

COLUMNS = [
    ("question_banks", "audience", "VARCHAR(32) NOT NULL DEFAULT 'candidate'"),
    ("exams", "audience", "VARCHAR(32) NOT NULL DEFAULT 'candidate'"),
    ("exam_submissions", "parsed_resume_id", "INT NULL"),
]


def migrate() -> None:
    with engine.begin() as conn:
        # 1) 补列
        for table, name, ddl in COLUMNS:
            cols = {r[0] for r in conn.execute(text(f"SHOW COLUMNS FROM {table}"))}
            if name not in cols:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))
                print(f"{table}.{name} 已加")
            else:
                print(f"{table}.{name} 已存在，跳过")

        # 2) exam_submissions.parsed_resume_id 索引
        indexes = {row[2] for row in conn.execute(text("SHOW INDEX FROM exam_submissions"))}
        if "ix_exam_submissions_parsed_resume_id" not in indexes:
            conn.execute(text("CREATE INDEX ix_exam_submissions_parsed_resume_id "
                              "ON exam_submissions (parsed_resume_id)"))
            print("索引 ix_exam_submissions_parsed_resume_id 已建")
        else:
            print("索引 ix_exam_submissions_parsed_resume_id 已存在，跳过")

        # 3) 新建 exam_assignments 表
        tables = {r[0] for r in conn.execute(text("SHOW TABLES"))}
        if "exam_assignments" not in tables:
            conn.execute(text("""
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
                  updated_at        DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
                  INDEX ix_exam_assignments_exam_id (exam_id),
                  INDEX ix_exam_assignments_parsed_resume_id (parsed_resume_id),
                  INDEX ix_exam_assignments_status (status)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
            """))
            print("表 exam_assignments 已建")
        else:
            print("表 exam_assignments 已存在，跳过")

    with engine.connect() as conn:
        print("\nquestion_banks.audience 分布：")
        for r in conn.execute(text("SELECT audience, COUNT(*) FROM question_banks GROUP BY audience")):
            print(f"  {r[0]}: {r[1]}")
        print("exams.audience 分布：")
        for r in conn.execute(text("SELECT audience, COUNT(*) FROM exams GROUP BY audience")):
            print(f"  {r[0]}: {r[1]}")


if __name__ == "__main__":
    migrate()
