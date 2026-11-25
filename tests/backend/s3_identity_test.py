"""S3 身份去重回归：同一人的两份简历只留最新为现行，同名不同手机号不合并。

用例设计（不污染演示库，用完即清）：
1) 上传一份"张伟"的复制件（同手机号、内容略改）→ 解析后旧行 is_current=0
2) 列表默认只剩 1 个张伟；include_superseded=1 能看到 2 个
3) 造一份同名但手机号不同的"张伟" → 两人并存，不合并
4) 详情返回 identity.siblings
5) 疑似重复接口能报出同名同校同专业的组
6) 归一化函数单测（+86/横线/括号/大小写）

用法：python tests/backend/s3_identity_test.py [base_url]
"""
from __future__ import annotations

import io
import json
import sys
import urllib.error
import urllib.request

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
PASS, FAIL, SKIP = [], [], []

ZHANG_WEI_PHONE = "13900000011"      # 库里张伟的手机号
ZHANG_WEI_EMAIL = "zhangwei@demo.com"


def call(method, path, token=None, body=None, timeout=180, raw=None, content_type=None):
    if raw is not None:
        req = urllib.request.Request(BASE + path, data=raw, method=method)
        req.add_header("Content-Type", content_type or "application/octet-stream")
    else:
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


def upload_txt(token, filename: str, text: str) -> list[int]:
    """multipart 上传一份 txt 简历，返回新建的 resume_file id。

    上传接口返回 {accepted: 数量, rejected: 数量, items: [{id, filename, size_bytes}]}。
    """
    boundary = "----S3Boundary7MA4YWxkTrZu0gW"
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="files"; filename="{filename}"\r\n'
        f"Content-Type: text/plain\r\n\r\n{text}\r\n"
        f"--{boundary}--\r\n"
    ).encode("utf-8")
    st, resp = call("POST", "/api/resumes/upload", token, raw=body,
                    content_type=f"multipart/form-data; boundary={boundary}")
    data = resp.get("data", {})
    items = data.get("items") or []
    return [int(a["id"]) for a in items if a.get("id")]


def parse_all(token) -> list[dict]:
    """把队列里的任务逐个消费完。"""
    out = []
    for _ in range(10):
        st, body = call("POST", "/api/resumes/parse-next", token, {})
        d = body.get("data") or {}
        if not d or d.get("status") in (None, "idle"):
            break
        out.append(d)
        if d.get("status") != "completed":
            break
    return out


def build_resume(name: str, phone: str, email: str, edu: str, major: str, years: int, extra: str) -> str:
    return (
        f"姓名：{name}\n手机：{phone}\n邮箱：{email}\n学历：{edu}\n"
        f"专业：{major}\n工作年限：{years} 年\n"
        f"技能：Python、PyTorch、向量数据库\n{extra}\n"
    )


