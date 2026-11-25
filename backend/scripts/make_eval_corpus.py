"""生成评测语料（P0-3）：32 份合成简历 + 解析标注 + 匹配标注。

设计原则（避免"自标自测"）：
- 解析标注的**真值由生成器写入**（姓名/手机/邮箱/学历/专业/年限），解析器不知道；
- 匹配标注的期望值只依据**岗位硬条件**推导（学历/技能/年限），不复用匹配引擎的评分逻辑；
- 语料故意包含不同排版（标签块/段落式/松散标签/首行姓名），让准确率反映真实水平而不是全绿。
"""
from __future__ import annotations

import json
import pathlib
import random

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
ROOT = BACKEND_DIR.parent
OUT_DIR = ROOT / "tests" / "data"
RES_DIR = OUT_DIR / "eval_resumes"

random.seed(42)

NAMES = ["张伟", "王芳", "李强", "刘敏", "陈杰", "杨帆", "赵磊", "黄婷",
         "周涛", "吴静", "徐亮", "孙悦", "马超", "朱琳", "胡斌", "郭蕾",
         "何勇", "高翔", "林雪", "罗浩", "郑爽", "梁宇", "谢楠", "唐倩",
         "许巍", "邓超", "曹阳", "彭博", "曾毅", "肖楠", "田莉", "董浩"]
EDUS = ["博士", "硕士", "硕士", "本科", "本科", "本科", "本科", "大专"]
MAJORS = ["计算机科学与技术", "软件工程", "人工智能", "信息管理", "电子信息",
          "数学与应用数学", "自动化", "统计学", "网络工程", "数据科学"]
SKILLS = ["Python", "PyTorch", "TensorFlow", "机器学习", "深度学习", "SQL", "Java", "Go",
          "JavaScript", "React", "Vue", "Docker", "Kubernetes", "需求分析", "产品设计",
          "项目管理", "数据分析", "Redis", "MySQL", "大模型"]
CITIES = ["北京", "上海", "杭州", "深圳", "成都"]


def make_case(i: int) -> dict:
    name = NAMES[i % len(NAMES)]
    edu = EDUS[i % len(EDUS)]
    major = MAJORS[i % len(MAJORS)]
    years = [0, 1, 2, 3, 3, 4, 5, 5, 6, 7, 8, 10][i % 12]
    phone = f"13{6 + i % 4}{i:02d}{i * 37 % 10000:04d}{i * 13 % 10000:04d}"[:11]
    email = f"user{i:02d}@{random.choice(['example.com', 'mail.com', 'test.cn'])}"
    skills = random.sample(SKILLS, k=random.randint(3, 6))
    gender = "男" if i % 2 == 0 else "女"
    age = 24 + years + (i % 5)
    return {"id": f"RS-{i + 1:02d}", "name": name, "phone": phone, "email": email,
            "education": edu, "major": major, "years_experience": years,
            "skills": skills, "gender": gender, "age": age,
            "city": CITIES[i % len(CITIES)]}


def render(case: dict, variant: int) -> str:
    s = "、".join(case["skills"])
    if variant == 0:  # 标准标签块
        return (f"姓名：{case['name']}\n性别：{case['gender']}    年龄：{case['age']}\n"
                f"学历：{case['education']}\n专业：{case['major']}\n"
                f"工作年限：{case['years_experience']} 年\n手机：{case['phone']}\n"
                f"邮箱：{case['email']}\n技能：{s}\n")
    if variant == 1:  # 段落式
        return (f"{case['name']}，{case['gender']}，{case['age']} 岁，{case['education']}，"
                f"{case['major']}专业，{case['years_experience']} 年工作经验。\n"
                f"联系电话 {case['phone']}，邮箱 {case['email']}。\n"
                f"熟悉 {s} 等技术，期望工作城市：{case['city']}。\n")
    if variant == 2:  # 松散标签 + 带分隔符的电话
        p = case["phone"]
        loose = f"{p[:3]}-{p[3:7]}-{p[7:]}"
        return (f"姓 名：{case['name']}\n最高学历：{case['education']}\n"
                f"所学专业：{case['major']}\n工作经验：{case['years_experience']} 年\n"
                f"电 话：{loose}\nEmail: {case['email']}\n专业技能：{s}\n")
    # 首行姓名（无标签）
    return (f"{case['name']}\n{case['gender']} {case['age']}岁 {case['education']} {case['major']}\n"
            f"{case['years_experience']}年工作经验\n手机 {case['phone']}\n邮箱 {case['email']}\n"
            f"技能：{s}\n")


def write_docx(path: pathlib.Path, text: str) -> None:
    from docx import Document
    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(path)


def write_pdf(path: pathlib.Path, text: str) -> None:
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c = canvas.Canvas(str(path))
    c.setFont("STSong-Light", 11)
    y = 800
    for line in text.split("\n"):
        c.drawString(50, y, line)
        y -= 18
    c.save()


