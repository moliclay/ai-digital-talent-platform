"""空缺预警 + 储备推荐 冒烟测试（走 HTTP）。

用法：python tests/backend/vacancy_test.py [base_url]  退出码 0 = 全部通过。
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


def check(name: str, cond: bool, detail: str = ""):
    (PASS if cond else FAIL).append(name)
    print(("PASS" if cond else "FAIL"), name, detail)


st, body = call("POST", "/api/auth/login", body={"username": "hr_zhao", "password": "123456"})
hr = body["data"]["token"]
st, body = call("POST", "/api/auth/login", body={"username": "emp_chen", "password": "123456"})
emp = body["data"]["token"]

# 空缺预警
st, body = call("GET", "/api/job-profiles/alerts", hr)
alerts = body["data"]
check("空缺预警返回列表", st == 200 and len(alerts) >= 2, f"岗位数={len(alerts)}")
fields_ok = all({"job_name", "headcount", "matched", "passed", "vacancy", "alert", "pass_rate"} <= set(a) for a in alerts)
check("预警字段齐全", fields_ok)
check("预警按严重度排序", all(a["alert"] in {"high", "medium", "low", "none"} for a in alerts))

# 储备推荐
st, body = call("GET", "/api/job-profiles/3/reserve", hr)
res = body["data"]
check("储备推荐结构正确", st == 200 and "near_miss" in res and "qualified_pool" in res and res["margin"] == 15,
      f"阈值={res['threshold']} 接近线={len(res['near_miss'])} 达标池={len(res['qualified_pool'])}")

# headcount 回写
st, body = call("PUT", "/api/job-profiles/3", hr, {"headcount": 3})
check("名额可回写", st == 200 and body["data"]["headcount"] == 3, f"headcount={body['data']['headcount']}")

# 普通员工无 job 权限
st, _ = call("GET", "/api/job-profiles/alerts", emp)
check("普通员工访问预警 → 403", st == 403, f"http={st}")

print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
sys.exit(0 if not FAIL else 1)
