"""匹配判定回归（P0-3）：36 条"要求级断言"，不复用匹配引擎的评分逻辑。

期望值只由岗位**硬条件**推导：
- must_fail：违反任一硬条件（学历/技能/年限）→ 判定必须为不通过且分数低于合格线；
- must_pass：硬条件全满足且技能全覆盖、年限达标 → 判定必须通过且分数不低于合格线。

用法：python tests/backend/eval_match_30.py [--show]
退出码 0 = 一致率达到目标（0.90）。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

ROOT = BACKEND_DIR.parent
EVAL_PATH = ROOT / "tests" / "data" / "match_eval_30.json"
TARGET = 0.90


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args()

    from app.services.matcher_service import evaluate

    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    jobs = {j["id"]: j for j in data["jobs"]}
    cases = data["cases"]

    passed_cnt = {"must_pass": 0, "must_fail": 0}
    ok_cnt = {"must_pass": 0, "must_fail": 0}
    score_ok = 0
    fails = []

    for case in cases:
        job = jobs[case["job_id"]]
        job_dict = {
            "name": job["name"],
            "conditions": job["conditions"],
            "score_rules": {"weights": job["weights"]},
            "passing_threshold": job["threshold"],
            "ability_requirements": {},
        }
        r = case["resume"]
        parsed = {
            "name": r["name"], "education": r["education"],
            "years_experience": r["years_experience"], "skills": r["skills"],
            "resume_content": "、".join(r["skills"]),
            "phone": "13800000000", "email": "x@example.com", "major": "计算机科学与技术",
        }
        v = evaluate(job_dict, parsed)
        kind = case["expected"]["outcome"]
        threshold = case["expected"]["threshold"]

        passed_cnt[kind] += 1
        good = (v.passed is True) if kind == "must_pass" else (v.passed is False)
        band_ok = (v.total_score >= threshold) if kind == "must_pass" else (v.total_score < threshold)
        if good and band_ok:
            ok_cnt[kind] += 1
        if good:
            score_ok += 1
        else:
            fails.append((case["id"], kind, v.passed, v.total_score, threshold, case["why"]))

    total = sum(passed_cnt.values())
    consistent = sum(ok_cnt.values())
    print(f"样本 {total} 条（must_pass {passed_cnt['must_pass']} / must_fail {passed_cnt['must_fail']}）\n")
    for kind in ("must_pass", "must_fail"):
        n, d = ok_cnt[kind], passed_cnt[kind]
        print(f"  {kind:10s} 一致 {n}/{d}  {n / d * 100:5.1f}%")
    print(f"\n  判定 + 分数带一致   {consistent}/{total}  {consistent / total * 100:5.1f}%")
    print(f"  仅判定一致         {score_ok}/{total}  {score_ok / total * 100:5.1f}%")

    if fails:
        print("\n不一致样本：")
        for row in fails[:20]:
            print("  ", row)

    verdict = "达标" if consistent / total >= TARGET else "未达标"
    print(f"\n目标 {TARGET:.0%} → {verdict}")
    return 0 if consistent / total >= TARGET else 1


if __name__ == "__main__":
    raise SystemExit(main())
