"""S6 题库文件导入回归（需求⑥）。

覆盖：
1) 上传 txt/md/csv/docx/xlsx → 返回草稿，不落库
2) 规则解析：单选/多选/填空/简答四种题型识别正确
3) 校验：答案不在选项内 → needs_review；选项不足 → 降级填空；空题干 → 丢弃
4) 确认落库：created 数量与草稿一致；重复题干幂等跳过
5) 不支持格式 → 400
6) 权限：员工不能导入
7) AI 不可用时 source=rule，仍能导入（降级不阻断）

用法：python tests/backend/s6_import_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:18080"
PASS, FAIL, SKIP = [], [], []

SAMPLE = """单选题
1. Transformer 注意力机制的核心计算是什么？
A. 矩阵乘法 QKV
B. 卷积运算
C. 池化降维
D. 归一化
答案：A
解析：QKV 三组矩阵相乘得到注意力权重

2. Kubernetes 中用于暴露服务的资源对象是？
A. Pod
B. Service
C. ConfigMap
答案：B

多选题
3. 下列哪些属于大模型推理优化手段？
A. 量化
B. KV Cache
C. 增加层数
D. 批处理
答案：A,B,D

填空题
4. 数据库索引最直接影响的是____与查询速度。
答案：写入放大

简答题
5. 请说明你如何评估模型上线前的风险。
答案：显存占用、推理延迟、数据漂移监控、灰度发布
"""

# 故意造一份"格式有问题"的题库
BAD_SAMPLE = """1. 这道题答案不在选项里
A. 选项甲
B. 选项乙
答案：Z

2. 这道题只有一个选项
A. 唯一选项
答案：A

3.

