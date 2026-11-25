"""简历解析准确率回归（P0-3）：对 32 份合成简历逐字段比对真值。

用法：
    python tests/backend/eval_parse.py            # 规则模式（关掉 AI 兜底，测解析器本身）
    python tests/backend/eval_parse.py --ai       # 开 AI 兜底（测"解析器 + 模型"整体）
    python tests/backend/eval_parse.py --show     # 打印每个失败样本的原文与抽取结果

退出码 0 = 字段级准确率达到 MVP 目标（0.90）；PRD 目标 0.99 单独汇报。
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[2] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

ROOT = BACKEND_DIR.parent
EVAL_PATH = ROOT / "tests" / "data" / "resume_parse_eval_30.json"
RES_DIR = ROOT / "tests" / "data"

FIELDS = ["name", "phone", "email", "education", "major", "years_experience"]
MVP_TARGET = 0.90
PRD_TARGET = 0.99


def norm(field: str, value) -> str:
    if value is None:
        return ""
    if field == "phone":
        return re.sub(r"\D", "", str(value))
    if field == "email":
        return str(value).strip().lower()
    if field == "years_experience":
        return str(int(value)) if str(value).isdigit() else str(value).strip()
    return str(value).strip()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ai", action="store_true", help="开启 AI 兜底")
    ap.add_argument("--show", action="store_true", help="打印失败明细")
    args = ap.parse_args()

    if not args.ai:
        # 只测规则：在导入协议层之前关掉 AI（settings 是 frozen dataclass，只能靠环境变量）
        import os
        os.environ["AI_ENABLED"] = "0"

    from app.services.parser_service import parse_resume

    cases = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    per_field = {f: [0, 0] for f in FIELDS}   # [对, 总]
    per_format: dict[str, list[int]] = {}
    all_correct = 0
    failures = []

    for case in cases:
        path = RES_DIR / case["file"]
        data = path.read_bytes()
        out = parse_resume(path.name, data)
        gt = case["ground_truth"]
        fields = out.fields or {}

        fmt = case["format"]
        per_format.setdefault(fmt, [0, 0])
        ok_all = True
        for f in FIELDS:
            got, want = norm(f, fields.get(f)), norm(f, gt.get(f))
            hit = got == want
            per_field[f][0] += 1 if hit else 0
            per_field[f][1] += 1
            if not hit:
                ok_all = False
                failures.append((case["id"], fmt, f, want, got))
        per_format[fmt][0] += 1 if ok_all else 0
        per_format[fmt][1] += 1
        all_correct += 1 if ok_all else 0

    total = len(cases)
    print(f"样本 {total} 份（模式：{'规则+AI' if args.ai else '仅规则'}）\n")
    print("字段级准确率：")
    for f in FIELDS:
        hit, tot = per_field[f]
        print(f"  {f:18s} {hit:2d}/{tot:2d}  {hit / tot * 100:5.1f}%")
    micro = sum(v[0] for v in per_field.values()) / sum(v[1] for v in per_field.values())
    print(f"\n  字段级合计（micro）    {micro * 100:5.1f}%")
    print(f"  整份全对（exact）      {all_correct}/{total}  {all_correct / total * 100:5.1f}%")

    print("\n按格式：")
    for fmt, (hit, tot) in sorted(per_format.items()):
        print(f"  {fmt:5s} 全对 {hit}/{tot}  {hit / tot * 100:5.1f}%")

    if failures and args.show:
        print("\n失败明细（字段 / 期望 / 实际）：")
        for row in failures[:40]:
            print("  ", row)

    print()
    verdict = "达标" if micro >= MVP_TARGET else "未达标"
    print(f"MVP 目标 {MVP_TARGET:.0%} → {verdict}；PRD 目标 {PRD_TARGET:.0%} → "
          f"{'达标' if micro >= PRD_TARGET else '未达标'}")
    return 0 if micro >= MVP_TARGET else 1


if __name__ == "__main__":
    raise SystemExit(main())