def main() -> None:
    RES_DIR.mkdir(parents=True, exist_ok=True)
    cases, parse_rows, match_rows = [], [], []

    jobs = [
        {"id": "J-ALG", "name": "岗位A（评测）", "threshold": 70,
         "conditions": [{"key": "学历", "op": ">=", "value": "硕士"},
                        {"key": "技能", "op": "contains", "value": ["Python", "PyTorch"]},
                        {"key": "工作年限", "op": ">=", "value": 3}],
         "weights": {"education": 25, "skills": 40, "experience": 20, "project": 10, "other": 5}},
        {"id": "J-PRD", "name": "岗位B（评测）", "threshold": 65,
         "conditions": [{"key": "学历", "op": ">=", "value": "本科"},
                        {"key": "技能", "op": "contains", "value": ["需求分析", "SQL"]},
                        {"key": "工作年限", "op": ">=", "value": 2}],
         "weights": {"education": 20, "skills": 40, "experience": 20, "project": 15, "other": 5}},
        {"id": "J-FE", "name": "岗位C（评测）", "threshold": 70,
         "conditions": [{"key": "学历", "op": ">=", "value": "大专"},
                        {"key": "技能", "op": "contains", "value": ["JavaScript", "React"]},
                        {"key": "工作年限", "op": ">=", "value": 1}],
         "weights": {"education": 15, "skills": 45, "experience": 20, "project": 15, "other": 5}},
    ]

    EDU_RANK = {"博士": 5, "硕士": 4, "本科": 3, "大专": 2, "高中": 1}

    for i in range(32):
        case = make_case(i)
        variant = 0 if i % 10 < 4 else 1 if i % 10 < 7 else 2 if i % 10 < 9 else 3
        text = render(case, variant)
        fmt = "txt" if i < 22 else "docx" if i < 28 else "pdf"
        path = RES_DIR / f"{case['id']}_{case['name']}.{fmt}"
        if fmt == "txt":
            path.write_text(text, encoding="utf-8")
        elif fmt == "docx":
            write_docx(path, text)
        else:
            write_pdf(path, text)

        parse_rows.append({
            "id": case["id"], "file": f"eval_resumes/{path.name}", "format": fmt,
            "variant": variant, "ground_truth": {k: case[k] for k in
                ("name", "phone", "email", "education", "major", "years_experience")},
            "expected_skills": case["skills"],
        })
        case["file"] = f"eval_resumes/{path.name}"
        case["format"] = fmt
        cases.append(case)

    # 匹配标注：每个岗位 6 过 + 6 不过，按硬条件直接构造（保证期望值与构造一致）
    EDU_ORDER = ["高中", "大专", "本科", "硕士", "博士"]
    for job in jobs:
        req_edu = next(x["value"] for x in job["conditions"] if x["key"] == "学历")
        req_skills = next(x["value"] for x in job["conditions"] if x["key"] == "技能")
        req_years = next(x["value"] for x in job["conditions"] if x["key"] == "工作年限")
        edu_ok_pool = [e for e in EDU_ORDER if EDU_ORDER.index(e) >= EDU_ORDER.index(req_edu)]
        edu_bad_pool = [e for e in EDU_ORDER if EDU_ORDER.index(e) < EDU_ORDER.index(req_edu)]

        n = 0
        # 6 条必须通过
        for k in range(6):
            edu = edu_ok_pool[k % len(edu_ok_pool)]
            years = req_years + k
            extra = [s for s in SKILLS if s not in req_skills][k % 4]
            n += 1
            match_rows.append({
                "id": f"{job['id']}-P{n:02d}", "job_id": job["id"],
                "resume": {"name": f"{job['name'][:2]}候选{n}", "education": edu,
                           "years_experience": years,
                           "skills": list(req_skills) + ([extra] if extra else [])},
                "job": job,
                "expected": {"outcome": "must_pass", "threshold": job["threshold"],
                             "reason_contains": [req_skills[0]]},
                "why": f"学历{edu}≥{req_edu}、技能全覆盖、{years}年≥{req_years}年",
            })
        # 6 条必须不通过（学历/技能/年限各两条）
        for k in range(6):
            mode = k % 3
            edu, years, skills = edu_ok_pool[0], req_years + 2, list(req_skills)
            reason = ""
            if mode == 0:
                edu = edu_bad_pool[-1] if edu_bad_pool else edu_ok_pool[0]
                reason = f"学历{edu}<{req_edu}"
            elif mode == 1:
                skills = list(req_skills[1:])
                reason = f"缺技能{req_skills[0]}"
            else:
                years = max(0, req_years - 2)
                reason = f"年限{years}<{req_years}"
            n += 1
            match_rows.append({
                "id": f"{job['id']}-F{n:02d}", "job_id": job["id"],
                "resume": {"name": f"{job['name'][:2]}候选{n}", "education": edu,
                           "years_experience": years, "skills": skills},
                "job": job,
                "expected": {"outcome": "must_fail", "threshold": job["threshold"],
                             "reason_contains": [req_edu]},
                "why": "硬条件不满足：" + reason,
            })

    (OUT_DIR / "resume_parse_eval_30.json").write_text(
        json.dumps(parse_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "match_eval_30.json").write_text(
        json.dumps({"jobs": jobs, "cases": match_rows}, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"语料生成完成：{len(parse_rows)} 份简历（txt/docx/pdf），匹配标注 {len(match_rows)} 条")
    print("输出：", OUT_DIR)


if __name__ == "__main__":
    main()
