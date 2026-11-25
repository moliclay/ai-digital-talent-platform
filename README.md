# AI 数字化人才平台

招聘简历入库、岗位匹配、人才画像、测评和员工培训。当前维护的是根目录下的 `frontend/`（由原 v2 迁入）和 `backend/`，旧前端不再维护。

产品范围、业务规则、验收标准和后续优先级见 [产品需求文档（PRD）](docs/产品需求文档.md)。

## 目录与分层

```text
frontend/                 React View：页面、组件、路由及 API 客户端
backend/
  app/main.py             FastAPI 应用装配与路由注册
  app/controllers/       Controller：HTTP 参数、权限入口、统一响应
  app/services/          业务规则、对象归属、查询与事务编排
  app/models/            Model：SQLAlchemy 表映射
  app/infrastructure/    本地存储、AI 网关、嵌入模型、向量库适配
  app/core/              配置、数据库连接、鉴权及通用响应
  scripts/               数据库初始化、迁移、样本生成等运维脚本
  storage/               运行时简历等文件，不提交源码仓库
scripts/windows/         根目录启停入口调用的内部脚本
tests/                   后端回归、浏览器探针、评测数据、演示样本
  seed_data.sql          首次初始化用的种子数据
docs/                    设计、演示、历史验收与前端交付资料
backup/                  现有数据库备份
logs/                    运行日志
```

请求路径：`frontend/src` → `/api` → `controllers` → `services` → `models` / `infrastructure`。改动 API 时同时检查权限、响应格式和前端调用。模型层不依赖业务服务或控制器；不为每张表强制增加空 DAO。

## 本地启动（Windows）

已有依赖和数据库时，从项目根目录运行 `一键启动.bat`，停止使用 `一键停止.bat`。前端端口 **5174**，后端端口 **8000**；健康检查为 `/api/health`，接口文档为 `/docs`。默认本地依赖包括 MySQL；Redis 为可选，AI、OCR 和向量能力取决于本地配置及服务可用性。

新环境使用 Python 3.12 和支持当前 Vite 的 Node.js。以下命令从根目录运行：

```powershell
python -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -r backend/requirements.txt
npm --prefix frontend ci
```

新环境可从 `backend/.env.example` 创建 `backend/.env` 并填入实际连接配置，**不要覆盖已有 `.env`**。只在有明确授权的开发数据库上运行初始化：

```powershell
backend/.venv/Scripts/python.exe backend/scripts/init_db.py
```

`init_db.py --reset` 会删除并重建目标库，不属于例行启动。后端配置从 `backend/.env` 加载，默认上传目录为 `backend/storage/`。启动包装脚本会执行 ChatAI 幂等增量迁移，已有业务数据保持原状。Milvus 使用现有 Docker 容器，语义检索还依赖 Ollama 嵌入服务。

## 验证与资料

```powershell
npm --prefix frontend run build
backend/.venv/Scripts/python.exe -B tests/backend/eval_parse.py
backend/.venv/Scripts/python.exe -B tests/backend/eval_match_30.py
```

上述两个评测不需要修改业务数据库。带登录、索引重建和提交的集成脚本只应指向隔离的测试环境，详见 [测试说明](tests/README.md)。[概要设计](docs/design/概要设计.md) 和 [历史交付](docs/MVP-1-历史说明.md) 保留当时的设想、旧版路径和验收记录；当前启动、目录与验证命令以本文件为准。

全平台验收结果及上线条件见 [全平台落地验收报告](全平台落地验收报告.md)。ChatAI 的设计与验收记录见 [ChatAI 开发方案](ChatAI-开发方案.md) 和 [ChatAI TODO](ChatAI-TODO.md)。
