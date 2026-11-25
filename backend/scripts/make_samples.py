"""生成三份不同格式的示例简历（PDF / DOCX / TXT），用于真实上传与解析验证。

内容为虚构脱敏数据，仅用于演示与回归。
"""
from __future__ import annotations

import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = BACKEND_DIR.parent / "tests" / "samples"

CHEN = {
    "name": "张伟",
    "gender": "男",
    "age": "28",
    "phone": "13900000011",
    "email": "zhangwei@demo.com",
    "education": "硕士",
    "major": "计算机科学与技术",
    "years": "5",
    "skills": "Python、PyTorch、NLP、分布式训练、Milvus",
    "summary": "5 年算法经验，主导推荐系统与大模型微调，熟悉推理优化与向量检索。",
    "projects": [
        "2023–2026 某平台推荐系统：负责召回与排序模型，离线 AUC 提升 6%，线上 CTR 提升 3.2%。",
        "2024 大模型微调项目：基于 LoRA 完成行业模型 SFT，推理时延下降 40%。",
        "参与搭建 RAG 检索链路，使用 Milvus 承载 200 万级向量。",
    ],
}

WANG = {
    "name": "刘洋",
    "gender": "男",
    "age": "30",
    "phone": "13900000012",
    "email": "liuyang@demo.com",
    "education": "本科",
    "major": "信息管理与信息系统",
    "years": "6",
    "skills": "需求分析、项目管理、Axure、产品设计",
    "summary": "6 年产品经验，负责 AI 平台产品设计与落地，擅长复杂需求拆解。",
    "projects": [
        "2022–2026 AI 平台产品线：完成 3 个中台产品的需求分析与版本规划。",
        "主导 B 端客户需求调研 40+ 场，输出 PRD 与原型，交付准时率 95%。",
    ],
}

LI = {
    "name": "李娜",
    "gender": "女",
    "age": "26",
    "phone": "13900000003",
    "email": "lina@demo.com",
    "education": "本科",
    "major": "软件工程",
    "years": "3",
    "skills": "React、Vue、TypeScript、CSS、数据可视化",
    "summary": "3 年前端经验，负责中后台系统与数据看板开发。",
    "projects": [
        "2023–2026 企业后台系统：基于 React + TypeScript 搭建 30+ 页面，首屏 1.2s。",
        "使用 ECharts 完成运营看板，支撑 200+ 指标展示。",
    ],
}


def text_of(p: dict) -> str:
    lines = [
        f"姓名：{p['name']}",
        f"性别：{p['gender']}    年龄：{p['age']}    学历：{p['education']}",
        f"专业：{p['major']}",
        f"手机：{p['phone']}    邮箱：{p['email']}",
        f"工作年限：{p['years']} 年",
        "",
        "技能：" + p["skills"],
        "",
        "个人优势",
        p["summary"],
        "",
        "项目经历",
    ]
    lines += [f"- {item}" for item in p["projects"]]
    return "\n".join(lines)


def make_pdf(path: Path, p: dict) -> None:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfgen import canvas

    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    c = canvas.Canvas(str(path), pagesize=A4)
    c.setFont("STSong-Light", 12)
    y = 800
    for line in text_of(p).splitlines():
        if y < 60:
            c.showPage()
            c.setFont("STSong-Light", 12)
            y = 800
        c.drawString(56, y, line)
        y -= 20
    c.save()


def make_docx(path: Path, p: dict) -> None:
    import docx

    document = docx.Document()
    for line in text_of(p).splitlines():
        document.add_paragraph(line)
    document.save(str(path))


def make_txt(path: Path, p: dict) -> None:
    path.write_text(text_of(p), encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    make_pdf(OUT_DIR / "张伟_算法工程师.pdf", CHEN)
    make_docx(OUT_DIR / "刘洋_AI产品经理.docx", WANG)
    make_txt(OUT_DIR / "李娜_前端工程师.txt", LI)
    # 加一份"扫描件"占位（周敏）：纯图片 bytes，用来验证 need_ocr 分支
    (OUT_DIR / "扫描件_周敏.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 64)
    for f in sorted(OUT_DIR.iterdir()):
        print(f"{f.name:32s} {f.stat().st_size:>8} bytes")


if __name__ == "__main__":
    sys.exit(main())
