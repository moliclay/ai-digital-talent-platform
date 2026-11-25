"""P2 向量能力回归：索引 / 语义检索 / 查重 / 岗位语义召回。

依赖：Ollama bge-m3 + Milvus(19530)。任一不可用时接口会返回 available=false，
脚本会把这种情况判为 SKIP（不算失败），但仍要求结构正确。

用法：python tests/backend/p2_test.py [base_url]
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
    print(("PASS" if cond else "FAIL"), name, detail)


st, body = call("POST", "/api/auth/login", body={"username": "hr_zhao", "password": "123456"})
hr = body["data"]["token"]
st, body = call("POST", "/api/auth/login", body={"username": "emp_chen", "password": "123456"})
emp = body["data"]["token"]

# 1) 状态
st, body = call("GET", "/api/vector/status", hr)
d = body.get("data") or {}
embed_ok = (d.get("embed") or {}).get("available") is True
milvus_ok = (d.get("milvus") or {}).get("available") is True
check("向量状态可读", st == 200 and "embed" in d and "milvus" in d, f"embed={embed_ok} milvus={milvus_ok}")

# 2) 建索引（幂等）
st, body = call("POST", "/api/vector/index", hr, {})
d = body.get("data") or {}
res_index = (d.get("resumes") or {}).get("indexed", 0)
job_index = (d.get("jobs") or {}).get("indexed", 0)
# 索引只扫「现行简历」，所以断言应对比现行份数而不是硬编码 6
st_r, body_r = call("GET", "/api/resumes?page_size=200", hr)
current_count = body_r.get("data", {}).get("total", 0)
check("简历+岗位向量索引", st == 200 and res_index == current_count and job_index >= 2,
      f"简历={res_index}（现行 {current_count}）岗位={job_index}",
      skip_if=not (embed_ok and milvus_ok))

# 3) 语义检索
st, body = call("GET", "/api/resumes/semantic?q=%E5%81%9A%E8%BF%87%20RAG%20%E5%92%8C%E5%A4%A7%E6%A8%A1%E5%9E%8B%E7%9A%84%E7%AE%97%E6%B3%95&top_k=5", hr)
d = body.get("data") or {}
items = d.get("items") or []
top3 = [i["name"] for i in items[:3]]
check("自然语言检索返回结果", st == 200 and len(items) >= min(3, current_count), f"top3={top3}", skip_if=not (embed_ok and milvus_ok))
check("技术类候选人排在前面", any(n in ("张伟", "程磊", "陈宇") for n in top3),
      f"top3={top3}", skip_if=not items)

# 4) 岗位语义召回
st, body = call("GET", "/api/job-profiles/3/semantic-candidates?top_k=5", hr)
d = body.get("data") or {}
cands = d.get("items") or []
check("岗位语义召回可用", st == 200 and len(cands) >= min(3, current_count),
      f"前3={[c['name'] for c in cands[:3]]}", skip_if=not (embed_ok and milvus_ok))

# 5) 查重（结构 + 阈值）
st, body = call("GET", "/api/resumes/duplicates?threshold=0.93", hr)
d = body.get("data") or {}
check("查重接口结构正确", st == 200 and "pairs" in d and ("available" in d),
      f"可疑对={d.get('total', 0)}", skip_if=not (embed_ok and milvus_ok))

# 6) 权限：普通员工不能建索引
st, _ = call("POST", "/api/vector/index", emp, {})
check("普通员工不能建索引（403）", st == 403, f"http={st}")

print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}" + (f"，跳过 {len(SKIP)}" if SKIP else ""))
sys.exit(0 if not FAIL else 1)
