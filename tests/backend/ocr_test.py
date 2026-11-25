"""扫描件 OCR 端到端测试：上传图片版 PDF → 解析队列 → 字段核对 → 清理。

用法：python tests/backend/ocr_test.py [base_url]
依赖：3065 多模态模型（Doubao-Seed-2.1-Turbo）+ PyMuPDF 渲染。
单份耗时约 1–2 分钟（模型侧延迟），脚本超时给 300 秒。
"""
from __future__ import annotations

import json
import pathlib
import sys
import time
import urllib.error
import urllib.request
import uuid

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL = [], []

TRUTH = {
    "name": "李娜", "phone": "13900002222", "email": "lina.scan@example.com",
    "education": "本科", "major": "软件工程", "years_experience": 3,
}


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, detail)


def build_scanned_pdf() -> bytes:
    import fitz

    text = (
        "姓名：李娜\n性别：女  年龄：26\n学历：本科\n专业：软件工程\n"
        "工作年限：3 年\n手机：13900002222\n邮箱：lina.scan@example.com\n"
        "技能：Vue、React、JavaScript、TypeScript\n"
    )
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((60, 80), text, fontsize=12, fontname="china-s")
    png = page.get_pixmap(matrix=fitz.Matrix(2, 2)).tobytes("png")
    # 只放图片 → 没有文本层，模拟扫描件
    scanned = fitz.open()
    p2 = scanned.new_page(width=595, height=842)
    p2.insert_image(fitz.Rect(0, 0, 595, 842), stream=png)
    return scanned.tobytes()


def post_multipart(path: str, token: str, filename: str, data: bytes, timeout=300):
    boundary = "----hermes" + uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
        f"Content-Type: application/pdf\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def call(method, path, token=None, body=None, timeout=300):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {}


def main() -> int:
    st, body = call("POST", "/api/auth/login", body={"username": "hr_zhao", "password": "123456"})
    token = body["data"]["token"]

    pdf = build_scanned_pdf()
    up = post_multipart("/api/resumes/upload", token, f"扫描件_{uuid.uuid4().hex[:6]}.pdf", pdf)
    items = (up.get("data") or {}).get("items") or []
    check("扫描件上传成功", bool(items), f"返回 {len(items)} 条")
    if not items:
        return 1
    resume_id = items[0]["id"] if "id" in items[0] else items[0].get("resume_id")

    t0 = time.time()
    parsed_ok = False
    for _ in range(3):
        st, body = call("POST", "/api/resumes/parse-next", token)
        d = body.get("data") or {}
        if d.get("parsed") or d.get("task_id") is None:
            parsed_ok = True
            break
        time.sleep(1)
    elapsed = time.time() - t0
    check("解析任务已消费", parsed_ok, f"{elapsed:.1f}s")

    st, body = call("GET", f"/api/resumes/{resume_id}", token)
    d = (body.get("data") or {}) if st == 200 else {}
    fields = d.get("parsed") or d
    check("解析结果 ok", d.get("parse_status") in (None, "completed") or d.get("status") == "completed",
          f"status={d.get('parse_status') or d.get('status')}")

    hits = {k: (str(fields.get(k)) if fields.get(k) is not None else "") for k in TRUTH}
    matched = sum(1 for k, v in TRUTH.items() if str(hits[k]).strip() == str(v))
    print("   实际字段:", hits)
    check("OCR 字段命中 ≥5/6", matched >= 5, f"{matched}/6")
    check("识别出姓名", hits["name"] == TRUTH["name"], hits["name"])
    check("识别出手机", hits["phone"].replace("-", "") == TRUTH["phone"], hits["phone"])

    # 清理：删掉测试简历（含解析结果、任务、日志、向量）
    from app.core.db import engine
    from sqlalchemy import text
    from app.infrastructure.vector_store import store
    from app.core.config import settings

    with engine.begin() as c:
        pid = c.execute(text("SELECT id FROM parsed_resumes WHERE resume_id=:r"), {"r": resume_id}).scalar()
        if pid:
            store.delete(settings.milvus_resume_collection, [int(pid)])
            c.execute(text("DELETE FROM match_results WHERE parsed_resume_id=:p"), {"p": pid})
            c.execute(text("DELETE FROM match_lists WHERE parsed_resume_id=:p"), {"p": pid})
            c.execute(text("DELETE FROM talent_profiles WHERE candidate_id=:p"), {"p": pid})
            c.execute(text("DELETE FROM parsed_resumes WHERE id=:p"), {"p": pid})
        c.execute(text("DELETE FROM parse_tasks WHERE resume_id=:r"), {"r": resume_id})
        c.execute(text("DELETE FROM parse_logs WHERE resume_id=:r"), {"r": resume_id})
        c.execute(text("DELETE FROM resume_files WHERE id=:r"), {"r": resume_id})
    print("   已清理测试简历")

    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    raise SystemExit(main())
