# Docker 镜像部署

平台已构建为两个镜像并发布到 GitHub Container Registry（仅 linux/amd64）：

| 镜像 | 内容 | 端口 |
| --- | --- | --- |
| `ghcr.io/moliclay/ai-talent-api:latest` | 后端 FastAPI + uvicorn（含建库/建表/种子脚本） | 8000 |
| `ghcr.io/moliclay/ai-talent-web:latest` | 前端静态站点 + nginx（把 `/api` 反代到 api） | 80 |

首次启动 api 容器会自动等待 MySQL、建库建表、灌入种子数据并创建演示账号（幂等，可用 `DB_AUTO_INIT=0` 关闭）。

演示账号：`admin` / `hr_zhao` / `pm_wang` / `emp_chen`，密码统一 `123456`。

---

## 方式一：compose 一键启动（推荐）

需要仓库根目录的 [docker-compose.yml](../docker-compose.yml)（含 MySQL 8.0、Redis 7、api、web）。

```bash
docker pull ghcr.io/moliclay/ai-talent-api:latest
docker pull ghcr.io/moliclay/ai-talent-web:latest

docker compose up -d
```

打开 <http://localhost:8080> 即可登录。默认端口可用 `WEB_PORT=9000 docker compose up -d` 修改。

停止与清理：

```bash
docker compose down          # 停止，保留数据卷
docker compose down -v       # 停止并删除数据库数据
```

## 方式二：纯 docker run（不用 compose）

```bash
docker network create ai-talent

docker run -d --name ai-talent-mysql --network ai-talent \
  -e MYSQL_ROOT_PASSWORD=123456 -e MYSQL_DATABASE=ai_talent \
  -v ai-talent-mysql:/var/lib/mysql \
  mysql:8.0 --character-set-server=utf8mb4 --collation-server=utf8mb4_unicode_ci

docker run -d --name ai-talent-redis --network ai-talent redis:7-alpine

docker run -d --name ai-talent-api --network ai-talent --network-alias api \
  -e DATABASE_URL='mysql+pymysql://root:123456@ai-talent-mysql:3306/ai_talent?charset=utf8mb4' \
  -e REDIS_URL=redis://ai-talent-redis:6379/0 \
  -e JWT_SECRET=change-me-in-prod \
  -e STORAGE_DIR=/app/storage \
  -e AI_ENABLED=0 \
  -v ai-talent-storage:/app/storage \
  ghcr.io/moliclay/ai-talent-api:latest

docker run -d --name ai-talent-web --network ai-talent -p 8080:80 \
  ghcr.io/moliclay/ai-talent-web:latest
```

> `--network-alias api` 不能省：nginx 按服务名 `api` 转发 `/api/*`。

## 环境变量

| 变量 | 默认（compose） | 说明 |
| --- | --- | --- |
| `MYSQL_ROOT_PASSWORD` | `123456` | MySQL root 密码，api 的 DATABASE_URL 会跟随 |
| `JWT_SECRET` | `mvp1-dev-secret-change-me-in-prod` | 登录令牌密钥，正式部署必须改 |
| `WEB_PORT` | `8080` | 前端对外端口 |
| `DB_AUTO_INIT` | `1` | 启动时自动初始化数据库（幂等） |
| `DB_WAIT_SECONDS` | `180` | 等待数据库可连接的最长秒数 |
| `AI_ENABLED` | `0` | 置 1 才调用大模型；关闭时解析/画像/评分走规则回退 |
| `AI_BASE_URL` | `http://host.docker.internal:3065/v1` | OpenAI 兼容网关地址 |
| `AI_API_KEY` | 空 | 网关密钥 |
| `EMBED_BASE_URL` | `http://host.docker.internal:11434` | 本地嵌入服务（bge-m3，1024 维） |
| `MILVUS_URI` | `http://host.docker.internal:19530` | 向量库地址 |

容器内访问宿主机服务统一用 `host.docker.internal`（compose 已配置 `host-gateway`）。

## 数据持久化

- `mysql-data` 卷：业务库 `ai_talent`
- `api-storage` 卷：简历原件等上传文件（`STORAGE_DIR=/app/storage`）

## 已知限制

- 只构建 `linux/amd64`，Apple Silicon / ARM 主机需要 Docker 的 amd64 模拟（`--platform linux/amd64`）。
- 语义检索需要自备 Milvus 与嵌入服务，镜像不内置；未配置时相关接口返回不可用提示，其他模块不受影响。
- 设计截图目录（`docs/frontend/shots`，约 136MB）未纳入版本库，仓库内少数交付说明的图片在 GitHub 上是坏图，属预期。

## 本地自行构建

```bash
docker build -f backend/Dockerfile -t ghcr.io/moliclay/ai-talent-api:latest .
docker build -f frontend/Dockerfile -t ghcr.io/moliclay/ai-talent-web:latest frontend
```

api 镜像的构建上下文必须是仓库根目录（需要 `tests/seed_data.sql`）；可加 `--build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple` 或 web 的 `--build-arg NPM_REGISTRY=https://registry.npmmirror.com` 走国内源。
