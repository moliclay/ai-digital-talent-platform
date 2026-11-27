#!/bin/sh
# 容器启动：等数据库可连接 → 幂等初始化（建库/建表/种子/演示账号）→ 启动 uvicorn
set -e

DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-180}"
echo "[entrypoint] 等待数据库可连接（最多 ${DB_WAIT_SECONDS}s）…"

python - "$DB_WAIT_SECONDS" <<'PY'
import sys
import time

from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url

from app.core.config import settings

deadline = time.time() + int(sys.argv[1])
# 只探测服务端连通性：库可能还没建，所以去掉 database 部分
server_url = make_url(settings.db_url).set(database=None)
while True:
    try:
        engine = create_engine(server_url, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        print("[entrypoint] 数据库已连通")
        break
    except Exception as exc:  # noqa: BLE001
        if time.time() > deadline:
            print(f"[entrypoint] 数据库连接失败：{exc}")
            sys.exit(1)
        time.sleep(3)
PY

if [ "${DB_AUTO_INIT:-1}" = "1" ]; then
  echo "[entrypoint] 初始化数据库（幂等，已有数据只做引导）…"
  python /app/scripts/init_db.py
fi

exec "$@"
