"""演示数据补齐：在 seed_data.sql 基础上补足回归测试所需的题目、课程与错题。

为什么需要它：`init_db.py --reset` 只加载 seed_data.sql（3 题 / 2 课 / 1 错题），
而 `training_test.py` / `p1_test.py` 需要 5 门课、覆盖五维的题目与错题。
历史上这些是手工补的，reset 一次就丢。固化成脚本后可重复执行、幂等。

用法：python scripts/seed_demo_extra.py
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from sqlalchemy import select  # noqa: E402

from app.core.db import SessionLocal  # noqa: E402
from app.models.orm import Question, QuestionBank, TrainingCourse  # noqa: E402

# 题目：覆盖五个能力维度（knowledge_category 决定折进画像哪一维）
QUESTIONS = [
    ("single_choice", "Transformer 注意力机制的核心计算是什么？",
     ["A. 矩阵乘法 QKV", "B. 卷积", "C. 池化", "D. 归一化"], "A", 20, "hard", "算法", "Transformer"),
    ("single_choice", "下列哪项最能提升大模型推理速度？",
     ["A. 增加层数", "B. 量化与 KV Cache", "C. 扩大词表", "D. 提高学习率"], "B", 20, "medium", "模型", "推理优化"),
    ("single_choice", "RAG 检索增强的主要作用是？",
     ["A. 减少显存", "B. 引入外部知识降低幻觉", "C. 加速训练", "D. 压缩模型"], "B", 20, "medium", "模型", "RAG"),
    ("single_choice", "Kubernetes 中用于暴露服务的资源对象是？",
     ["A. Pod", "B. Service", "C. ConfigMap", "D. Secret"], "B", 20, "easy", "部署", "K8s"),
    ("single_choice", "数据库索引最直接影响的是？",
     ["A. 写入放大与查询速度", "B. 磁盘容量", "C. 网络带宽", "D. CPU 主频"], "A", 20, "medium", "数据库", "索引"),
    ("single_choice", "转化漏斗分析主要衡量什么？",
     ["A. 各环节流失率", "B. 服务器负载", "C. 代码覆盖率", "D. 磁盘 IO"], "A", 20, "easy", "业务", "转化漏斗"),
    ("single_choice", "跨部门冲突最有效的处理方式是？",
     ["A. 上报领导", "B. 明确目标与接口人后对齐", "C. 搁置", "D. 各做各的"], "B", 20, "medium", "沟通", "跨部门协作"),
    ("single_choice", "复盘方法中最关键的一步是？",
     ["A. 追责", "B. 找到可改进的具体动作", "C. 写总结", "D. 开会"], "B", 20, "easy", "成长", "复盘"),
    ("essay", "请说明你如何评估一个模型上线前的风险，列出至少三个检查项。",
     [], "显存占用、推理延迟、数据漂移监控、灰度发布、回滚方案", 30, "hard", "工程", "上线评估"),
]

COURSES = [
    ("大模型微调实战", "LoRA / SFT 实操，含数据构造与评测", "技术深度", 8, "hard", "算法组"),
    ("产品需求分析方法", "从用户访谈到需求优先级排序", "业务理解", 6, "medium", "产品组"),
    ("高并发服务工程实践", "缓存、限流、异步与压测", "工程能力", 10, "hard", "平台组"),
    ("跨部门协作与沟通", "目标对齐、冲突处理、接口人机制", "协作沟通", 4, "easy", "HR"),
    ("职业成长与复盘方法", "周复盘、能力盘点、成长路径设计", "成长性", 3, "easy", "HR"),
]

# 课后考核：给课程挂一份试卷，培养计划的「考核」环节才有 exam_id
COURSE_EXAM = {
    "大模型微调实战": "算法工程师内测",
    "产品需求分析方法": "算法工程师内测",
}


def _attach_course_exams(db) -> int:
    """给课程挂课后考核试卷。返回挂上的数量。"""
    from app.models.orm import Exam

    attached = 0
    for course_name, exam_name in COURSE_EXAM.items():
        course = db.execute(select(TrainingCourse).where(TrainingCourse.name == course_name)).scalar_one_or_none()
        if course is None or course.exam_id:
            continue
        exam = db.execute(select(Exam).where(Exam.name == exam_name)).scalar_one_or_none()
        if exam is None:
            continue
        course.exam_id = exam.id
        attached += 1
    return attached


def main() -> int:
    with SessionLocal() as db:
        bank = db.execute(select(QuestionBank).where(QuestionBank.name == "算法基础题库")).scalar_one_or_none()
        if bank is None:
            bank = QuestionBank(name="算法基础题库", description="覆盖五维能力的基础题",
                                total_questions=0, status="active")
            db.add(bank)
            db.flush()

        existing = {q.content for q in db.execute(
            select(Question).where(Question.bank_id == bank.id)).scalars()}
        added_q = 0
        for qtype, content, options, answer, score, difficulty, category, point in QUESTIONS:
            if content in existing:
                continue
            db.add(Question(
                bank_id=bank.id, question_type=qtype, content=content, options=options,
                answer=answer, score=score, difficulty=difficulty,
                knowledge_category=category, knowledge_point=point,
                subjective=(qtype == "essay"), status="active",
            ))
            added_q += 1
        db.flush()
        bank.total_questions = db.execute(
            select(Question).where(Question.bank_id == bank.id)).scalars().all().__len__()

        existing_c = {c.name for c in db.execute(select(TrainingCourse)).scalars()}
        added_c = 0
        for name, desc, category, hours, difficulty, instructor in COURSES:
            if name in existing_c:
                continue
            db.add(TrainingCourse(name=name, description=desc, category=category,
                                  duration_hours=hours, difficulty=difficulty,
                                  instructor=instructor, content="", status="active"))
            added_c += 1

        db.commit()
        print(f"题目 +{added_q}（题库共 {bank.total_questions} 题）；课程 +{added_c}")

        # 课程挂课后考核（重置后 exam_id 会丢）
        attached = _attach_course_exams(db)
        db.commit()
        print(f"课程挂考核 +{attached}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
