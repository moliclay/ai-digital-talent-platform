"""P1 三项能力的回归测试（走 HTTP，AI 可用走 AI，不可用必须自动降级且结构一致）。

用法：python tests/backend/p1_test.py [base_url]
退出码 0 = 全部通过。注意：这里断言的是**结构与降级行为**，不是"AI 一定成功"——
网关抖动时 source 会是 rule/ai_rule，但返回必须完整可用。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL = [], []


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


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, detail)


st, body = call("POST", "/api/auth/login", body={"username": "hr_zhao", "password": "123456"})
hr = body["data"]["token"]
st, body = call("POST", "/api/auth/login", body={"username": "emp_chen", "password": "123456"})
emp = body["data"]["token"]

# ---------- P1-1 JD 解析 ----------
JD = """岗位名称：资深算法工程师（大模型方向）
岗位职责：负责大模型在业务场景落地，包括 RAG 检索链路、微调与推理优化；与产品、数据团队协作推进。
任职要求：
1. 硕士及以上学历，计算机、人工智能、数学相关专业；
2. 5 年以上算法工程经验；
3. 精通 Python、PyTorch，熟悉 LangChain、向量数据库；
4. 有 RAG、Agent 项目落地经验优先。"""

st, body = call("POST", "/api/job-profiles/parse-jd", hr, {"text": JD})
d = body.get("data") or {}
draft = d.get("draft") or {}
conds = draft.get("conditions") or []
keys = {c["key"] for c in conds}
check("JD 解析返回草稿", st == 200 and d.get("source") in {"ai", "rule", "ai_rule"},
      f"source={d.get('source')}")
check("JD 抽出学历+年限+技能", {"学历", "工作年限", "技能"} <= keys, f"keys={sorted(keys)}")
check("JD 权重合计 100", sum((draft.get("score_rules") or {}).get("weights", {}).values()) == 100,
      f"weights={(draft.get('score_rules') or {}).get('weights')}")
check("JD 草稿不落库（只返回 draft）", "id" not in draft)

st, _ = call("POST", "/api/job-profiles/parse-jd", emp, {"text": JD})
check("普通员工不能解析 JD（403）", st == 403, f"http={st}")

# ---------- P1-2 自适应组卷 ----------
st, body = call("POST", "/api/exams/adaptive", hr, {"candidate_name": "陈宇", "count": 6})
d = body.get("data") or {}
exam = d.get("exam") or {}
qs = d.get("questions") or []
rat = d.get("rationale") or {}
check("自适应组卷成功", st == 200 and exam.get("id") and len(qs) == exam.get("total_questions"),
      f"题数={len(qs)} 总分={exam.get('total_score')}")
check("组卷给出理由（薄弱点/弱维度）",
      isinstance(rat.get("weak_dimensions"), list) and isinstance(rat.get("weak_points"), list),
      f"weak_dims={rat.get('weak_dimensions')}")
check("题目按难度递增排列",
      [q["difficulty"] for q in qs] == sorted([q["difficulty"] for q in qs],
                                              key=lambda x: {"easy": 1, "medium": 2, "hard": 3}.get(x, 2)))
check("组卷覆盖了错题知识点", rat.get("covered", 0) >= 1, f"covered={rat.get('covered')}")

# ---------- P1-3 能力结构分析 ----------
st, body = call("GET", "/api/talent-profiles", hr)
profiles = (body.get("data") or {}).get("items", [])
profile_id = next((p["id"] for p in profiles if p.get("name") == "陈宇"), None)
check("种子画像存在", profile_id is not None)
if profile_id is None:
    sys.exit(1)
st, body = call("GET", f"/api/talent-profiles/{profile_id}/analysis?job_id=3", hr)
d = body.get("data") or {}
rep = d.get("report") or {}
check("分析报告返回结构完整",
      st == 200 and rep.get("headline") and isinstance(rep.get("risks"), list)
      and isinstance(rep.get("actions"), list),
      f"source={d.get('source')}")
check("分析基于事实（含五维与评级）",
      (d.get("facts") or {}).get("abilities") and (d.get("facts") or {}).get("rating"),
      f"overall={(d.get('facts') or {}).get('rating', {}).get('overall')}")
check("有岗位时会算基线差距", isinstance((d.get("facts") or {}).get("job_gaps"), list))

print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
sys.exit(0 if not FAIL else 1)
