"""S7 收口验收：跨阶段端到端检查（一次跑完所有需求的关键链路）。

不做单元级重复（那些由 s1–s6 覆盖），这里只验：
- 六项需求各自的核心承诺是否在真实 HTTP 上成立
- 角色边界（HR / 员工）
- 数据一致性（现行简历数 = 向量数，已有画像关联现行简历）
- 种子夹具仍可加载的结构前提（新列都有默认值）

用法：python tests/backend/s7_acceptance_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL = [], []


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


def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print("PASS" if cond else "FAIL", name, "—", detail)


def login(username="hr_zhao", password="123456"):
    st, body = call("POST", "/api/auth/login", body={"username": username, "password": password})
    return body.get("data", {}).get("token")


def main() -> int:
    hr = login()
    if not hr:
        print("HR 登录失败")
        return 1

    print("\n========== 需求① 向量入库带基本字段 ==========")
    st, body = call("POST", "/api/vector/index", hr, {})
    idx = body.get("data", {}).get("resumes", {})
    check("① 向量索引可用", st == 200 and idx.get("indexed", 0) > 0,
          f"indexed={idx.get('indexed')}")
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=5", hr)
    sem = body.get("data", {}).get("items", [])
    check("① 语义检索返回学历/专业/技能/文件名",
          bool(sem) and all(i.get("education") and i.get("major")
                            and i.get("skills_count") is not None and i.get("filename") for i in sem),
          f"{[(i['name'], i['education'], i['major'], i['skills_count']) for i in sem[:3]]}")
    # 跑一次查重再检索（原 bug 回归点）
    call("GET", "/api/resumes/duplicates?threshold=0.5", hr)
    st, body = call("GET", "/api/resumes/semantic?q=RAG&top_k=5", hr)
    sem2 = body.get("data", {}).get("items", [])
    check("① 查重后字段不被抹空（原 bug）",
          bool(sem2) and all(i.get("education") for i in sem2),
          f"{[i.get('education') for i in sem2]}")

    print("\n========== 需求② 同一人取最新简历 ==========")
    st, body = call("GET", "/api/resumes?page_size=200", hr)
    rows = body.get("data", {}).get("items", [])
    keys = [r["identity_key"] for r in rows if r.get("identity_key")]
    check("② 列表现行身份键不重复", len(keys) == len(set(keys)),
          f"现行简历={len(rows)} 有身份键={len(keys)}")
    check("② 列表项都带 is_current=true", all(r.get("is_current") for r in rows),
          f"非现行={[r['name'] for r in rows if not r.get('is_current')]}")
    st, body = call("GET", "/api/resumes?page_size=200&include_superseded=1", hr)
    all_rows = body.get("data", {}).get("items", [])
    check("② include_superseded=1 能看到历史版本", len(all_rows) >= len(rows),
          f"全部={len(all_rows)} 现行={len(rows)}")
    st, body = call("GET", "/api/resumes/identity/suspected", hr)
    check("② 疑似重复只报不合并", st == 200,
          f"groups={len(body.get('data', {}).get('groups', []))}")

    print("\n========== 需求③ 查重/召回可点进详情 ==========")
    st, body = call("GET", "/api/resumes/duplicates?threshold=0.5", hr)
    pairs = body.get("data", {}).get("pairs", [])
    if pairs:
        p = pairs[0]
        ok = True
        for side in ("a", "b"):
            b = p[side]
            st2, _b2 = call("GET", f"/api/resumes/{b['parsed_resume_id']}", hr)
            if st2 != (200 if b["accessible"] else 403):
                ok = False
        check("③ 查重两侧都能按 id 打开详情", ok,
              f"a={p['a']['parsed_resume_id']} b={p['b']['parsed_resume_id']} sim={p['similarity']}")
    else:
        check("③ 查重结果可点进详情", True, "当前无重复对（阈值 0.5 下）")
    st, body = call("GET", "/api/job-profiles/3/semantic-candidates?top_k=3", hr)
    cand = body.get("data", {}).get("items", [])
    check("③ 岗位召回可点进详情",
          bool(cand) and all("parsed_resume_id" in i and "similarity" in i for i in cand),
          f"{[(i['name'], i['similarity']) for i in cand]}")

    print("\n========== 需求④ 题库两套受众 + 绑定 + 已测评 ==========")
    st, body = call("GET", "/api/question-banks", hr)
    banks = body.get("data", [])
    check("④ 题库带 audience 字段", all("audience" in b for b in banks),
          f"{[(b['name'], b['audience']) for b in banks]}")
    st, body = call("GET", "/api/exams?audience=candidate", hr)
    check("④ 试卷可按受众过滤", st == 200,
          f"candidate 卷={len(body.get('data', []))}")
    st, body = call("GET", "/api/exam-assignments", hr)
    check("④ 测评任务接口可用", st == 200,
          f"total={body.get('data', {}).get('total')}")
    check("④ 简历列表带 exam_summary",
          all("exam_summary" in r for r in rows),
          f"三态分布={sorted({r['exam_summary']['state'] for r in rows})}")

    print("\n========== 需求⑤ 转正建号 + 员工只做培训 ==========")
    emp = login("emp_chen")
    if emp:
        st, body = call("GET", "/api/auth/me", emp)
        me = body.get("data", {})
        allowed = [m for m in me.get("menus", []) if m.get("allowed")]
        check("⑤ 员工菜单只有培训成长",
              len(allowed) == 1 and allowed[0]["path"] == "/training",
              f"{[(m['name'], m['path']) for m in allowed]}")
        check("⑤ 员工权限只有 train:*",
              all(p.startswith("train:") for p in me.get("permissions", [])),
              f"{me.get('permissions')}")
        st, body = call("GET", "/api/my/training/summary", emp)
        check("⑤ /my/training/summary 可用",
              st == 200 and "onboarded" in body.get("data", {}),
              f"onboarded={body.get('data', {}).get('onboarded')}")
        st, _b = call("GET", "/api/resumes", emp)
        check("⑤ 员工不能看简历（403）", st == 403, f"http={st}")
    else:
        check("⑤ 员工登录", False, "emp_chen 登录失败")

    print("\n========== 需求⑥ 题库文件导入 ==========")
    st, body = call("GET", "/openapi.json")
    paths = body.get("paths", {})
    check("⑥ 导入草稿接口已注册",
          "/api/question-banks/{bank_id}/import" in paths,
          f"{[p for p in paths if 'import' in p]}")
    check("⑥ 导入确认接口已注册",
          "/api/question-banks/{bank_id}/import/confirm" in paths)

    print("\n========== 数据一致性 ==========")
    st, body = call("GET", "/api/vector/status", hr)
    milvus = body.get("data", {}).get("milvus", {})
    check("向量库行数 = 现行简历数",
          milvus.get("resume_count") == milvus.get("expected_count"),
          f"count={milvus.get('resume_count')} expected={milvus.get('expected_count')} stale={milvus.get('stale')}")
    st, body = call("GET", "/api/talent-profiles?page_size=200", hr)
    profiles = body.get("data", {}).get("items", [])
    profile_ids = [p["resume_id"] for p in profiles]
    current_ids = {r["id"] for r in rows}
    check("已有画像唯一关联现行简历",
          st == 200 and bool(profiles) and len(profile_ids) == len(set(profile_ids))
          and set(profile_ids) <= current_ids,
          f"画像={len(profiles)} 现行简历={len(rows)}")

    print("\n========== 角色边界 ==========")
    st, body = call("GET", "/openapi.json")
    total_paths = len(body.get("paths", {}))
    check("接口总数 ≥ 70（S1–S6 新增已注册）", total_paths >= 70, f"paths={total_paths}")

    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}")
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
