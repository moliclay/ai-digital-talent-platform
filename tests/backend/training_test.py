"""培训模块冒烟测试：走真实 HTTP，覆盖诊断→计划→防挂机→考核→台账→权限。

用法：python tests/backend/training_test.py [base_url]
退出码 0 = 全部通过。需要在后端已重启（加载了 training 路由）之后运行。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL = [], []


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json; charset=utf-8")
    if token:
        req.add_header("Authorization", "Bearer " + token)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"code": e.code, "message": "http"}


def login(username: str) -> str:
    _, body = call("POST", "/api/auth/login", body={"username": username, "password": "123456"})
    return body["data"]["token"]


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, detail)


hr = login("hr_zhao")
emp = login("emp_chen")

# 陈宇的现行简历 id（身份去重后旧简历 id=1 已被 id=6 替代，关联数据随之迁移）
# 硬编码 id=1 会在身份去重后失效，所以动态解析「陈宇 + is_current」的那一条
_st, _b = call("GET", "/api/resumes?page_size=200", hr)
CHENYU = next((r["id"] for r in _b.get("data", {}).get("items", [])
               if r["name"] == "陈宇" and r.get("is_current")), 1)
print(f"（陈宇现行简历 id={CHENYU}）")

# 1) 课程目录（HR 可读，普通员工无 train 权限 → 403）
st, body = call("GET", "/api/training-courses", hr)
check("课程目录可读", st == 200 and body["data"]["total"] >= 5, f"total={body['data']['total']}")
# 需求⑤：员工已获 train:view(self)，可以读课程目录，但只能看到自己的计划/台账
st2, body2 = call("GET", "/api/training-courses", emp)
check("普通员工可读课程目录（train:view self）", st2 == 200,
      f"http={st2} total={body2.get('data', {}).get('total')}")
st3, _b3 = call("GET", f"/api/training/diagnose?candidate_id={CHENYU}&job_id=3", emp)
check("★ 普通员工不能查他人培训诊断（403）", st3 == 403, f"http={st3}")

# 2) 缺口诊断
st, body = call("GET", f"/api/training/diagnose?candidate_id={CHENYU}&job_id=3", hr)
gaps = body["data"]["gaps"]
check("缺口诊断可用", st == 200 and len(gaps) == 5 and any(g["gap"] > 0 for g in gaps),
      f"候选={body['data']['candidate_name']} 缺口维度数={sum(1 for g in gaps if g['gap']>0)}")

# 3) 生成培养计划（幂等）
st, body = call("POST", "/api/prejob-plans/generate", hr, {"candidate_id": CHENYU, "job_id": 3, "weeks": 6, "mentor": "李工"})
plan = body["data"]
check("生成培养计划", st == 200 and plan["total_weeks"] == 6 and plan["tasks"],
      f"任务数={len(plan['tasks'])} 标题={plan['plan_title']}")
task = next((t for t in plan["tasks"] if not t.get("exam_id")), None)
check("普通学习任务存在", task is not None)
if task is None:
    sys.exit(1)
plan_id = plan["id"]

# 4) 防挂机：未学习就 complete → 400
st, body = call("POST", f"/api/prejob-plans/tasks/{task['id']}/complete", hr)
check("防挂机拦截（未学习直接完成）", st == 400, f"http={st} msg={body.get('message')}")

# 5) 学习达标后完成
st, _ = call("POST", f"/api/prejob-plans/tasks/{task['id']}/progress", hr, {"minutes": 999, "progress": 100})
st, body = call("POST", f"/api/prejob-plans/tasks/{task['id']}/complete", hr)
check("学时达标后可完成", st == 200 and body["data"]["status"] == "done", f"status={body['data']['status']}")

# 6) 课后考核 → 台账 + 画像提升（找带 exam_id 的任务）
exam_task = next((t for t in plan["tasks"] if t.get("exam_id")), None)
if exam_task:
    # 使用隔离库中明确关联当前候选人和课程试卷的提交。
    st, paper = call("GET", f"/api/exams/{exam_task['exam_id']}", hr)
    st, questions = call("GET", "/api/questions?page_size=200", hr)
    standards = {q["id"]: q["answer"] for q in questions["data"]["items"]}
    answers = [{"question_id": q["id"], "answer": standards[q["id"]]} for q in paper["data"]["questions"]]
    st, submission = call("POST", f"/api/exams/{exam_task['exam_id']}/submit", hr, {"candidate_name": "陈宇", "parsed_resume_id": CHENYU, "answers": answers})
    check("明确绑定的课后测评提交成功", st == 200 and submission.get("data", {}).get("passed") is True, str(st))
    if st != 200:
        sys.exit(1)
    st, body = call("POST", f"/api/prejob-plans/tasks/{exam_task['id']}/assess", hr, {"submission_id": submission["data"]["submission_id"]})
    check("课后考核通过", st == 200 and body["data"]["status"] == "done", f"status={body['data']['status']}")
    st, body = call("GET", f"/api/training/ledger?candidate_id={CHENYU}", hr)
    ledger = (body.get("data") or {}).get("items", [])
    check("成长台账有记录", st == 200 and bool(ledger) and ledger[0]["delta"] > 0,
          f"记录数={len(ledger)}")
else:
    FAIL.append("课后考核任务存在")
    print("FAIL 课后考核任务存在（计划里没有 exam_id 的任务）")

# 7) 计划列表
st, body = call("GET", f"/api/prejob-plans?candidate_id={CHENYU}", hr)
check("计划列表可读", st == 200 and body["data"]["total"] >= 1, f"total={body['data']['total']}")

print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
sys.exit(0 if not FAIL else 1)
