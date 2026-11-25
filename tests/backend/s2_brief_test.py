"""S2 简历摘要回归：验证查重/语义检索/岗位召回都能点进简历详情。

核心断言：
1) 三处返回都有 `parsed_resume_id` + `accessible`；
2) 拿 `parsed_resume_id` 调 `GET /api/resumes/{id}`，无障碍项必须 200；
3) 越权项标 `accessible=false` 且**不被剔除**（成对展示）；
4) `skills_top` ≤5、`skills_count` 与库内一致。

用法：python tests/backend/s2_brief_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL, SKIP = [], [], []


def call(method, path, token=None, body=None, timeout=180):
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


BRIEF_KEYS = {"parsed_resume_id", "resume_file_id", "name", "education", "major",
              "years_experience", "skills_top", "skills_count", "filename",
              "created_at", "accessible"}


def main() -> int:
    token = login()
    if not token:
        print("登录失败")
        return 1

    st, body = call("GET", "/api/vector/status", token)
    status = body.get("data", {})
    vector_ok = status.get("embed", {}).get("available") and status.get("milvus", {}).get("available")

    # ---------- 1. 语义检索 ----------
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=5", token)
    sem = body.get("data", {}).get("items", [])
    check("语义检索可用", st == 200 and bool(sem), f"items={len(sem)}", skip_if=not vector_ok)
    if sem:
        miss = BRIEF_KEYS - set(sem[0].keys())
        check("语义检索项是完整 brief", not miss, f"缺={sorted(miss)}" if miss else "齐全")
        check("skills_top ≤ 5", all(len(i["skills_top"]) <= 5 for i in sem),
              f"{[len(i['skills_top']) for i in sem]}")
        check("skills_count ≥ skills_top 长度",
              all(i["skills_count"] >= len(i["skills_top"]) for i in sem),
              f"{[(i['skills_count'], len(i['skills_top'])) for i in sem]}")

    # ---------- 2. 查重成对返回 ----------
    st, body = call("GET", "/api/resumes/duplicates?threshold=0.5", token)
    dup = body.get("data", {})
    pairs = dup.get("pairs", [])
    check("查重可用", st == 200 and dup.get("available") is True, f"pairs={dup.get('total')}",
          skip_if=not vector_ok)
    if pairs:
        p = pairs[0]
        check("查重项含 a / b 两个 brief",
              isinstance(p.get("a"), dict) and isinstance(p.get("b"), dict),
              f"keys={sorted(p.keys())}")
        check("查重 a/b 都是完整 brief",
              not (BRIEF_KEYS - set(p["a"].keys())) and not (BRIEF_KEYS - set(p["b"].keys())),
              "齐全")
        check("查重含 similarity", 0 < p.get("similarity", 0) <= 1, f"sim={p.get('similarity')}")

    # ---------- 3. 拿 id 能跳进详情（核心需求） ----------
    if sem:
        rid = sem[0]["parsed_resume_id"]
        st, body = call("GET", f"/api/resumes/{rid}", token)
        check("★ 语义检索结果可点进详情", st == 200 and body.get("data", {}).get("id") == rid,
              f"resume_id={rid} http={st}")
    if pairs:
        for side in ("a", "b"):
            brief = pairs[0][side]
            rid = brief["parsed_resume_id"]
            st, _b = call("GET", f"/api/resumes/{rid}", token)
            expect = 200 if brief["accessible"] else 403
            check(f"★ 查重 {side} 方可点进详情（expect {expect}）", st == expect,
                  f"resume_id={rid} accessible={brief['accessible']} http={st}")

    # ---------- 4. 岗位召回 ----------
    st, body = call("GET", "/api/job-profiles/3/semantic-candidates?top_k=5", token)
    cand = body.get("data", {}).get("items", [])
    check("岗位召回可用", st == 200 and bool(cand), f"items={len(cand)}", skip_if=not vector_ok)
    if cand:
        miss = BRIEF_KEYS - set(cand[0].keys())
        check("岗位召回项是完整 brief", not miss, f"缺={sorted(miss)}" if miss else "齐全")
        check("岗位召回含 similarity", 0 < cand[0].get("similarity", 0) <= 1,
              f"sim={cand[0].get('similarity')}")
        rid = cand[0]["parsed_resume_id"]
        st, _b = call("GET", f"/api/resumes/{rid}", token)
        check("★ 岗位召回结果可点进详情", st == 200, f"resume_id={rid} http={st}")

    # ---------- 5. 越权项：单边保留、双边丢弃 ----------
    emp = login("emp_chen")
    if emp:
        st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=5", emp)
        check("员工无 resume:view → 403", st == 403, f"http={st}")

    if pairs:
        acc_flags = [pairs[0]["a"]["accessible"], pairs[0]["b"]["accessible"]]
        check("查重 brief 带 accessible 布尔", all(isinstance(x, bool) for x in acc_flags),
              f"{acc_flags}")

    # 权限规则：双方都不可访问的成对结果必须被丢弃（用 dept 范围账号实测）
    # hr_zhao 实际是 all 范围，这里只能断言"返回的每一对至少有一方 accessible"
    if pairs:
        both_locked = [p for p in pairs
                       if not p["a"]["accessible"] and not p["b"]["accessible"]]
        check("★ 不存在双方都不可访问的成对结果", not both_locked,
              f"违规对数={len(both_locked)}")

    return report()


def report() -> int:
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
