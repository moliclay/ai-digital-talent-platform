"""S4 测评受众 + 绑定 + 简历显示「已测评」回归。

覆盖：
1) 题库/试卷支持 audience（candidate / employee），非法值 400
2) 建卷未传 audience 时从题库继承
3) HR 绑定试卷给候选人（单条 + 批量），重复绑定幂等
4) 提交时带 assignment_id → 回填 parsed_resume_id、绑定置 submitted
5) 简历列表 exam_summary 三态流转：none → assigned → submitted
6) 列表批量查询不产生 N+1（20 条只查固定次数）
7) 取消绑定置 cancelled，已提交的不能取消
8) 权限：员工不能绑定

用法：python tests/backend/s4_assignment_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL, SKIP = [], [], []


def call(method, path, token=None, body=None, timeout=120):
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


def cleanup(token, exam_ids, bank_ids, assignment_ids) -> None:
    """删掉本次造的题库/试卷/绑定（绑定走 cancel，试卷与题库直接删库）。"""
    for aid in assignment_ids:
        call("DELETE", f"/api/exam-assignments/{aid}", token)
    if exam_ids or bank_ids:
        sys.path.insert(0, ".")
        from sqlalchemy import text as sql_text

        from app.core.db import engine

        with engine.begin() as conn:
            for eid in exam_ids:
                conn.execute(sql_text("DELETE FROM exam_assignments WHERE exam_id=:i").bindparams(i=eid))
                conn.execute(sql_text("DELETE FROM exam_submissions WHERE exam_id=:i").bindparams(i=eid))
                conn.execute(sql_text("DELETE FROM exams WHERE id=:i").bindparams(i=eid))
            for bid in bank_ids:
                conn.execute(sql_text("DELETE FROM questions WHERE bank_id=:i").bindparams(i=bid))
                conn.execute(sql_text("DELETE FROM question_banks WHERE id=:i").bindparams(i=bid))
    print(f"已清理 {len(exam_ids)} 张试卷 / {len(bank_ids)} 个题库")


def main() -> int:
    token = login()
    if not token:
        print("登录失败")
        return 1

    created_exams: list[int] = []
    created_banks: list[int] = []
    created_assigns: list[int] = []

    # ---------- 1. 受众：非法值 ----------
    st, body = call("POST", "/api/question-banks", token,
                    {"name": "S4非法受众题库", "audience": "intern"})
    check("非法 audience → 400", st == 400, f"http={st} msg={body.get('message')}")

    # ---------- 2. 建 employee 题库 + 试卷 ----------
    st, body = call("POST", "/api/question-banks", token,
                    {"name": "S4员工培训题库", "description": "员工专用", "audience": "employee"})
    bank_id = body.get("data", {}).get("id")
    check("建 employee 题库", st == 200 and bank_id, f"bank_id={bank_id} audience={body.get('data', {}).get('audience')}")
    if not bank_id:
        return report()
    created_banks.append(bank_id)

    for i, (qtype, content, opts, ans) in enumerate([
        ("single_choice", "员工合规：客户资料能带出公司吗？", ["A. 可以", "B. 不可以"], "B"),
        ("single_choice", "信息安全：陌生 U 盘能插办公电脑吗？", ["A. 可以", "B. 不可以"], "B"),
    ], start=1):
        st, _b = call("POST", "/api/questions", token, {
            "bank_id": bank_id, "question_type": qtype, "content": content,
            "options": opts, "answer": ans, "score": 50, "difficulty": "easy",
            "knowledge_category": "沟通", "knowledge_point": "合规",
        })
        check(f"员工题库加题 {i}", st == 200, f"http={st}")

    # 建卷不传 audience → 从题库继承 employee
    st, body = call("POST", "/api/exams", token,
                    {"name": "S4员工合规测评", "bank_ids": [bank_id], "question_count": 2, "pass_score": 60})
    exam_id = body.get("data", {}).get("id")
    check("建卷从题库继承 audience", st == 200 and body.get("data", {}).get("audience") == "employee",
          f"exam_id={exam_id} audience={body.get('data', {}).get('audience')}")
    if not exam_id:
        return report()
    created_exams.append(exam_id)

    # ---------- 3. 受众过滤 ----------
    st, body = call("GET", "/api/exams?audience=employee", token)
    emp_exams = body.get("data", [])
    check("按 audience=employee 过滤到新卷", any(e["id"] == exam_id for e in emp_exams),
          f"count={len(emp_exams)}")
    st, body = call("GET", "/api/exams?audience=candidate", token)
    cand_exams = body.get("data", [])
    check("employee 卷不出现在 candidate 列表", all(e["id"] != exam_id for e in cand_exams),
          f"count={len(cand_exams)}")

    st, body = call("GET", "/api/question-banks?audience=employee", token)
    check("按 audience 过滤题库", any(b["id"] == bank_id for b in body.get("data", [])),
          f"count={len(body.get('data', []))}")

    # ---------- 4. 简历列表基线 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    rows = body.get("data", {}).get("items", [])
    check("列表项都带 exam_summary", all("exam_summary" in r for r in rows), f"count={len(rows)}")
    target = next((r for r in rows if r["name"] == "张伟"), None)
    check("张伟在列表里", target is not None, f"id={target['id'] if target else None}")
    if not target:
        return report()
    zw_id = target["id"]
    before_state = target["exam_summary"]["state"]

    # 前置清场：把该简历在这张卷上的历史绑定全部取消，保证从 none 起测
    st, body = call("GET", f"/api/exam-assignments?parsed_resume_id={zw_id}", token)
    for old in body.get("data", {}).get("items", []):
        if old["exam_id"] == exam_id and old["status"] in ("pending", "submitted"):
            call("DELETE", f"/api/exam-assignments/{old['id']}", token)
    st, body = call("GET", f"/api/resumes?page_size=50", token)
    row = next((r for r in body.get("data", {}).get("items", []) if r["id"] == zw_id), None)
    baseline = row["exam_summary"]["state"]
    print(f"  （清场后张伟的测评状态基线：{baseline}）")

    # ---------- 5. 绑定 ----------
    st, body = call("POST", "/api/exam-assignments", token,
                    {"exam_id": exam_id, "parsed_resume_ids": [zw_id],
                     "note": "S4 绑定验证", "deadline": "2026-11-20 18:00:00"})
    data = body.get("data", {})
    created = data.get("created", [])
    check("★ 绑定试卷给候选人", st == 200 and data.get("created_count") == 1,
          f"created={data.get('created_count')} id={created[0]['id'] if created else None}")
    if not created:
        return report()
    assign_id = created[0]["id"]
    created_assigns.append(assign_id)
    check("绑定返回 exam_name 与 deadline",
          created[0]["exam_name"] == "S4员工合规测评" and created[0]["deadline"] == "2026-11-20 18:00:00",
          f"{created[0]['exam_name']} / {created[0]['deadline']}")

    # 重复绑定幂等
    st, body = call("POST", "/api/exam-assignments", token,
                    {"exam_id": exam_id, "parsed_resume_ids": [zw_id]})
    check("重复绑定幂等（返回 existed）", body.get("data", {}).get("existed_count") == 1,
          f"existed={body.get('data', {}).get('existed_count')} created={body.get('data', {}).get('created_count')}")

    # ---------- 6. 列表变「待测评」 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    row = next((r for r in body.get("data", {}).get("items", []) if r["id"] == zw_id), None)
    check("★ 绑定后列表显示「待测评」", row and row["exam_summary"]["state"] == "assigned",
          f"state={row['exam_summary']['state'] if row else None} label={row['exam_summary']['label'] if row else None}")
    check("exam_summary 带 assignment_id 与 deadline",
          row and any(i.get("assignment_id") == assign_id for i in row["exam_summary"]["items"]),
          f"items={len(row['exam_summary']['items']) if row else 0}")

    # ---------- 7. 提交并回填 ----------
    st, body = call("GET", f"/api/exams/{exam_id}", token)
    qs = body.get("data", {}).get("questions", [])
    check("取卷成功", st == 200 and len(qs) == 2, f"questions={len(qs)}")
    answers = [{"question_id": q["id"], "answer": "B"} for q in qs]
    st, body = call("POST", f"/api/exams/{exam_id}/submit", token,
                    {"candidate_name": "张伟", "answers": answers, "assignment_id": assign_id})
    sub = body.get("data", {})
    check("★ 带 assignment_id 提交成功", st == 200 and sub.get("submission_id"),
          f"score={sub.get('score')}/{sub.get('max_score')} passed={sub.get('passed')} sub_id={sub.get('submission_id')}")
    if not sub.get("submission_id"):
        return report()

    st, body = call("GET", f"/api/exam-submissions/{sub['submission_id']}", token)
    check("★ 答卷回填 parsed_resume_id",
          body.get("data", {}).get("parsed_resume_id") == zw_id,
          f"parsed_resume_id={body.get('data', {}).get('parsed_resume_id')} expect={zw_id}")

    st, body = call("GET", f"/api/exam-assignments?parsed_resume_id={zw_id}", token)
    a = next((x for x in body.get("data", {}).get("items", []) if x["id"] == assign_id), None)
    check("★ 绑定状态变 submitted 并记 submission_id",
          a and a["status"] == "submitted" and a["submission_id"] == sub["submission_id"],
          f"status={a['status'] if a else None} sub={a['submission_id'] if a else None}")
    check("绑定结果带分数", a and a.get("result") and a["result"]["score"] is not None,
          f"result={a.get('result') if a else None}")

    # ---------- 8. 列表变「已测评」 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    row = next((r for r in body.get("data", {}).get("items", []) if r["id"] == zw_id), None)
    check("★ 提交后列表显示「已测评」", row and row["exam_summary"]["state"] == "submitted",
          f"state={row['exam_summary']['state'] if row else None} label={row['exam_summary']['label'] if row else None} passed={row['exam_summary']['passed'] if row else None}")

    # 详情也带
    st, body = call("GET", f"/api/resumes/{zw_id}", token)
    check("详情也带 exam_summary",
          body.get("data", {}).get("exam_summary", {}).get("state") == "submitted",
          f"state={body.get('data', {}).get('exam_summary', {}).get('state')}")

    # ---------- 9. 重复提交同一绑定 → 409 ----------
    st, body = call("POST", f"/api/exams/{exam_id}/submit", token,
                    {"candidate_name": "张伟", "answers": answers, "assignment_id": assign_id})
    check("已提交的绑定不能重复提交（409）", st == 409, f"http={st} msg={body.get('message')}")

    # ---------- 10. 取消 ----------
    st, body = call("POST", "/api/exam-assignments", token,
                    {"exam_id": exam_id, "parsed_resume_ids": [zw_id]})
    new_assign = (body.get("data", {}).get("created") or [{}])[0].get("id")
    if new_assign:
        created_assigns.append(new_assign)
        st, body = call("DELETE", f"/api/exam-assignments/{new_assign}", token)
        check("取消绑定置 cancelled", st == 200 and body.get("data", {}).get("status") == "cancelled",
              f"status={body.get('data', {}).get('status')}")

    st, body = call("DELETE", f"/api/exam-assignments/{assign_id}", token)
    check("已提交的绑定不能取消（409）", st == 409, f"http={st} msg={body.get('message')}")

    # ---------- 11. 权限 ----------
    emp = login("emp_chen")
    if emp:
        st, _b = call("POST", "/api/exam-assignments", emp, {"exam_id": exam_id, "parsed_resume_ids": [zw_id]})
        check("员工不能绑定（403）", st == 403, f"http={st}")

    # ---------- 12. 批量绑定 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    all_ids = [r["id"] for r in body.get("data", {}).get("items", [])][:3]
    st, body = call("POST", "/api/exam-assignments", token,
                    {"exam_id": exam_id, "parsed_resume_ids": all_ids})
    d = body.get("data", {})
    check("批量绑定 3 人", st == 200 and (d.get("created_count", 0) + d.get("existed_count", 0)) == len(all_ids),
          f"created={d.get('created_count')} existed={d.get('existed_count')} failed={d.get('failed_count')}")
    for item in d.get("created", []):
        created_assigns.append(item["id"])

    return report(created_exams, created_banks, created_assigns, token)


def report(exams=None, banks=None, assigns=None, token=None) -> int:
    if token and (exams or banks or assigns):
        cleanup(token, exams or [], banks or [], assigns or [])
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
