# AI 数字化人才平台 · MVP-1

> 历史资料：原始路径、设计范围和验收记录仅用于追溯。当前目录和启动方式以 [项目 README](../README.md) 为准。

招聘选拔闭环的可运行实现：**简历上传 → 规则解析 → 岗位条件 → 匹配打分 → 名单复核**。
对应方案：`../MVP-1-开发方案.md`。

- 后端：FastAPI + SQLAlchemy 2 + MySQL + Redis（会话/黑名单）
- 前端：Vite + React 18 + TypeScript（深色主题：深蓝黑底 + 青色数据色 #35c2f2；登录页为照片背景，左侧登录卡、右侧留空）
- 解析：pypdf / python-docx + 规则引擎；**抽不全时由 AI 兜底**；**图片/扫描件走 3065 多模态 OCR**（PyMuPDF 渲染 → 视觉模型抽字段）
- 向量：Ollama `bge-m3`(1024 维) → Milvus，支持语义检索、查重、岗位语义召回
- 存储：本地文件适配器（MinIO 未装，接口已留）

---

## 1. 启动

```bat
start.bat          :: 起 MySQL（若未运行）→ 建表导种子 → 起前后端 → 开浏览器
stop.bat           :: 停前后端（MySQL 需单独停）
```

- 前端 <http://127.0.0.1:5173>
- 接口文档 <http://127.0.0.1:8000/docs>
- 健康检查 <http://127.0.0.1:8000/api/health>

## 1.1 AI 网关（可选，但推荐）

`backend/.env`：

```
AI_ENABLED=1
AI_BASE_URL=http://127.0.0.1:3065/v1
AI_MODEL=deepseek-v4.1-flash
AI_API_KEY=<你的网关 Key>
AI_REASONING_EFFORT=medium
```

> 网关在 2026-11 把所有 `-solo` 后缀模型下线了，模型名现在是 `deepseek-v4.1-flash`（不带后缀）。
> 备用 `Doubao-Seed-2.1-Pro`、视觉 `Doubao-Seed-2.1-Turbo` 同名规则。模型名变更时只改 `.env` 即可。

用到 AI 的三处，都可降级：

| 场景 | 有 Key | 没 Key |
|---|---|---|
| 简历解析兜底 | 规则置信度 < 0.75 时让模型补齐学历/年限/姓名并合并 | 只用规则结果，页面显示"置信度" |
| 人才画像 | 模型改写摘要与用人建议（不编造经历） | 模板句，数字不变 |
| 简答题评分 | 关键词命中率 + 模型复核，两者取平均 | 只按关键词命中率 |

> 匹配打分**不接模型**：分数必须可复现、可核对，模型只用于表达与兜底。

## 2. 演示账号（密码统一 `123456`）

| 账号 | 角色 | 数据范围 | 能看到 |
|---|---|---|---|
| `hr_zhao` | HR 管理员 | 本部门 | 简历、岗位条件、匹配、测评、培训（可执行） |
| `admin` | 系统管理员 | 全公司 | 全部 + 系统用户/日志 |
| `pm_wang` | 业务负责人 | 本部门 | **已停用**（本期只做 HR + 普通员工） |
| `emp_chen` | 普通员工 | 本人 | **仅培训成长**（转正员工同此口径） |

> 本期只实现 **HR** 与 **普通员工** 两个角色。转正员工账号 = 手机号 + 初始密码（`Emp` + 6 位数字），
> 菜单只有「培训成长」，落地页 `/training`。

> 密码在 `scripts/init_db.py` 首次运行时写入（seed 里的 `ENC:test_placeholder` 会被覆盖）。

## 3. 验证（每次改动都跑）

```bat
cd backend
.venv\Scripts\python.exe scripts\init_db.py --check       :: 表结构与 seed 对齐核对
.venv\Scripts\python.exe scripts\smoke_test.py            :: 17 条接口/权限断言
.venv\Scripts\python.exe scripts\eval_match.py            :: 标注集回归（判定/分数/原因三项）
```

**全量回归（12 个脚本 196 项断言）**：

```bat
.venv\Scripts\python.exe scripts\s1_vector_test.py        :: 11  向量字段
.venv\Scripts\python.exe scripts\s2_brief_test.py         :: 18  简历摘要
.venv\Scripts\python.exe scripts\s3_identity_test.py      :: 21  身份去重
.venv\Scripts\python.exe scripts\s4_assignment_test.py    :: 27  测评绑定
.venv\Scripts\python.exe scripts\s5_onboard_test.py       :: 25  转正建号
.venv\Scripts\python.exe scripts\s6_import_test.py        :: 20  题库导入
.venv\Scripts\python.exe scripts\s7_acceptance_test.py    :: 22  六需求端到端验收
.venv\Scripts\python.exe scripts\training_test.py         :: 10
.venv\Scripts\python.exe scripts\vacancy_test.py          :: 6
.venv\Scripts\python.exe scripts\p1_test.py               :: 12
.venv\Scripts\python.exe scripts\p2_test.py               :: 7
```

当前实测：smoke **17/17**，eval **5/5 · 5/5 · 5/5**，S1–S7 + 既有脚本 **196/196**。

## 3.1 迁移与演示数据

```bat
.venv\Scripts\python.exe scripts\migrate_backend_v2.py    :: 统一迁移（S1–S6 结构+权限），幂等
.venv\Scripts\python.exe scripts\seed_demo_extra.py       :: 补齐 12 题/5 课/课后考核，幂等
```

> `init_db.py --reset` 会清空业务数据，seed 只有 3 题 2 课，**reset 后必须跑 `seed_demo_extra.py`**，
> 否则 `training_test` / `p1_test` 会因数据缺失失败（不是代码问题）。

