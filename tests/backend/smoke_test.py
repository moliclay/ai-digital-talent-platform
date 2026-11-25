"""接口冒烟测试：用四个演示账号走一遍真实 HTTP，断言权限与主流程。

用法：python tests/backend/smoke_test.py [base_url]
退出码 0 = 全部通过。
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL = [], []


def call(method: str, path: str, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"raw": raw}


def check(name: str, condition: bool, detail: str = "") -> None:
    (PASS if condition else FAIL).append(name)
    print(f"{'PASS' if condition else 'FAIL'}  {name}" + (f"  — {detail}" if detail else ""))


def login(username: str) -> str:
    status, body = call("POST", "/api/auth/login", body={"username": username, "password": "123456"})
    check(f"登录 {username}", status == 200 and body.get("code") == 0,
          f"http={status} code={body.get('code')} scope={(body.get('data') or {}).get('user', {}).get('data_scope')}")
    return ((body.get("data") or {}).get("token") or "")


def main() -> int:
    status, body = call("GET", "/api/health")
    check("健康检查", status == 200 and body["data"]["mysql"], f"redis={body['data']['redis']}")

    hr = login("hr_zhao")
    pm = login("pm_wang")
    emp = login("emp_chen")
    admin = login("admin")

    status, body = call("GET", "/api/resumes?page=1&page_size=20", hr)
    items = (body.get("data") or {}).get("items") or []
    check("HR 可读简历（dept 范围）", status == 200 and len(items) >= 2, f"条数={len(items)}（seed 2 条 + 上传样例）")

    status, body = call("GET", "/api/resumes", pm)
    check("业务负责人访问简历被拒（无菜单权限）", status == 403, f"http={status} {body.get('message')}")

    status, body = call("GET", "/api/system/users", emp)
    check("普通员工访问系统管理被拒", status == 403, f"http={status}")

    status, body = call("GET", "/api/system/users", admin)
    # 不写死数量：转正建号会增加员工账号，断言「能读到且含基线 4 个账号」更稳
    users = (body.get("data") or {}).get("items") or []
    names = {u.get("username") for u in users}
    check("管理员可读系统用户",
          status == 200 and len(users) >= 4 and {"admin", "hr_zhao", "pm_wang", "emp_chen"} <= names,
          f"http={status} total={len(users)}")

    status, body = call("GET", "/api/job-profiles", hr)
    jobs = (body.get("data") or {}).get("items") or []
    check("岗位条件列表可读", status == 200 and len(jobs) >= 2, f"条数={len(jobs)}")
    job_ids = {j["name"]: j["id"] for j in jobs}
    algo_id = next((jid for name, jid in job_ids.items() if "算法" in name), None)

    status, body = call("GET", "/api/matching/lists", pm)
    check("业务负责人可读匹配名单（dept 范围）", status == 200, f"http={status}")

    if algo_id:
        status, body = call("POST", "/api/matching/run", hr, {"job_profile_id": algo_id})
        data = body.get("data") or {}
        check("HR 执行匹配", status == 200 and data.get("scanned", 0) >= 2,
              f"scanned={data.get('scanned')} passed={data.get('passed')} failed={data.get('failed')}")

        status, body = call("GET", f"/api/matching/lists?job_profile_id={algo_id}", hr)
        rows = (body.get("data") or {}).get("items") or []
        check("匹配名单有结果且分数在 0-100", bool(rows) and all(0 <= r["total_score"] <= 100 for r in rows),
              f"条数={len(rows)} 分数={[r['total_score'] for r in rows]}")

        if rows:
            status, body = call("GET", f"/api/matching/{rows[0]['id']}", hr)
            detail = body.get("data") or {}
            check("匹配详情含可解释原因与五维构成",
                  status == 200 and bool(detail.get("reason")) and bool((detail.get("detail") or {}).get("dimensions")),
                  f"reason={str(detail.get('reason'))[:40]}…")

    status, body = call("GET", "/api/dashboard/overview", hr)
    data = body.get("data") or {}
    check("工作台概览可用", status == 200 and "files" in data, f"files={data.get('files')}")

    status, body = call("GET", "/api/system/operation-logs?page_size=5", admin)
    logs = (body.get("data") or {}).get("items") or []
    check("操作日志已留痕", status == 200 and len(logs) > 0, f"条数={len(logs)}")

    status, body = call("GET", "/api/resumes/1", admin)
    check("管理员可读单份简历详情", status == 200, f"http={status}")

    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
    if FAIL:
        print("失败项：" + "；".join(FAIL))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
