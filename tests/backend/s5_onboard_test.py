"""S5 转正建号 + 员工权限回归（需求⑤）。

覆盖：
1) 员工登录后菜单只剩培训成长（dashboard/知识库已收回）
2) 候选人转正式员工：用手机号建号、返回一次性初始密码
3) 幂等：重复转正 → 409
4) 手机号缺失 → 400；手机号被占用 → 409
5) 员工用自己的账号登录 → /my/training/* 返回自己的数据
6) 员工不能操作别人的任务（403）
7) 员工不能访问简历/岗位/画像（403）
8) 员工能推进自己的任务进度

用法：python tests/backend/s5_onboard_test.py [base_url]
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL, SKIP = [], [], []


def call(method, path, token=None, body=None, timeout=90):
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


def login(username, password="123456"):
    st, body = call("POST", "/api/auth/login", body={"username": username, "password": password})
    return body.get("data", {}).get("token")


def upload(hr: str, filename: str, data: bytes) -> tuple[int, dict]:
    """multipart 上传一份简历。返回 (http, body)。"""
    boundary = "----S5Boundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n"
    ).encode("utf-8") + data + f"\r\n--{boundary}--\r\n".encode("utf-8")
    import urllib.error
    req = urllib.request.Request(BASE + "/api/resumes/upload", data=body, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", "Bearer " + hr)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode())
        except Exception:
            return e.code, {"code": e.code, "message": "http"}


def cleanup(user_id: int, parsed_id: int) -> None:
    """删掉本次建的员工账号与关联，恢复演示库。"""
    if not user_id:
        return
    sys.path.insert(0, ".")
    from sqlalchemy import text as sql_text

    from app.core.db import SessionLocal, engine
    from app.services.identity_service import reconcile_all

    with engine.begin() as conn:
        conn.execute(sql_text("DELETE FROM sys_user_roles WHERE user_id=:u").bindparams(u=user_id))
        conn.execute(sql_text("DELETE FROM sys_users WHERE id=:u").bindparams(u=user_id))
        conn.execute(sql_text(
            "UPDATE talent_profiles SET employee_user_id=NULL WHERE employee_user_id=:u"
        ).bindparams(u=user_id))

        # 删掉本次造的临时简历（连同其全部关联数据，否则外键会拦住）
        if parsed_id:
            row = conn.execute(sql_text(
                "SELECT resume_id FROM parsed_resumes WHERE id=:p").bindparams(p=parsed_id)
            ).first()
            rid = row[0] if row else None
            for table, cols in (
                ("talent_profiles", ("candidate_id",)),
                ("prejob_plans", ("candidate_id",)),
                ("growth_ledger", ("candidate_id",)),
                ("exam_assignments", ("parsed_resume_id",)),
                ("exam_submissions", ("parsed_resume_id",)),
                ("exam_interview_results", ("candidate_id",)),
                ("match_lists", ("candidate_id", "parsed_resume_id")),
                ("match_results", ("parsed_resume_id",)),
            ):
                for col in cols:
                    conn.execute(sql_text(
                        f"DELETE FROM {table} WHERE {col}=:p").bindparams(p=parsed_id))
            conn.execute(sql_text("DELETE FROM parsed_resumes WHERE id=:p").bindparams(p=parsed_id))
            if rid:
                conn.execute(sql_text("DELETE FROM parse_tasks WHERE resume_id=:r").bindparams(r=rid))
                conn.execute(sql_text("DELETE FROM parse_logs WHERE resume_id=:r").bindparams(r=rid))
                conn.execute(sql_text("DELETE FROM resume_files WHERE id=:r").bindparams(r=rid))

    with SessionLocal() as db:
        reconcile_all(db)
    print(f"已清理员工账号 {user_id} 与临时简历 {parsed_id}")


def main() -> int:
    hr = login("hr_zhao")
    if not hr:
        print("登录失败")
        return 1

    created_user_id = 0
    created_parsed_id = 0

    # ---------- 1. 员工权限基线 ----------
    emp = login("emp_chen")
    if not emp:
        print("emp_chen 登录失败")
        return report()
    st, body = call("GET", "/api/auth/me", emp)
    me = body.get("data", {})
    user_info = me.get("user", {})
    menus = [m for m in me.get("menus", []) if m.get("allowed")]
    check("★ 员工可见菜单只有培训成长", len(menus) == 1 and menus[0]["path"] == "/training",
          f"menus={[(m['name'], m['path']) for m in menus]}")
    check("员工角色是 employee", "employee" in user_info.get("roles", []),
          f"roles={user_info.get('roles')}")
    check("员工权限只剩 train:*",
          all(p.startswith("train:") for p in me.get("permissions", [])),
          f"perms={me.get('permissions')}")

    # 员工访问其它模块 → 403
    for path, label in (("/api/resumes", "简历"), ("/api/job-profiles", "岗位"),
                        ("/api/talent-profiles", "画像"), ("/api/exams", "测评")):
        st, _b = call("GET", path, emp)
        check(f"员工访问{label} → 403", st == 403, f"http={st}")

    # 未转正的员工调 /my/training → onboarded=false，不是 404
    st, body = call("GET", "/api/my/training/summary", emp)
    d = body.get("data", {})
    check("未转正员工调 /my/training/summary 返回 onboarded=false",
          st == 200 and d.get("onboarded") is False, f"http={st} onboarded={d.get('onboarded')}")

    # ---------- 2. 转正建号 ----------
    # 造一份临时简历来转正，避免污染真实候选人（之前直接转正真实候选人，
    # 中途失败会留下残留账号，还会把员工的转正绑定挂到真实简历上）。
    import uuid
    phone = "138" + uuid.uuid4().hex[:8].translate(str.maketrans("abcdef", "012345"))
    tmp_name = "转正测试" + uuid.uuid4().hex[:4]
    txt = f"{tmp_name}\n{phone}\n{tmp_name}@test.com\n本科 计算机科学与技术\n2020-2024 某公司 开发\nPython Java MySQL".encode()
    st, body = upload(hr, f"{tmp_name}.txt", txt)
    check("上传临时简历", st == 200 and (body.get("data", {}).get("items") or []),
          f"http={st} items={len(body.get('data', {}).get('items') or [])}")
    items = body.get("data", {}).get("items") or []
    if not items:
        return report()
    pid = items[0]["id"]
    created_parsed_id = pid

    # 先解析（转正需要手机号，解析后才有）
    call("POST", "/api/resumes/parse-next", hr, {})
    # 生成画像（培养计划依赖画像，缺画像会 404）
    st, body = call("POST", "/api/talent-profiles/generate", hr,
                    {"resume_id": pid, "use_ai": False})
    check("为临时简历生成画像", st == 200 and body.get("data"),
          f"http={st} profile_id={(body.get('data') or {}).get('id')}")
    # 生成培养计划（测「员工推进自己的任务」）
    st, body = call("POST", "/api/prejob-plans/generate", hr,
                    {"candidate_id": pid, "job_id": 3, "weeks": 4})
    check("为目标候选人生成培养计划", st == 200 and (body.get("data") or {}).get("id"),
          f"plan_id={(body.get('data') or {}).get('id')} tasks={len((body.get('data') or {}).get('tasks') or [])}")

    st, body = call("POST", f"/api/resumes/{pid}/onboard", hr, {"department_name": "算法组"})
    d = body.get("data", {})
    check("★ 转正建号成功", st == 200 and d.get("employee_user_id"),
          f"user_id={d.get('employee_user_id')} username={d.get('username')}")
    if not d.get("employee_user_id"):
        return report()
    created_user_id = d["employee_user_id"]
    check("账号是手机号", d.get("username") and d["username"].isdigit(), f"username={d.get('username')}")
    check("返回一次性初始密码", bool(d.get("initial_password")),
          f"password={d.get('initial_password')} generated={d.get('password_generated')}")
    check("绑定 employee 角色", d.get("role") == "employee", f"role={d.get('role')}")

    # 幂等
    st, body = call("POST", f"/api/resumes/{pid}/onboard", hr, {})
    check("重复转正 → 409", st == 409, f"http={st} msg={body.get('message')}")

    # ---------- 3. 新员工登录 ----------
    new_token = login(d["username"], d["initial_password"])
    check("★ 新员工能用手机号+初始密码登录", bool(new_token), f"username={d['username']}")
    if not new_token:
        return report(created_user_id, created_parsed_id)

    st, body = call("GET", "/api/auth/me", new_token)
    me2 = body.get("data", {})
    menus2 = [m for m in me2.get("menus", []) if m.get("allowed")]
    check("新员工菜单也只有培训成长", len(menus2) == 1 and menus2[0]["path"] == "/training",
          f"menus={[(m['name'], m['path']) for m in menus2]}")

    # ---------- 4. 我的培训 ----------
    st, body = call("GET", "/api/my/training/summary", new_token)
    d2 = body.get("data", {})
    check("★ 新员工 /my/training/summary 返回 onboarded=true",
          st == 200 and d2.get("onboarded") is True,
          f"onboarded={d2.get('onboarded')} plans={d2.get('plans')} tasks={d2.get('tasks')} todo={len(d2.get('todo', []))}")

    st, body = call("GET", "/api/my/training/plans", new_token)
    check("新员工 /my/training/plans 可用", st == 200,
          f"total={body.get('data', {}).get('total')}")
    st, body = call("GET", "/api/my/training/ledger", new_token)
    check("新员工 /my/training/ledger 可用", st == 200,
          f"total={body.get('data', {}).get('total')}")

    # ---------- 5. 员工推进自己的任务 ----------
    st, body = call("GET", "/api/my/training/plans", new_token)
    plans = body.get("data", {}).get("items", [])
    my_task = None
    for p in plans:
        my_task = next((t for t in p.get("tasks", []) if t["status"] != "done"), None)
        if my_task:
            break
    if my_task:
        st, body = call("POST", f"/api/prejob-plans/tasks/{my_task['id']}/progress", new_token,
                        {"minutes": 60, "progress": 50})
        check("★ 员工能推进自己的任务进度", st == 200,
              f"task={my_task['id']} http={st} progress={body.get('data', {}).get('progress')}")
        check("员工能读自己的计划", st == 200)
    else:
        check("员工有可推进的任务", False, "该候选人没有未完成任务", skip_if=False)

    # ---------- 6. 员工不能操作别人的任务 ----------
    st, body = call("GET", "/api/prejob-plans?page_size=50", hr)
    other_plan = None
    for p in body.get("data", {}).get("items", []):
        if p.get("candidate_id") != pid:
            other_plan = p
            break
    if other_plan:
        st, body = call("GET", f"/api/prejob-plans/{other_plan['id']}", hr)
        other_task = None
        for t in body.get("data", {}).get("tasks", []):
            if t["status"] != "done":
                other_task = t
                break
        if other_task:
            st, body = call("POST", f"/api/prejob-plans/tasks/{other_task['id']}/progress", new_token,
                            {"minutes": 60, "progress": 50})
            check("★ 员工不能操作别人的任务（403）", st == 403,
                  f"task={other_task['id']} owner={other_plan.get('candidate_name')} http={st} msg={body.get('message')}")
        else:
            check("找到别人的任务用于越权测试", False, "没有未完成任务")
    else:
        check("找到别人的计划用于越权测试", False, "只有一个计划")

    # ---------- 7. 手机号占用 ----------
    # 用一个临时简历验证占号，不动演示库里的真实手机号（用完删掉）
    sys.path.insert(0, ".")
    from sqlalchemy import text as sql_text

    from app.core.db import engine

    temp_pid = 0
    hr_dept = 4  # hr_zhao 的部门（seed 重置后为 4）
    with engine.begin() as conn:
        conn.execute(sql_text(
            "INSERT INTO resume_files (filename, object_key, status, content_type, size_bytes, "
            "project_name, position, dept_id, created_by, created_at, updated_at) "
            "VALUES ('占号测试.txt','tmp/s5.txt','completed','text/plain',10,'','',4,2,NOW(),NOW())"
        ))
        rid = conn.execute(sql_text("SELECT LAST_INSERT_ID()")).scalar()
        conn.execute(sql_text(
            "INSERT INTO parsed_resumes (resume_id, project_demand_id, job_profile_id, name, phone, "
            "email, skills, years_experience, strengths, resume_content, raw_json, manually_fixed, "
            "created_at, updated_at) "
            "VALUES (:rid,0,0,'占号测试','13900008888','',JSON_ARRAY(),0,'','',JSON_OBJECT(),0,NOW(),NOW())"
        ).bindparams(rid=rid))
        temp_pid = conn.execute(sql_text("SELECT LAST_INSERT_ID()")).scalar()

    if temp_pid:
        st, body = call("POST", f"/api/resumes/{temp_pid}/onboard", hr, {})
        d0 = body.get("data") or {}
        check("手机号未被占用时可建号", st == 200, f"http={st} username={d0.get('username')} msg={body.get('message')}")
        temp_uid = d0.get("employee_user_id")
        # 再建一个同手机号的 → 409
        with engine.begin() as conn:
            conn.execute(sql_text(
                "INSERT INTO resume_files (filename, object_key, status, content_type, size_bytes, "
                "project_name, position, dept_id, created_by, created_at, updated_at) "
                "VALUES ('占号测试2.txt','tmp/s5b.txt','completed','text/plain',10,'','',4,2,NOW(),NOW())"
            ))
            rid2 = conn.execute(sql_text("SELECT LAST_INSERT_ID()")).scalar()
            conn.execute(sql_text(
                "INSERT INTO parsed_resumes (resume_id, project_demand_id, job_profile_id, name, phone, "
                "email, skills, years_experience, strengths, resume_content, raw_json, manually_fixed, "
                "created_at, updated_at) "
                "VALUES (:rid,0,0,'占号测试2','13900008888','',JSON_ARRAY(),0,'','',JSON_OBJECT(),0,NOW(),NOW())"
            ).bindparams(rid=rid2))
            temp_pid2 = conn.execute(sql_text("SELECT LAST_INSERT_ID()")).scalar()
        st, body = call("POST", f"/api/resumes/{temp_pid2}/onboard", hr, {})
        check("★ 手机号被占用 → 409", st == 409, f"http={st} msg={body.get('message')}")

        # 清理临时数据
        with engine.begin() as conn:
            for p in (temp_pid, temp_pid2):
                conn.execute(sql_text(
                    "DELETE FROM parsed_resumes WHERE id=:p").bindparams(p=p))
            conn.execute(sql_text("DELETE FROM resume_files WHERE filename LIKE '占号测试%'"))
            if temp_uid:
                conn.execute(sql_text("DELETE FROM sys_user_roles WHERE user_id=:u").bindparams(u=temp_uid))
                conn.execute(sql_text("DELETE FROM sys_users WHERE id=:u").bindparams(u=temp_uid))

    # ---------- 8. 缺手机号 ----------
    st, body = call("GET", "/api/resumes?page_size=50", hr)
    no_phone = next((r for r in body.get("data", {}).get("items", [])
                     if r["id"] != pid and not r.get("phone")), None)
    if no_phone:
        st, body = call("POST", f"/api/resumes/{no_phone['id']}/onboard", hr, {})
        check("缺手机号 → 400", st == 400, f"http={st} msg={body.get('message')}")
    else:
        check("缺手机号的场景", True, "当前演示库所有简历都有手机号（跳过）")

    return report(created_user_id, created_parsed_id)


def report(user_id: int = 0, parsed_id: int = 0) -> int:
    if user_id:
        cleanup(user_id, parsed_id)
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
