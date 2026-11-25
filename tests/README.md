# 测试与样本

- `backend/`：Python 回归、离线评测和 HTTP 集成脚本。从仓库根目录调用，例如 `backend/.venv/Scripts/python.exe -B tests/backend/eval_match_30.py`。
- `frontend/`：当前前端的浏览器探测与截图辅助脚本。`shot.mjs` 可从根目录运行；需要启动前端，部分探测依赖演示数据。
- `data/`：带标注的评测集；`samples/`：演示简历；`seed_data.sql`：开发数据库种子。

离线检查优先运行 `eval_parse.py`（默认关闭 AI）与 `eval_match_30.py`。`eval_match.py` 通过 HTTP 重新计算岗位结果；部分 `*_test.py` 和浏览器脚本会上传简历、重建向量索引、提交测评或改培训进度。只在可回滚的测试数据库和独立向量集合执行这些脚本。
