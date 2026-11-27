# syntax=docker/dockerfile:1
# 构建上下文必须是仓库根目录（需要同时拷入 backend/ 与 tests/seed_data.sql）：
#   docker build -f backend/Dockerfile -t ai-talent-api .
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    TZ=Asia/Shanghai

WORKDIR /app

# ---------------------------------------------------------------------------
# Python 依赖：按体积拆成多个 RUN，每个 RUN 一层。
# 依赖清单仍以 backend/requirements.txt 为准，这里只是把安装过程分层：
#   1) 单层过大会让推送在收尾阶段超时（镜像经代理上传时，单层 500MB+ 会 timeout）；
#   2) 分层后每层只有几十 MB，推送稳定，拉取也能按层复用缓存。
# PyMuPDF 用 --no-deps 安装：代码只用到 fitz 的基础解析能力，
# 不需要 PyMuPDF 2.x 附带的 onnxruntime / pymupdf4llm / pymupdf-layout（约 100MB+）。
# ---------------------------------------------------------------------------
ARG PIP_INDEX_URL=https://pypi.org/simple

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      fastapi==0.162.0 starlette==1.10.0 "uvicorn[standard]==0.54.0"

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      pydantic==2.14.2 python-multipart==0.0.33 PyMySQL==1.2.3 PyJWT==2.15.1 redis==8.1.0

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      SQLAlchemy==2.1.6

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      pypdf==6.21.4 python-docx==1.2.0 openpyxl==3.1.5

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      reportlab==5.1.0

# numpy / pandas 是 pymilvus 的依赖，单独成层以免与 PyMuPDF 叠在一起
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      numpy

# pandas 3.x 自带 43MB 的测试数据，运行不需要，装完立刻删掉，避免整层过大
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      pandas \
 && rm -rf /usr/local/lib/python3.12/site-packages/pandas/tests

# fitz 本体（不带附加模型依赖）；layout/ 是 PyMuPDF 2.x 的版面分析模型（onnx/presidio，51MB），
# 代码只用 fitz 的文本抽取与页面渲染，装完立刻删除，避免出现 120MB 的单层
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      --no-deps PyMuPDF==2.1 \
 && rm -rf /usr/local/lib/python3.12/site-packages/pymupdf/layout \
           /usr/local/lib/python3.12/site-packages/pymupdf/__pycache__ \
           /usr/local/lib/python3.12/site-packages/pymupdf/mupdf-devel

# fitz 运行期需要的基础依赖
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      networkx pyyaml psutil tabulate

RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url "${PIP_INDEX_URL}" \
      pymilvus==3.0.2

COPY backend/ /app/
# init_db.py 读取 BACKEND_DIR.parent/tests/seed_data.sql，镜像内即 /tests/seed_data.sql
COPY tests/seed_data.sql /tests/seed_data.sql

RUN chmod +x /app/docker-entrypoint.sh && mkdir -p /app/storage

EXPOSE 8000
ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
