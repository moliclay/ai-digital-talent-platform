"""匹配准确率回归：用 tests/data/match_eval.json 的标注集跑真实 HTTP。

用法：
    python tests/backend/eval_match.py             # 只跑评测（假定简历已入库）
    python tests/backend/eval_match.py --prepare    # 先上传样例简历并解析，再评测
退出码 0 = 三项指标全部达标。
"""
from __future__ import annotations

import argparse
import json
import mimetypes
import pathlib
import sys
import urllib.error
import urllib.request
import uuid

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "backend"
EVAL_PATH = BACKEND_DIR.parent / "tests" / "data" / "match_eval.json"
SAMPLES = BACKEND_DIR.parent / "tests" / "samples"
BASE = "http://127.0.0.1:8000"


def call(method: str, path: str, token: str | None = None, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def upload_files(token: str, files: list[pathlib.Path]) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    parts: list[bytes] = []
    for f in files:
        ctype = mimetypes.guess_type(f.name)[0] or "application/octet-stream"
        parts.append(
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{f.name}\"\r\n"
            f"Content-Type: {ctype}\r\n\r\n".encode() + f.read_bytes() + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    payload = b"".join(parts)
    req = urllib.request.Request(BASE + "/api/resumes/upload", data=payload, method="POST")
    req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
    req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode() or "{}")


def prepare(token: str) -> None:
    files = [p for p in sorted(SAMPLES.iterdir()) if p.suffix.lower() in (".pdf", ".docx", ".txt")]
    files.append(SAMPLES / "扫描件_张伟.png") if (SAMPLES / "扫描件_张伟.png").exists() else None
    status, body = upload_files(token, files)
    print(f"上传：http={status} accepted={(body.get('data') or {}).get('accepted')}")
    for _ in range(20):
        status, body = call("POST", "/api/resumes/parse-next", token)
        data = body.get("data") or {}
        if data.get("status") == "idle":
            break
        print(f"  解析 task={data.get('task_id')} status={data.get('status')} fields={data.get('fields')}")
    status, body = call("GET", "/api/resumes/queue", token)
    print(f"队列：{(body.get('data') or {}).get('counts')}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true", help="先上传并解析样例简历")
    args = parser.parse_args()

    status, body = call("POST", "/api/auth/login", body={"username": "hr_zhao", "password": "123456"})
    if status != 200:
        print("登录失败，后端是否已启动？", body)
        return 1
    token = body["data"]["token"]

    if args.prepare:
        prepare(token)

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    job_ids = sorted({c["job_profile_id"] for c in cases})

    for job_id in job_ids:
        status, body = call("POST", "/api/matching/run", token, {"job_profile_id": job_id})
        data = body.get("data") or {}
        print(f"匹配 job={job_id} http={status} scanned={data.get('scanned')} "
              f"passed={data.get('passed')} failed={data.get('failed')}")

    rows: dict[tuple[int, str], dict] = {}
    for job_id in job_ids:
        status, body = call("GET", f"/api/matching/lists?job_profile_id={job_id}&page_size=200", token)
        for item in (body.get("data") or {}).get("items", []):
            rows[(job_id, item["name"])] = item

    judge_ok = score_ok = reason_ok = 0
    print("\n=== 标注集回归 ===")
    for case in cases:
        key = (case["job_profile_id"], case["resume_name"])
        expected = case["expected"]
        row = rows.get(key)
        if row is None:
            print(f"FAIL {case['id']} 未产生匹配记录（{case['resume_name']} vs {case['job_profile_name']}）")
            continue

        passed_ok = bool(row["passed"]) == bool(expected["passed"])
        lo = expected.get("score_min", 0)
        hi = expected.get("score_max", 100)
        in_range = lo <= row["total_score"] <= hi
        missing_words = [w for w in expected.get("reason_contains", []) if w not in (row.get("reason") or "")]
        reason_hit = not missing_words

        judge_ok += passed_ok
        score_ok += in_range
        reason_ok += reason_hit
        flag = "PASS" if (passed_ok and in_range and reason_hit) else "FAIL"
        print(
            f"{flag} {case['id']} {case['resume_name']}→{case['job_profile_name']} "
            f"score={row['total_score']} 期望[{lo},{hi}] passed={row['passed']} 期望{expected['passed']}"
            + (f" 缺少关键词={missing_words}" if missing_words else "")
        )
        if flag == "FAIL":
            print(f"      reason={row.get('reason')}")

    total = len(cases)
    print(f"\n通过判定一致 {judge_ok}/{total}　分数落区间 {score_ok}/{total}　原因关键词命中 {reason_ok}/{total}")
    ok = judge_ok == total and score_ok == total and reason_ok == total
    print("结论：" + ("达标（示范规模 5 条，正式验收需扩到 ≥30 条）" if ok else "未达标"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