def main() -> int:
    token = login()
    if not token:
        print("登录失败")
        return 1

    created_ids: list[int] = []

    # ---------- 0. 归一化单测 ----------
    sys.path.insert(0, ".")
    try:
        from app.services.identity_service import normalize_email, normalize_phone
        cases = [("139-0000-0011", "13900000011"), ("+86 139 0000 0011", "13900000011"),
                 ("(139)0000-0011", "13900000011"), ("0086 13900000011", "13900000011"),
                 ("", ""), ("1234", "")]
        ok = all(normalize_phone(a) == b for a, b in cases)
        check("手机号归一化（+86/横线/括号）", ok,
              f"{[(a, normalize_phone(a)) for a, b in cases if normalize_phone(a) != b]}" or "全部正确")
        check("邮箱归一化（大小写/空白）",
              normalize_email("  ZhangWei@Demo.COM ") == "zhangwei@demo.com",
              normalize_email("  ZhangWei@Demo.COM "))
        check("无效邮箱返回空", normalize_email("abc") == "", repr(normalize_email("abc")))
    except Exception as exc:
        check("导入 identity_service", False, str(exc)[:80])

    # ---------- 1. 列表基线 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    before = body.get("data", {}).get("items", [])
    before_zw = [i for i in before if i["name"] == "张伟"]
    if not before_zw:
        baseline = build_resume("张伟", ZHANG_WEI_PHONE, ZHANG_WEI_EMAIL, "本科",
                                "计算机科学与技术", 4, "2024 年：模型训练项目")
        uploaded = upload_txt(token, "张伟_基线.txt", baseline)
        done = [p for p in parse_all(token) if p.get("status") == "completed"] if uploaded else []
        if done:
            created_ids.append(int(done[-1]["resume_id"]))
            _, body = call("GET", "/api/resumes?page_size=50", token)
            before_zw = [i for i in body.get("data", {}).get("items", []) if i["name"] == "张伟"]
    check("基线：列表里张伟 1 份", len(before_zw) == 1, f"count={len(before_zw)}")
    if len(before_zw) != 1:
        return report(created_ids, token)
    old_zw_id = before_zw[0]["id"] if before_zw else None

    # ---------- 2. 上传同手机号的新版张伟 ----------
    text = build_resume("张伟", ZHANG_WEI_PHONE, ZHANG_WEI_EMAIL, "硕士",
                        "计算机科学与技术", 6, "2026 年新增：主导大模型推理优化项目")
    ids = upload_txt(token, "张伟_新版_20261104.txt", text)
    check("上传新版张伟成功", bool(ids), f"ids={ids}")
    if not ids:
        return report(created_ids, token)

    parsed = parse_all(token)
    done = [p for p in parsed if p.get("status") == "completed"]
    check("新版张伟解析完成", bool(done), f"tasks={[(p.get('status'), p.get('resume_id')) for p in parsed]}")
    if not done:
        return report(created_ids, token)

    new_id = done[-1]["resume_id"]
    created_ids.append(int(new_id))
    identity = done[-1].get("identity", {})
    check("解析结果带 identity 信息", isinstance(identity, dict) and "identity_key" in identity,
          f"identity={identity}")

    # ---------- 3. 旧版被置为非现行 ----------
    st, body = call("GET", f"/api/resumes/{old_zw_id}", token)
    old = body.get("data", {})
    check("★ 旧张伟 is_current=False", old.get("is_current") is False,
          f"is_current={old.get('is_current')} superseded_by={old.get('superseded_by')}")
    check("★ 旧张伟 superseded_by 指向新版", old.get("superseded_by") == new_id,
          f"superseded_by={old.get('superseded_by')} new_id={new_id}")

    st, body = call("GET", f"/api/resumes/{new_id}", token)
    new = body.get("data", {})
    check("新版张伟 is_current=True", new.get("is_current") is True, f"is_current={new.get('is_current')}")

    # ---------- 4. 列表默认只显示现行 ----------
    st, body = call("GET", "/api/resumes?page_size=50", token)
    after = body.get("data", {}).get("items", [])
    after_zw = [i for i in after if i["name"] == "张伟"]
    check("★ 列表默认张伟仍只有 1 份", len(after_zw) == 1,
          f"count={len(after_zw)} ids={[i['id'] for i in after_zw]}")
    check("列表里那份是新的", after_zw and after_zw[0]["id"] == new_id,
          f"id={after_zw[0]['id'] if after_zw else None}")

    # ---------- 5. include_superseded=1 能看到 2 份 ----------
    st, body = call("GET", "/api/resumes?page_size=50&include_superseded=1", token)
    allrows = body.get("data", {}).get("items", [])
    all_zw = [i for i in allrows if i["name"] == "张伟"]
    check("★ include_superseded=1 能看到 2 份张伟", len(all_zw) == 2,
          f"count={len(all_zw)} ids={[i['id'] for i in all_zw]}")

    # ---------- 6. 详情返回 siblings ----------
    st, body = call("GET", f"/api/resumes/{new_id}", token)
    ident = body.get("data", {}).get("identity", {})
    sib = ident.get("siblings", [])
    check("详情含 identity.siblings", isinstance(sib, list) and len(sib) == 2,
          f"siblings={[(s['parsed_resume_id'], s['is_current']) for s in sib]}")

    # ---------- 7. 同名不同手机号 → 不合并 ----------
    other_phone = "13900009999"
    text2 = build_resume("张伟", other_phone, "zw2@demo.com", "本科", "软件工程", 3,
                         "另一位同名候选人")
    ids2 = upload_txt(token, "张伟_同名不同人_20261104.txt", text2)
    check("上传同名不同手机号的张伟", bool(ids2), f"ids={ids2}")
    if ids2:
        parsed2 = parse_all(token)
        done2 = [p for p in parsed2 if p.get("status") == "completed"]
        check("同名不同人解析完成", bool(done2), f"{[p.get('status') for p in parsed2]}")
        if done2:
            other_id = done2[-1]["resume_id"]
            created_ids.append(int(other_id))
            st, body = call("GET", f"/api/resumes/{other_id}", token)
            d2 = body.get("data", {})
            check("★ 同名不同手机号：is_current=True（没被合并）",
                  d2.get("is_current") is True,
                  f"is_current={d2.get('is_current')} key={d2.get('identity_key')}")
            st, body = call("GET", "/api/resumes?page_size=50", token)
            rows = body.get("data", {}).get("items", [])
            zw = [i for i in rows if i["name"] == "张伟"]
            check("★ 列表出现 2 个不同的张伟", len(zw) == 2,
                  f"count={len(zw)} keys={[i['identity_key'] for i in zw]}")

    # ---------- 8. 疑似重复接口 ----------
    st, body = call("GET", "/api/resumes/identity/suspected", token)
    groups = body.get("data", {}).get("groups", [])
    check("疑似重复接口可用", st == 200, f"groups={len(groups)}")
    if groups:
        check("疑似组带 ids 与 reason", "ids" in groups[0] and "reason" in groups[0],
              f"{groups[0]}")

    # ---------- 9. 全量重算幂等 ----------
    st, body = call("POST", "/api/resumes/identity/reconcile", token, {})
    r1 = body.get("data", {})
    check("全量重算可用", st == 200, f"total={r1.get('total')} superseded={r1.get('superseded')}")

    return report(created_ids, token)