样本简历在 `samples/`（PDF / DOCX / TXT / 一张图片用于验证 OCR 分支），
`scripts/make_samples.py` 可重新生成。

## 4. 目录

```
backend/
  app/core/          配置、DB、JWT、统一返回、鉴权与数据范围
  app/infrastructure/ ORM（38 表）、本地存储、技能词典、Milvus 适配
  app/services/      解析、匹配、简历、岗位、工作台、登录
                     + identity_service（身份去重）
                     + assignment_service（测评绑定 + exam_summary）
                     + onboard_service（转正建号）
                     + my_training_service（员工自助 + 归属校验）
                     + question_import_service（题库导入）
  app/api/           auth / resumes / job-profiles / matching / dashboard / system
                     + exams / exam_assignments / my_training / question_import / vector
  scripts/           init_db · make_samples · smoke_test · eval_match
                     + migrate_backend_v2（统一迁移）· seed_demo_extra（演示数据）
                     + s1~s7 回归脚本
frontend/           （旧前端，只读参照）
frontend-v2/        （新前端 Vite7 + React19 + TS，逐页重构中）
  src/pages/         Login / Dashboard / Resumes / JobProfiles / Matching / MatchDetail
  src/components/    Shell（侧栏+顶栏）、ui（ScoreBar、Drawer、Pill…）
  src/styles/        app.css（skill 基线）+ theme.css（抽签令牌）+ custom.css
```

## 5. 关键设计

- **统一返回** `{code, message, data}`，错误码沿用接口设计文档；全局异常处理器兜底。
- **数据范围按资源解析**：同一用户对简历可能是 `dept`、对岗位条件可能是 `all`，
  因此权限表存"权限码 → 范围"的映射，而不是一个全局 scope（`app/core/deps.py`）。
- **匹配可复现**：每次匹配把权重与阈值快照写进 `match_results.condition_detail`，
  改权重只影响下一次执行。
- **硬条件优先**：任一硬条件不满足 → 分数折算到合格线下、`passed=false`，但**不隐藏分数**，
  原因里逐条点名差在哪（不允许"综合素质不符"这类无法核对的措辞）。
- **解析队列并发安全**：`SELECT ... FOR UPDATE SKIP LOCKED` + 条件更新，检查影响行数。
- **人工修正只改档案**：修正后需重新匹配才生效（页面上明示）。

## 6. 已知限制（MVP 边界，不是 bug）

| 限制 | 说明 |
|---|---|
| 图片/扫描件 | 标记 `need_ocr`，不进入匹配；接 PaddleOCR 后补一个 parser 实现 |
| `.doc` 旧格式 | 不支持，提示走 OCR/人工 |
| 解析准确率 | 规则引擎，关键字段可核对 + 可人工修正；**不承诺 PRD 的 99%** |
| 队列 | 前端轮询逐份消费，未接 Celery |
| 培训/RAG/智能问数/Agent 编排 | **培训已可用**（诊断/计划/任务/台账）；RAG、智能问数、Agent 编排仍为空态 |
| 业务负责人角色 | 本期停用（只做 HR + 普通员工） |
| 员工自助答题 | 未做，本期仍是 HR 代答（按需求原文） |
| 老简历 | 标记 `is_current=0` 不物理删除，`?include_superseded=1` 可追溯 |
| 疑似重复合并 | 只报不合并（`/identity/suspected`），避免误合并丢人 |
| 题库导入 pdf | 扫描件不支持（需 OCR） |
| 题库导入 xlsx | 依赖表头识别，表头认不出时退回按行解析，效果较差 |

### 测评怎么反哺画像（v1.2 新增）

做完测评，成绩会按知识分类折成能力证据，混进画像，再影响匹配：

| 题目知识分类 | 折进画像维度 |
|---|---|
| 算法 / 模型 / 深度学习 / 框架 | 技术深度 |
| 工程 / 部署 / 性能 / 架构 / 数据库 | 工程能力 |
| 业务 / 产品 / 需求 / 指标 / 分析 | 业务理解 |
| 沟通 / 协作 / 团队 / 管理 / 项目 | 协作沟通 |
| 学习 / 成长 / 复盘 / 规划 | 成长性 |

- 该维得分率 = 该维已得分 ÷ 该维满分；**按题量折权**：1 题按 10%、2 题约 20%、3 题起满额 30%。
- 合成分 = 简历分 ×(1-w) + 测评分 ×w；测评分低于简历分时会把该项拉低，这是有意的（验证性证据）。
- 没有知识分类的题目**不进画像**（不硬塞），所以录题时务必选分类。
- 重新生成画像即生效；画像抽屉里有「测评证据（反哺）」逐维对照，能看出哪一维被测评拉动。

### 画像怎么参与匹配（v1.1 新增）

岗位条件里多了「画像能力基线」：技术深度 / 工程能力 / 业务理解 / 协作沟通 / 成长性，各填 0–100。
填了基线，该维度就按「实际能力 ÷ 基线」打分（超基线按 100 封顶，取各维平均），并占用「档案完整度」的权重席位；
不填，退回旧口径（按档案完整度算），历史分数不受影响。候选人没有画像时同样退回，详情页会注明。

## 7. 环境事实

- MySQL 9.4：`D:\mysql-9.4.0-winx64`，root/123456，库名 `ai_talent`
- Redis：`127.0.0.1:6379`（老版本，必须 `protocol=2`，已在 `core/db.py` 处理）
- Python：`backend\.venv`（3.12）
- 数据库重建：`python scripts/init_db.py --reset`（**会删库**）
