"""ORM 模型：以 docs/design/数据库表设计.md 为准，目标是 tests/seed_data.sql 可原样加载。

MVP-1 有业务逻辑的表 16 张；其余为对齐设计文档与 seed 夹具而建表，暂不写逻辑。
相对设计文档的扩展字段（评审通过）：resume_files.dept_id / created_by、parsed_resumes.manually_fixed。
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON, BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer,
    String, Text, func, text,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


# ---------------------------------------------------------------- ChatAI
class ChatSession(Base, TimestampMixin):
    __tablename__ = "chat_sessions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("sys_users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(128), default="新对话", nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    active_turn_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ChatConversation(Base, TimestampMixin):
    __tablename__ = "chat_conversations"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(Integer, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    rewritten_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    business_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    source_refs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    audit_status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", nullable=False)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)


# ---------------------------------------------------------------- 系统 / 权限
class SysDepartment(Base):
    __tablename__ = "sys_departments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    leader: Mapped[str | None] = mapped_column(String(64), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SysUser(Base):
    __tablename__ = "sys_users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    real_name: Mapped[str] = mapped_column(String(64), nullable=False)
    password: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    department_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    department_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SysRole(Base):
    __tablename__ = "sys_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    data_scope: Mapped[str] = mapped_column(String(16), default="self", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SysUserRole(Base):
    __tablename__ = "sys_user_roles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    role_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)


class SysMenu(Base):
    __tablename__ = "sys_menus"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    path: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    permission_code: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    type: Mapped[str] = mapped_column(String(16), default="menu", nullable=False)
    hidden: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sort: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class SysRolePermission(Base):
    __tablename__ = "sys_role_permissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    role_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    menu_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(32), default="view", nullable=False)
    data_scope: Mapped[str] = mapped_column(String(16), default="self", nullable=False)


class SysOperationLog(Base):
    __tablename__ = "sys_operation_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    username: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    module: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    method: Mapped[str] = mapped_column(String(16), default="", nullable=False)
    path: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    params: Mapped[str | None] = mapped_column(Text, nullable=True)
    ip: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="success", nullable=False)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


# ---------------------------------------------------------------- 岗位
class Position(Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)


class JobProfile(Base, TimestampMixin):
    __tablename__ = "job_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, default="", nullable=False)
    conditions: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    score_rules: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    # 画像五维基线 {维度: 0-100}；留空表示该岗位不启用画像契合打分
    ability_requirements: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    headcount: Mapped[int] = mapped_column(Integer, default=1, nullable=False, server_default=text("1"))  # 招聘名额，空缺预警用
    passing_threshold: Mapped[int] = mapped_column(Integer, default=70, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class ProjectDemand(Base):
    __tablename__ = "project_demands"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    project_group: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    position: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    headcount: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    expected_start_date: Mapped[Any | None] = mapped_column(String(32), nullable=True)
    priority: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    remark: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Candidate(Base):
    __tablename__ = "candidates"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    position: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


# ---------------------------------------------------------------- 简历与解析
class ResumeFile(Base, TimestampMixin):
    __tablename__ = "resume_files"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(500), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="waiting", nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(120), nullable=True)
    size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    attachment_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    project_demand_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    job_profile_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    position: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    source_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    # 扩展：行级权限与归属（评审通过）
    dept_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    created_by: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)


class ParseTask(Base, TimestampMixin):
    __tablename__ = "parse_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume_files.id"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="waiting", index=True, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ParseLog(Base):
    __tablename__ = "parse_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    task_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    raw_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    extracted_summary: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class ParsedResume(Base, TimestampMixin):
    __tablename__ = "parsed_resumes"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(ForeignKey("resume_files.id"), index=True, nullable=False)
    project_demand_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    job_profile_id: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education: Mapped[str | None] = mapped_column(String(120), nullable=True)
    major: Mapped[str | None] = mapped_column(String(120), nullable=True)
    skills: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    strengths: Mapped[str] = mapped_column(Text, default="", nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    photo_object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    resume_content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_json: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    # 扩展：人工修正标记（评审通过）；给 DB 默认值，seed 不带该列也能原样加载
    manually_fixed: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default=text("0"), nullable=False
    )
    # 扩展：身份去重（同一人的多份简历只留最新一份为现行）
    # identity_key 形如 "phone:13900000001" / "email:xx@yy"；无可靠身份时为空串
    identity_key: Mapped[str] = mapped_column(
        String(160), default="", server_default=text("''"), index=True, nullable=False
    )
    is_current: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default=text("1"), index=True, nullable=False
    )
    superseded_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 扩展：候选人转正式员工后的账号（需求⑤）
    employee_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------- 匹配
class MatchResult(Base, TimestampMixin):
    __tablename__ = "match_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    parsed_resume_id: Mapped[int] = mapped_column(
        ForeignKey("parsed_resumes.id"), index=True, nullable=False
    )
    job_profile_id: Mapped[int] = mapped_column(
        ForeignKey("job_profiles.id"), index=True, nullable=False
    )
    condition_detail: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class MatchList(Base, TimestampMixin):
    __tablename__ = "match_lists"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_file_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    parsed_resume_id: Mapped[int] = mapped_column(
        ForeignKey("parsed_resumes.id"), index=True, nullable=False
    )
    job_profile_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    job_profile_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)
    age: Mapped[int | None] = mapped_column(Integer, nullable=True)
    education: Mapped[str | None] = mapped_column(String(120), nullable=True)
    major: Mapped[str | None] = mapped_column(String(120), nullable=True)
    skills: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    years_experience: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    strengths: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passing_threshold: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


# ---------------------------------------------------------------- 人才画像
class TalentTag(Base):
    __tablename__ = "talent_tags"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class TalentProfile(Base):
    __tablename__ = "talent_profiles"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    position: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    project_group_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    project_group_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    project_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    profile_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    summary: Mapped[str] = mapped_column(Text, default="", nullable=False)
    strengths: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    weaknesses: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    abilities: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    dimensions: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    tag_ids: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    tag_quantify: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    data_sources: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # 扩展：转正式员工后的账号（需求⑤），便于反查
    employee_user_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


# ---------------------------------------------------------------- 测评
class QuestionBank(Base):
    __tablename__ = "question_banks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    # 扩展：题库受众（需求④）——candidate 面向候选人，employee 面向企业员工
    audience: Mapped[str] = mapped_column(
        String(32), default="candidate", server_default=text("'candidate'"), nullable=False
    )


class Question(Base):
    __tablename__ = "questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    bank_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    serial_no: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="single_choice", nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    options: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    scoring_standard: Mapped[str] = mapped_column(Text, default="", nullable=False)
    analysis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    knowledge_point: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    knowledge_category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    knowledge_base_category: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    subjective: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    operator: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class Exam(Base):
    __tablename__ = "exams"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    bank_ids: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    question_ids: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_score: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    start_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)
    # 扩展：试卷受众（需求④）——建卷时从题库继承
    audience: Mapped[str] = mapped_column(
        String(32), default="candidate", server_default=text("'candidate'"), nullable=False
    )


class ExamSubmission(Base):
    __tablename__ = "exam_submissions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    answers: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, default="", nullable=False)
    detail: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    # 扩展：答卷归属哪份简历（需求④）——NULL 表示历史数据（只按姓名）
    parsed_resume_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)


class ExamAssignment(Base):
    """HR 把试卷绑定给候选人（需求④）。

    一个「简历 × 试卷」只应有一条 pending 记录；提交后置 submitted 并记 submission_id。
    取消置 cancelled，不物理删除，保留审计轨迹。
    """
    __tablename__ = "exam_assignments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    parsed_resume_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True, nullable=False)
    submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    assigned_by: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )


class ExamInterviewResult(Base):
    __tablename__ = "exam_interview_results"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invite_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    pass_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    result: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    result_label: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    next_round_recommended: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    candidate_status: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    notification_status: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    notification_message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    answers: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    detail: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)


class WrongQuestion(Base):
    __tablename__ = "wrong_questions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    bank_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    user_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    standard_answer: Mapped[str] = mapped_column(Text, default="", nullable=False)
    analysis: Mapped[str] = mapped_column(Text, default="", nullable=False)
    score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class ReviewPlan(Base):
    __tablename__ = "review_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    wrong_question_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    question_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    question_type: Mapped[str] = mapped_column(String(32), default="", nullable=False)
    review_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reminder: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="scheduled", nullable=False)


# ---------------------------------------------------------------- 培训
class TrainingCourse(Base):
    __tablename__ = "training_courses"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    category: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    duration_hours: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(32), default="medium", nullable=False)
    instructor: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    content: Mapped[str] = mapped_column(Text, default="", nullable=False)
    exam_id: Mapped[int | None] = mapped_column(Integer, nullable=True)  # 课后考核试卷
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class CourseAttachment(Base):
    __tablename__ = "course_attachments"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    url: Mapped[str] = mapped_column(Text, default="", nullable=False)
    size: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    content_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    upload_failed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)


class PrejobPlan(Base):
    __tablename__ = "prejob_plans"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    roster_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    position_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    plan_title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    goal: Mapped[str] = mapped_column(Text, default="", nullable=False)
    total_weeks: Mapped[int] = mapped_column(Integer, default=4, nullable=False)
    phases: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    course_ids: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    mentor: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="draft", nullable=False)


class PrejobPlanTask(Base, TimestampMixin):
    """岗前培养计划里的单个学习任务：阶段 → 课程 → 考核，带学时与防挂机。"""
    __tablename__ = "prejob_plan_tasks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    plan_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    phase_index: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    title: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    course_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    exam_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    required_minutes: Mapped[int] = mapped_column(Integer, default=30, nullable=False)
    study_minutes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    detail: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)


class GrowthLedger(Base, TimestampMixin):
    """成长台账：每次考核通过或培养完成后，记录某维能力的前后变化。"""
    __tablename__ = "growth_ledger"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    candidate_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    candidate_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    before_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    after_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delta: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source: Mapped[str] = mapped_column(String(32), default="prejob", nullable=False)
    ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note: Mapped[str] = mapped_column(Text, default="", nullable=False)


# ---------------------------------------------------------------- 知识库
class KnowledgeCategory(Base):
    __tablename__ = "knowledge_categories"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)


class BusinessKnowledge(Base):
    __tablename__ = "business_knowledge"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    category_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    title: Mapped[str] = mapped_column(String(256), default="", nullable=False)
    filename: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    attachment_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content_type: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    content_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="not_started", nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    knowledge_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    category_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    milvus_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    score: Mapped[Any | None] = mapped_column(JSON, nullable=True)


# ---------------------------------------------------------------- 智能体 / 调度
class AgentRegistry(Base):
    __tablename__ = "agent_registry"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    category: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="active", nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    endpoint: Mapped[str] = mapped_column(String(500), default="", nullable=False)
    version: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    capabilities: Mapped[Any] = mapped_column(JSON, default=list, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    avg_latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    registered_by: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    retired_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    task_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="", nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    message: Mapped[str] = mapped_column(Text, default="", nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, index=True, nullable=False, server_default=func.now()
    )


class TaskScheduleRule(Base):
    __tablename__ = "task_schedule_rules"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(160), index=True, nullable=False)
    digital_worker: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    agent_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    trigger_rule: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    schedule_type: Mapped[str] = mapped_column(String(32), index=True, default="interval", nullable=False)
    schedule_cron: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    interval_minutes: Mapped[int] = mapped_column(Integer, default=60, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[str] = mapped_column(String(32), index=True, default="enabled", nullable=False)
    retry_policy: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)
    owner: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, index=True, nullable=True)
    run_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    config: Mapped[Any] = mapped_column(JSON, default=dict, nullable=False)


class ModelProvider(Base):
    __tablename__ = "model_providers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    provider_type: Mapped[str] = mapped_column(String(64), index=True, default="", nullable=False)
    base_url: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    api_key: Mapped[str] = mapped_column(String(512), default="", nullable=False)
    model: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
