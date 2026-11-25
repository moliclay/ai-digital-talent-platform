"""S1 向量字段回归：验证"跑查重不会把语义检索的字段抹空"。

背景：find_duplicates 原来手搓 {id,vector,name} 写 Milvus，upsert 是整行替换，
会把 education/major/skills/filename 覆盖成空。这个脚本专门盯这个回归。

用法：python tests/backend/s1_vector_test.py [base_url]
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


def main() -> int:
    token = login()
    if not token:
        print("登录失败，无法继续")
        return 1

    # 1) 向量能力是否可用
    st, body = call("GET", "/api/vector/status", token)
    status = body.get("data", {})
    milvus = status.get("milvus", {})
    embed_ok = status.get("embed", {}).get("available")
    milvus_ok = milvus.get("available")
    skip = not (embed_ok and milvus_ok)
    check("向量能力可用（Ollama + Milvus）", bool(embed_ok and milvus_ok),
          f"embed={embed_ok} milvus={milvus_ok}", skip_if=skip)
    if skip:
        print("\n跳过剩余用例：向量能力不可用")
        return report()

    # 2) 状态里带 stale / expected_count
    check("status 含 stale 与 expected_count",
          "stale" in milvus and "expected_count" in milvus,
          f"stale={milvus.get('stale')} expected={milvus.get('expected_count')} count={milvus.get('resume_count')}")

    # 3) 重建索引
    st, body = call("POST", "/api/vector/index", token, {})
    indexed = body.get("data", {}).get("resumes", {})
    check("重建索引成功", indexed.get("indexed", 0) > 0,
          f"indexed={indexed.get('indexed')} total={indexed.get('total')}")

    # 4) 重建后检索，字段必须完整
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=3", token)
    before = body.get("data", {}).get("items", [])
    before_ok = bool(before) and all(i.get("education") and i.get("filename") for i in before)
    check("重建后检索字段完整", before_ok,
          f"{[(i.get('name'), i.get('education')) for i in before]}")

    # 5) 跑查重
    st, body = call("GET", "/api/resumes/duplicates?threshold=0.5", token)
    dup = body.get("data", {})
    check("查重可用", dup.get("available") is True, f"pairs={dup.get('total')}")

    # 6) 【核心回归】查重后检索字段仍在
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=3", token)
    after = body.get("data", {}).get("items", [])
    after_ok = bool(after) and all(i.get("education") and i.get("filename") for i in after)
    check("★ 查重后检索字段仍完整（原 bug 回归点）", after_ok,
          f"{[(i.get('name'), i.get('education'), i.get('skills_count')) for i in after]}")

    # 7) 新增字段齐全
    need = {"parsed_resume_id", "name", "education", "major", "years_experience",
            "skills_top", "skills_count", "filename", "score", "accessible"}
    missing = need - set(after[0].keys()) if after else need
    check("检索项含 brief 全部字段", not missing,
          f"缺={sorted(missing)}" if missing else "字段齐全")

    # 8) 连跑两次查重，字段仍然完整（幂等）
    call("GET", "/api/resumes/duplicates?threshold=0.5", token)
    call("GET", "/api/resumes/duplicates?threshold=0.5", token)
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=3", token)
    third = body.get("data", {}).get("items", [])
    check("连续 3 次查重后字段仍完整", bool(third) and all(i.get("education") for i in third),
          f"{[i.get('education') for i in third]}")

    # 9) 幂等重建：行数已对时不应重建
    st, body = call("POST", "/api/vector/reindex-if-stale", token, {})
    re = body.get("data", {})
    check("reindex-if-stale 幂等（不重复重建）", re.get("rebuilt") is False,
          f"rebuilt={re.get('rebuilt')} count={re.get('count')} expected={re.get('expected')}")

    # 10) 岗位语义召回字段回 MySQL
    st, body = call("GET", "/api/job-profiles/3/semantic-candidates?top_k=3", token)
    cand = body.get("data", {}).get("items", [])
    check("岗位召回字段完整", bool(cand) and all(i.get("education") for i in cand),
          f"{[(i.get('name'), i.get('education'), i.get('similarity')) for i in cand]}")

    # 11) 权限：员工不能建索引
    emp = login("emp_chen")
    if emp:
        st, _b = call("POST", "/api/vector/index", emp, {})
        check("员工不能建索引（403）", st == 403, f"http={st}")

    return report()


def report() -> int:
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