def cleanup(ids: list[int], token: str) -> None:
    """删掉本次造的简历（连带文件、解析任务与日志），并重算身份关系。"""
    sys.path.insert(0, ".")
    from sqlalchemy import text as sql_text

    from app.core.db import SessionLocal, engine
    from app.services.identity_service import reconcile_all

    if not ids:
        return
    import re
    if not re.fullmatch(r"ai_talent_accept_[0-9a-f]{10}", engine.url.database or ""):
        raise RuntimeError("Cleanup requires an isolated acceptance database")
    uniq = sorted({int(i) for i in ids})
    with engine.begin() as conn:
        rows = conn.execute(sql_text(
            "SELECT id, resume_id FROM parsed_resumes WHERE id IN ("
            + ",".join(map(str, uniq)) + ")")
        ).fetchall()
        for pid, rid in rows:
            conn.execute(sql_text("DELETE FROM parse_tasks WHERE resume_id=:r").bindparams(r=rid))
            conn.execute(sql_text("DELETE FROM parse_logs WHERE resume_id=:r").bindparams(r=rid))
            # 删除前先把画像「退回」同身份的其它简历，避免把人唯一的画像一起删掉。
            # 场景：s3 上传新版张伟 → 画像被 migrate_links 迁到新版 → cleanup 删新版 → 画像消失。
            survivor = conn.execute(sql_text(
                "SELECT id FROM parsed_resumes "
                "WHERE identity_key=(SELECT identity_key FROM parsed_resumes WHERE id=:p) "
                "  AND id<>:p AND identity_key<>'' ORDER BY id DESC LIMIT 1"
            ).bindparams(p=pid)).scalar()
            if survivor:
                conn.execute(sql_text(
                    "UPDATE talent_profiles SET candidate_id=:s WHERE candidate_id=:p"
                ).bindparams(s=survivor, p=pid))
            # 先删所有引用该简历的子表数据，否则外键约束会拦住。
            # match_lists 同时有 candidate_id 和 parsed_resume_id 两列，两列都要删。
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
                        f"DELETE FROM {table} WHERE {col}=:p").bindparams(p=pid))
            conn.execute(sql_text("DELETE FROM parsed_resumes WHERE id=:p").bindparams(p=pid))
            conn.execute(sql_text("DELETE FROM resume_files WHERE id=:r").bindparams(r=rid))
    # 删掉被替代行后，剩下的 superseded_by 可能指向已删记录 → 重算修正。
    # 注意：删除「新版本」后，原本被它替代的旧版本会重新变成现行，
    # 但画像可能已随迁移挂到被删的新版本上 → 重算后需要检查并补回。
    with SessionLocal() as db:
        result = reconcile_all(db)
    print(f"已清理 {len(uniq)} 条测试简历，并重算身份关系")

    # 补回因删除新版本而丢失的画像：现行简历缺画像时，用同身份其它版本的画像顶上
    with engine.begin() as conn:
        orphans = conn.execute(sql_text(
            "SELECT pr.id, pr.name FROM parsed_resumes pr "
            "WHERE pr.is_current=1 AND NOT EXISTS ("
            "  SELECT 1 FROM talent_profiles tp WHERE tp.candidate_id=pr.id)"
        )).fetchall()
        for pid, name in orphans:
            moved = conn.execute(sql_text(
                "UPDATE talent_profiles SET candidate_id=:p "
                "WHERE candidate_id IN ("
                "  SELECT id FROM (SELECT id FROM parsed_resumes "
                "    WHERE identity_key=(SELECT identity_key FROM parsed_resumes WHERE id=:p) "
                "      AND id<>:p) t)"
            ).bindparams(p=pid)).rowcount
            if moved:
                print(f"  补回画像：{name}（{moved} 条迁到 id={pid}）")


def report(cleanup_ids: list[int] | None = None, token: str | None = None) -> int:
    if cleanup_ids and token:
        cleanup(cleanup_ids, token)
    print(f"\n通过 {len(PASS)} / {len(PASS) + len(FAIL)}"
          + (f"  （跳过 {len(SKIP)}）" if SKIP else ""))
    return 0 if not FAIL else 1


if __name__ == "__main__":
    sys.exit(main())
