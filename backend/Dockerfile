# syntax=docker/dockerfile:1
# 构建上下文必须是仓库根目录（需要同时拷入 backend/ 与 tests/seed_data.sql）：
#   docker build -f backend/Dockerfile -t ai-talent-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

ARG PIP_INDEX_URL=https://pypi.org/simple
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --index-url "${PIP_INDEX_URL}" -r /tmp/requirements.txt

COPY backend/ /app/
# init_db.py 读取 BACKEND_DIR.parent/tests/seed_data.sql，镜像内即 /tests/seed_data.sql
COPY tests/seed_data.sql /tests/seed_data.sql

RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/storage

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