4. 正常题
A. 甲
B. 乙
答案：A
"""


def call(method, path, token=None, body=None, timeout=180, raw=None, content_type=None):
    if raw is not None:
        req = urllib.request.Request(BASE + path, data=raw, method=method)
        req.add_header("Content-Type", content_type or "application/octet-stream")
    else:
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
            return e.code, {"code": e.code}


def check(name, cond, detail="", skip_if=None):
    if skip_if:
        SKIP.append(name)
        print("SKIP", name, detail)
        return
    (PASS if cond else FAIL).append(name)
    print("PASS" if cond else "FAIL", name, "—", detail)


def login(username="hr_zhao", password="123456"):
    st, body = call("POST", "/api/auth/login", body={"username": username, "password": password})
    return body.get("data", {}).get("token")


def upload(token, bank_id, filename, content: str, mime="text/plain"):
    boundary = "----S6Boundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n{content}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    return call("POST", f"/api/question-banks/{bank_id}/import", token, raw=body,
                content_type=f"multipart/form-data; boundary={boundary}")


def upload_bytes(token, bank_id, filename, data: bytes, mime="application/octet-stream"):
    boundary = "----S6Boundary7MA4YWxkTrZu0gW"
    head = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    tail = f"\r\n--{boundary}--\r\n".encode("utf-8")
    return call("POST", f"/api/question-banks/{bank_id}/import", token, raw=head + data + tail,
                content_type=f"multipart/form-data; boundary={boundary}")


def make_docx(text: str) -> bytes:
    import io

    import docx

    d = docx.Document()
    for line in text.splitlines():
        d.add_paragraph(line)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def make_xlsx(rows: list[list[str]]) -> bytes:
    import io

    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def main() -> int:
    st, health = call("GET", "/api/health")
    if st != 200 or (health.get("data") or {}).get("env") != "test":
        raise RuntimeError("题库导入回归需要独立测试环境")
    hr = login()
    if not hr:
        print("登录失败")
        return 1

    created_banks: list[int] = []

    # ---------- 1. 建一个专用题库 ----------
    st, body = call("POST", "/api/question-banks", hr,
                    {"name": "S6导入验证题库", "description": "导入测试", "audience": "candidate"})
    bank_id = body.get("data", {}).get("id")
    check("建导入专用题库", st == 200 and bank_id, f"bank_id={bank_id}")
    if not bank_id:
        return report(created_banks, hr)
    created_banks.append(bank_id)

    # ---------- 2. txt 导入（规则解析） ----------
    st, body = upload(hr, bank_id, "题库样例.txt", SAMPLE)
    d = body.get("data") or {}
    check("★ txt 导入返回草稿", st == 200 and d.get("parsed_count", 0) >= 5,
          f"source={d.get('source')} parsed={d.get('parsed_count')} ai={d.get('ai_available')}")
    draft = d.get("draft") or []

    types = [q["question_type"] for q in draft]
    check("★ 四种题型都识别到",
          set(types) >= {"single_choice", "multi_choice", "fill_blank", "essay"},
          f"types={types}")
    check("草稿不落库（返回体无 id）", "id" not in d, f"keys={sorted(d.keys())[:6]}")

    # 检查多选题答案保留 A,B,D
    multi = next((q for q in draft if q["question_type"] == "multi_choice"), None)
    check("多选题答案保留多选", multi and "A" in multi["answer"] and "D" in multi["answer"],
          f"answer={multi['answer'] if multi else None}")

    # 填空题分数默认 10、简答 20
    fill = next((q for q in draft if q["question_type"] == "fill_blank"), None)
    essay = next((q for q in draft if q["question_type"] == "essay"), None)
    check("填空题默认 10 分", fill and fill["score"] == 10, f"score={fill['score'] if fill else None}")
    check("简答题默认 20 分", essay and essay["score"] == 20, f"score={essay['score'] if essay else None}")

    # 自动推断知识分类
    cats = [q["knowledge_category"] for q in draft]
    check("自动推断知识分类（非空）", any(cats), f"cats={cats}")

    # ---------- 3. 确认落库 ----------
    st, body = call("POST", f"/api/question-banks/{bank_id}/import/confirm", hr, {"questions": draft})
    c = body.get("data") or {}
    check("★ 确认落库", st == 200 and c.get("created", 0) == len(draft),
          f"created={c.get('created')} skipped={c.get('skipped')} failed={c.get('failed_count')} bank_total={c.get('bank_total')}")

    st, body = call("GET", f"/api/questions?bank_id={bank_id}&page_size=50", hr)
    total = body.get("data", {}).get("total", 0)
    check("题库题目数已更新", total == len(draft), f"total={total} expect={len(draft)}")

    # 幂等：重复确认同一批
    st, body = call("POST", f"/api/question-banks/{bank_id}/import/confirm", hr, {"questions": draft})
    c2 = body.get("data") or {}
    check("★ 重复导入幂等（同题干跳过）", c2.get("created") == 0 and c2.get("skipped") == len(draft),
          f"created={c2.get('created')} skipped={c2.get('skipped')}")

    # ---------- 4. 格式有问题的题库 ----------
    st, body = upload(hr, bank_id, "格式问题.txt", BAD_SAMPLE)
    d2 = body.get("data") or {}
    draft2 = d2.get("draft") or []
    warnings = d2.get("warnings") or []
    print(f"  （格式问题题库：source={d2.get('source')} parsed={len(draft2)} "
          f"types={[q['question_type'] for q in draft2]} review={[q.get('needs_review') for q in draft2]}）")
    check("★ 答案不在选项内 → 标 needs_review",
          any(q.get("needs_review") for q in draft2),
          f"needs_review={[q.get('needs_review') for q in draft2]}")
    # 选项只有 1 个的题必须降级成填空（AI 与规则两条链路都要过校验）
    single_opt = [q for q in draft2 if len(q.get("options") or []) == 1]
    check("★ 选项不足 2 个 → 降级填空题",
          bool(single_opt) and all(q["question_type"] == "fill_blank" for q in single_opt),
          f"单选项题={len(single_opt)} 其题型={[q['question_type'] for q in single_opt]}")
    check("★ 空题干被丢弃", len(draft2) < 4, f"parsed={len(draft2)}")
    check("★ warnings 逐条点名", len(warnings) >= 2, f"warnings={warnings}")

    # ---------- 5. docx 导入 ----------
    docx_bytes = make_docx(SAMPLE)
    st, body = upload_bytes(hr, bank_id, "题库样例.docx", docx_bytes,
                            "application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    d3 = body.get("data") or {}
    check("★ docx 导入可用", st == 200 and d3.get("parsed_count", 0) >= 5,
          f"parsed={d3.get('parsed_count')} source={d3.get('source')}")

    # ---------- 6. xlsx 导入 ----------
    xlsx_rows = [
        ["题型", "题干", "选项A", "选项B", "选项C", "选项D", "答案", "分值", "分类"],
        ["单选", "下列哪个是 Python 的 Web 框架？", "Django", "Nginx", "MySQL", "Redis", "A", "10", "工程能力"],
        ["单选", "HTTP 状态码 404 表示？", "成功", "未找到", "服务器错误", "重定向", "B", "10", "工程能力"],
    ]
    xlsx_bytes = make_xlsx(xlsx_rows)
    st, body = upload_bytes(hr, bank_id, "题库样例.xlsx", xlsx_bytes,
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    d4 = body.get("data") or {}
    check("★ xlsx 导入可用", st == 200 and d4.get("parsed_count", 0) >= 1,
          f"parsed={d4.get('parsed_count')} source={d4.get('source')} warnings={(d4.get('warnings') or [])[:1]}")

    # ---------- 7. 不支持格式 ----------
    st, body = upload(hr, bank_id, "不支持.rar", "fake")
    check("不支持的格式 → 400", st == 400, f"http={st} msg={body.get('message')}")

    # ---------- 8. 权限 ----------
    emp = login("emp_chen")
    if emp:
        st, body = upload(emp, bank_id, "权限测试.txt", SAMPLE)
        check("员工不能导入题库（403）", st == 403, f"http={st}")

    # ---------- 9. 空文件 ----------
    st, body = upload(hr, bank_id, "空文件.txt", "")
    check("空文件 → 400", st == 400, f"http={st} msg={body.get('message')}")

    return report(created_banks, hr)


def report(banks: list[int], token: str) -> int:
    if banks:
        print(f"保留 {len(banks)} 个隔离测试题库，随验收环境统一清理")
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
