# PAGE-MAP · AI 数字化人才平台（新前端）

> 历史资料：原始路径、设计范围和验收记录仅用于追溯。当前目录和启动方式以 [项目 README](../../README.md) 为准。

版本 v0.1 · S1 产物 · 2026-11-03
目录决策：新前端在 `E:\AI数字化人才平台-相关文档\mvp\frontend-v2`；旧前端 `mvp/frontend` 与后端 `mvp/backend` 一律只读，不改一行。
本文件只做信息架构与页面契约，不含代码。

---

## 0. 事实基线（声明 vs 实测）

> **范围变更（2026-11-03）**：移动端适配暂缓。S5 逐页实现与 S6 门禁只验 1440 与 768；390 保留基础响应式但不做打磨、不列入本阶段验收。`ACCEPTANCE.md` 中 A13/B5 的 390 项标记为 deferred，恢复时再补。

| 项 | 输入声明 | 实测（证据） | 本项目的处理 |
|---|---|---|---|
| 技术栈 | 原为 Next.js 14，2026-11-03 解除限制 | 旧前端是 Vite 5.4 + React 18.3 + react-router 6.26（`mvp/frontend/package.json`） | 新目录用 **Vite 7 + React 19 + TypeScript 5.9（纯 SPA）**，理由见 §0.1；旧前端保留不动 |
| 依赖 | 原为"不新增"，已解除 | 旧前端只有 react / react-dom / react-router | 运行时 5 个：`react` `react-dom` `react-router-dom` `@tanstack/react-query` `lucide-react`；不引 UI 组件库、图表库、toast 库、i18n 库、Tailwind |
| 后端 | 已开发完成、不可改 | FastAPI：8 个 router（44 条路由）+ 1 条 app 级 `/api/health` = **45 个端点**，统一 `{code,message,data}` | 只消费现有接口；缺字段只记录，不编造 |
| 角色 | 按后端代码 | 4 角色：`admin` / `hr` / `biz` / `employee`，权限码 + `data_scope`（self/dept/all），`app/core/deps.py` | 按钮级权限读 `/api/auth/me` 的 `permissions`，不在前端写死角色名 |
| 数据范围 | 按后端代码 | 简历/匹配/工作台做行级过滤；岗位/画像/测评**未做**行级过滤（见 §3） | UI 口径按真实行为写，不把"本部门"贴在全局数据上 |
| 现有页面 | 自己定 | 旧前端 11 条业务路由 + 2 条重定向、11 个页面文件，缺系统管理、403、404、错题复习独立视图 | 新前端 14 条路由（见 §2） |
| 演示账号 | 无 | `admin` / `hr_zhao` / `pm_wang` / `emp_chen`，密码 `123456`（`scripts/init_db.py`） | 验收按这 4 个账号实测 |
| 运行环境 | 无 | 后端 8000，旧前端 5173，MySQL 3306，Redis 6379；AI 网关 `127.0.0.1:3065` 已启用并配了 Key（`backend/.env`），但接口仍可能降级，前端按"可缺席"处理 | 新前端 dev 5174（避开旧前端 5173），`/api/*` 由 Vite 代理到 8000 |
| 文案 | 必须中文 | 后端错误文案已是中文；旧前端无 i18n 体系 | 不引 i18n 库；文案集中到 `src/content/copy.ts`，key 用 `页面.区块.元素`，将来可替换 |

接口规模明细：认证 3、工作台 1、简历 8、岗位 8、匹配 4、画像 4、测评 13、系统 3、健康 1。

### 0.1 技术栈决策（为什么是这套）

| 选项 | 结论 | 理由 |
|---|---|---|
| Next.js 14/16 App Router | 不选 | 这是登录后的内部工作台：没有 SEO、没有首屏内容需求；SSR 只会多一层 Node 服务、多一套会话转发，静态产物部署与回滚都更麻烦 |
| **Vite 7 + React 19 + TS 5.9（纯 SPA）** | **选它** | 首屏预算最好控（React 19 + Router 6 + Query 约 95KB gzip，应用代码可控），路由级 `import()` 天然拆分；dev 启动秒级，14 个页面迭代最快 |
| Vue 3 / Svelte | 不选 | 三套门禁（inspect、axe、verify_*）都在 React 形态上验证过；换框架只增加未知，不增加产品价值 |
| UI 组件库（Ant / shadcn / MUI） | 不选 | S4 要求一个原子只实现一次并逐项过八态与 token 映射；组件库自带风格会和 S2 单一主题打架，覆写成本高于自建 |
| 图表库（ECharts / Recharts） | 不选 | 只有五维能力与分数分布两类图；手写 SVG 更可控，也不会带进彩虹色 |

版本锁定：`vite@7.3.7` + `@vitejs/plugin-react@5.1.0`（plugin-react 6 只配 Vite 8，还带 React Compiler 相关 peer，没必要）、`react@19.3.1`、`react-router-dom@6.30.6`（v7/v8 对 14 条业务路由没有收益）、`@tanstack/react-query@5.105.3`、`lucide-react@1.66.0`、`typescript@5.9.3`。

图标用 lucide：运行时就是内联 SVG + `currentColor`，tree-shake 后每图标约 1KB；不引第二套图标风格，也不手绘容易走形的图标集。

---

## 1. 角色与权限（以 seed + init_db 实际授权为准）

| 权限码 | admin | hr_zhao | pm_wang | emp_chen |
|---|---|---|---|---|
| `dashboard:view` | all | dept | 无 | self |
| `resume:view / create / edit / delete` | all | dept | 无 | 无 |
| `job:view` | all | all | all | 无 |
| `job:create / edit` | all | all | 无 | 无 |
| `job:delete` | all | **无** | 无 | 无 |
| `match:view / create` | all | dept | dept | 无 |
| `talent:view` | all | dept | dept | 无 |
| `talent:create` | all | dept | 无 | 无 |
| `exam:view` | all | dept | dept | 无 |
| `exam:create` | all | dept | 无 | 无 |
| `sys:view` | all | 无 | 无 | 无 |

要点：

1. `hr` 能改岗位但**不能删**（`init_db.ensure_permissions` 只授了 view/create/edit，menu 10 没有 delete）。删除按钮只对 `admin` 出现。
2. `pm_wang`（biz）没有 `dashboard:view`，登录后不能落在 `/dashboard`。落地页必须按 `menus` 里第一个 `allowed=true` 计算。
3. `emp_chen`（employee）只有 `dashboard:view(self)` 和 `kb:view(self)`；知识库没有接口，只能进空态页。
4. 测评接口不按部门过滤，`hr`、`biz` 看到的是全公司数据。UI 不得写"本部门测评"。

---

## 2. 页面矩阵

> 五态缩写：**L** loading｜**E** empty｜**Err** error｜**403** no-permission｜**OL** over-limit
> 性能预算三项固定：页面 API p95、LCP、该页首屏 JS（gzip）。全站基线见 `ACCEPTANCE.md` A 段。

| # | 页面（路由） | 用户任务（一句话） | 主接口 | 角色权限 | 五态 | 性能预算 | a11y 等级 | 验收人 |
|---|---|---|---|---|---|---|---|---|
| P00 | 登录 `/login` | 用一个账号进来，并立刻知道自己是谁、能看什么。 | `POST /api/auth/login`；守卫复用 `GET /api/auth/me` | 未登录公开；已登录访问跳落地页 | L 提交中禁用表单＋按钮转圈｜E 不适用（无列表）｜Err 401「用户名或密码错误」内联表单顶部｜403「账号已停用」单独文案｜OL 用户名 1–64、密码 1–128（后端 422），前端 maxlength＋余量提示 | ≤300ms · LCP ≤1.5s · JS ≤120KB | AA：label 显式关联、错误 `aria-live=assertive`、密码可见按钮 `aria-pressed` | `emp_chen`（最小权限）＋`hr_zhao`（主路径） |
| P01 | 智能工作台 `/dashboard` | 今天有多少简历卡在队列、最近一次匹配通过多少。 | `GET /api/dashboard/overview` | `dashboard:view`：admin all / hr dept / employee self；biz 无 | L 4 个指标＋队列骨架｜E scope=self 且 0 条 →「你名下还没有简历」｜Err 页内错误条＋重试｜403 → `/403` 带 `dashboard:view`｜OL 最近操作固定 8 条（后端硬编码），不分页 | ≤500ms · LCP ≤2.5s · JS ≤130KB | AA：`dl/dt/dd` 语义、状态不只靠颜色 | `emp_chen`（空态）＋`hr_zhao` |
| P02 | 简历智能筛选 `/resumes` | 把一批简历放进队列，确认解析结果能拿去匹配。 | `GET /api/resumes`；`POST /api/resumes/upload`；`GET /api/resumes/queue`；`POST /api/resumes/parse-next`；`DELETE /api/resumes/queue/{task_id}`；`GET /api/resumes/{id}`；`PATCH /api/resumes/{id}`；`GET /api/resumes/file/{key}` | `resume:view/create/edit/delete`（hr dept、admin all）；biz/employee 403 | L 表格 10 行骨架｜E 0 份＋上传入口＋队列说明｜Err 上传逐条失败原因（`accepted`/`rejected`）｜403 `resume:view`｜OL 单文件 >10MB 拒收（后端 400）；单批前台上限 20 份（UI 明示）；`parse-next` 一次只消费 1 份，进度按"第 i/N 份"显示 | ≤300ms · LCP ≤2.5s · JS ≤170KB | AA：`caption`＋`th scope`、上传支持键盘与拖拽、进度 `role=status` | `hr_zhao`＋`pm_wang`（403） |
| P03 | 岗位条件 `/job-profiles` | 定义"这个岗位到底要什么"，并当场知道条件会不会太严。 | `GET /api/positions`；`GET/POST /api/job-profiles`；`GET/PUT/DELETE /api/job-profiles/{id}`；`GET /api/job-profiles/{id}/summary`；`POST /api/job-profiles/{id}/dry-run` | `job:view`（hr all、biz all）；`job:create/edit`（仅 hr）；`job:delete`（仅 admin） | L 列表＋编辑器骨架｜E 0 个岗位＋新建｜Err 保存失败保留草稿｜403 `job:view`｜OL 条件行前端上限 20 行（后端无限制，UI 明示）；试算按 5 档分桶展示 | dry-run ≤1s（≤500 份）· LCP ≤2.5s · JS ≤170KB | AA：条件行 `fieldset/legend`、删除 `danger`＋确认框焦点陷阱 | `hr_zhao`（增改/试算）＋`admin`（删除）＋`pm_wang`（只读） |
| P04 | 岗位匹配 `/matching` | 选一个岗位跑一次匹配，先看谁够格、差在哪。 | `GET /api/job-profiles`（选择器）；`POST /api/matching/run`；`GET /api/matching/summary`；`GET /api/matching/lists` | `match:view/create`（hr dept、biz dept、admin all） | L 汇总＋名单骨架｜E 该岗位 0 条 →「还没跑匹配」｜Err 400「没有可匹配的简历，请先上传并解析」｜403 `match:view`｜OL `run` 会整批重建该岗位结果（幂等、无上限），可见简历 >500 份时二次确认 | run ≤3s（≤500 份）· LCP ≤2.5s · JS ≤180KB | AA：分数＝文字＋图形（图形 `aria-hidden`）、筛选组 `role=group` | `hr_zhao`＋`pm_wang` |
| P05 | 匹配详情 `/matching/{id}` | 这个分数是怎么算出来的，差在哪个条件。 | `GET /api/matching/{id}` | `match:view`＋行级校验（dept/self 不符 → 403「无权访问该匹配记录」） | L 详情骨架｜E 不适用（404 代替）｜Err 404「匹配记录不存在」｜403 行级 403 解释（不是菜单级）｜OL 简历原文 >2000 字折叠（UI 策略，明示） | ≤300ms · LCP ≤2.0s · JS ≤150KB | AA：维度表用 `table` 语义；原文 `pre-wrap` 但不用等宽字体 | `hr_zhao`＋`pm_wang`＋`admin` |
| P06 | 人才画像 `/talent-profiles` | 把简历与测评证据合成一张能解释的画像，决定用不用。 | `GET /api/talent-profiles`；`POST /api/talent-profiles/generate`；`GET /api/talent-profiles/{id}`；`GET /api/talent-profiles/meta/skills` | `talent:view`（hr/biz dept）；`talent:create`（仅 hr） | L 卡片骨架｜E 0 张 →「先解析简历再生成」｜Err 400「没有可生成画像的已解析简历」｜403 `talent:view`｜OL 一次 `generate` 处理全部可见已解析简历（无上限，显示将处理 N 份）；`ai_available=false` 时必须写"本次为规则生成" | generate ≤5s/10 份 · LCP ≤2.5s · JS ≤170KB | AA：五维必须数字可读（图形不能是唯一表达）；抽屉焦点陷阱＋归还焦点 | `hr_zhao`（生成）＋`pm_wang`（只读） |
| P07 | 测评中心 `/exams` | 组织一次测评：有题库、能出卷、看得到谁交了卷。 | `GET/POST /api/question-banks`；`GET/POST /api/questions`；`GET/POST /api/exams`；`GET /api/exam-submissions`；`GET /api/ai/status` | `exam:view`（hr/biz）；`exam:create`（仅 hr） | L 三区骨架｜E 无题库／无试卷／无答卷 三种空态各自给下一步｜Err AI 不可用 → 顶部「简答题仅关键词评分」｜403 `exam:view`｜OL 出卷题数 > 题库总数时后端取 min，UI 必须回显实际题数；答卷列表最近 100 条（硬编码）；题目 50/页 | ≤300ms · LCP ≤2.5s · JS ≤180KB | AA：三个区各有 `h2`；建库建卷控件有 label | `hr_zhao`＋`pm_wang`（只读） |
| P08 | 答题 `/exams/{id}/take` | 在时限内答完交卷，中途不丢答案。 | `GET /api/exams/{id}`；`POST /api/exams/{id}/submit` | `exam:view`；employee 无此权限（见 G1） | L 试卷骨架｜E 不适用｜Err 提交失败保留本地草稿＋重试｜403 `exam:view`｜OL 时长到点自动交卷（后端只存 `duration_minutes` 不校验，前端计时）；答案 `localStorage` 暂存，提交成功即清 | 首题可交互 ≤1.5s · LCP ≤2.0s · JS ≤140KB | AA+：每题 `fieldset/legend`、计时 `aria-live=polite`、全键盘可完成 | `hr_zhao`（本期代考；employee 不可用） |
| P09 | 成绩与错题 `/exams/result/{sid}` | 这份卷子得了多少、错在哪、接下来复习什么。 | `GET /api/exam-submissions/{sid}`；`GET /api/wrong-questions?candidate_name=`；`GET /api/review-plans?candidate_name=` | `exam:view` | L 骨架｜E 全对 →「本卷没有错题」｜Err 404「答卷不存在」｜403 `exam:view`｜OL 错题与复习计划各最近 200 条（硬编码），UI 标注"最近 200 条" | ≤400ms · LCP ≤2.0s · JS ≤150KB | AA：得分与合格线用文字表达；对错不只靠颜色 | `hr_zhao` |
| P10 | 系统管理 `/system` | 知道谁能进系统、谁能干什么、刚才谁动了什么。 | `GET /api/system/users`；`GET /api/system/roles`；`GET /api/system/operation-logs` | `sys:view`（仅 admin） | L 三表骨架｜E 无日志｜Err 重试｜403 `sys:view`｜OL 用户/日志 20 条/页（`page_size ≤200`），角色全量 | ≤300ms/表 · LCP ≤2.5s · JS ≤160KB | AA：`tablist`＋方向键；时间用 `time` 元素 | `admin`＋`hr_zhao`（403） |
| P11 | 无权访问 `/403` | 知道自己缺哪个权限、该找谁，而不是看空白。 | 无（路由参数读 `code`/`from`）；`GET /api/auth/me` 校验会话 | 所有已登录角色 | 静态页；必须显示：缺失权限码、当前账号与角色、一个"回到我可用的首页"按钮 | 无请求 · LCP ≤1.0s · JS ≤110KB | AA：`h1`＋说明＋一个主行动 | `pm_wang` 访问 `/resumes` |
| P12 | 页面不存在 `/404` | 知道地址错了，能回去。 | 无 | 所有角色 | 静态页；显示请求路径＋返回落地页 | 无请求 · LCP ≤1.0s · JS ≤110KB | AA | 任意角色 |
| P13 | 里程碑空态 `/soon/{module}` | 知道这个模块还没上线、属于哪个里程碑。 | 无（读 `/api/auth/me` 的 `menus` 判断是否允许） | 对应菜单 `allowed=true` 才可进，否则 `/403` | 静态页；覆盖 3 个模块：数据决策、知识库、Agent 编排；文案写"该模块在后续里程碑"，不放假数据（培训成长、向量已转正为 P16 / P15） | 无请求 · LCP ≤1.0s · JS ≤110KB | AA | `admin`（3 个）＋`emp_chen`（知识库） |
| P14 | 空缺预警与储备 `/vacancy` | 哪个岗位要招、缺几人、储备池里谁最接近。 | `GET /api/job-profiles/alerts`；`GET /api/job-profiles/{id}/reserve` | `job:view`（hr all、biz all、admin all） | L 预警卡＋储备表骨架｜E 无岗位 / 无预警 / 无储备 三种空态｜Err 重试｜403 `job:view`｜OL 预警按岗位全量（无上限）；储备列表后端 `page_size` 上限 | ≤400ms · LCP ≤2.5s · JS ≤170KB | AA：四级预警不只靠颜色（文字 + 图标）；储备行可进匹配详情 | `hr_zhao`＋`pm_wang`（只读） |
| P15 | 语义检索与查重 `/semantic` | 用一句话找简历、找出疑似重复、按岗位语义召回。 | `GET /api/vector/status`；`POST /api/vector/index`；`GET /api/resumes/semantic?q=`；`GET /api/resumes/duplicates`；`GET /api/job-profiles/{id}/semantic-candidates` | `resume:view`（检索/查重/状态）、`resume:create`（建索引）、`job:view`（岗位召回） | L 状态卡＋结果骨架｜E 向量库未建 → 引导建索引｜Err Milvus/Ollama 不可用 → `available:false` 说明｜403 `resume:view`｜OL 检索 top-K（后端硬编码）、查重阈值（≥0.x） | ≤500ms（语义）· LCP ≤2.5s · JS ≤170KB | AA：语义命中显示相似度数值；查重对成对展示＋人工确认（不自动合并） | `hr_zhao`（建索引）＋`pm_wang`（只读） |
| P16 | 培训成长 `/training` | 看出能力缺口，生成培养计划，跟踪到提能。 | `GET/POST /api/training-courses`；`PUT/DELETE /api/training-courses/{id}`；`GET /api/training/diagnose`；`POST /api/prejob-plans/generate`；`GET /api/prejob-plans`；`GET /api/prejob-plans/{id}`；`POST /api/prejob-plans/tasks/{id}/progress|complete|assess`；`GET /api/training/ledger` | `train:view/create/edit/delete`（hr 全权、biz 只读、admin 全、emp 403） | L 四标签骨架｜E 无课程 / 无计划 / 无台账 各自空态｜Err 重试｜403 `train:view`｜OL 任务进度 0–100、学时达标才可 complete（后端校验，防挂机）；台账/计划 `page_size` 上限 | ≤400ms · LCP ≤2.5s · JS ≤180KB | AA：`tablist`＋方向键；进度/学时数字可读；考核结果文字说明 | `hr_zhao`（全流程）＋`pm_wang`（只读）＋`admin` |

已拍板：P10 系统管理纳入本期（2026-11-03），仅 `admin` 可见，三个标签各自满足五态。

## 2.1 本轮范围补充（2026-11-03，依据运行中 `/openapi.json`）

对齐产物：`接口与模块清单.md`（用户提供，声称 68 路由/38 表）↔ 运行中 `/openapi.json`（实为 59 路径）↔ 已实现页面。缺口如下，全部补进 PAGE-MAP：

| 缺口 | 归宿 | 说明 |
|---|---|---|
| 岗位 `parse-jd`（JD→条件草稿）、`summary`（岗位汇总）、`dry-run`（试算）、`headcount`（名额） | P03 扩展 | 编辑器补「名额」字段 +「从 JD 粘贴」对话框；试算已有（走 dry-run）；summary 并入编辑器/详情 |
| 岗位 `alerts` / `reserve` | **P14 新页** | 空缺预警 + 储备推荐 |
| 画像 `trend` / `analysis` | P06 扩展 | 抽屉加「能力趋势」「AI 结构分析」两段 |
| 测评 `adaptive`（自适应组卷） | P07 扩展 | 出卷对话框加「自适应」模式 |
| 简历 `DELETE /queue/{task_id}` | P02 扩展 | 队列抽屉补「移除任务」 |
| 向量 `status/index/semantic/duplicates/semantic-candidates` | **P15 新页** | 依赖 Milvus/Ollama，见 G25 |
| 培训成长 12 条 | **P16 新页** | 原 `/soon` 转正 |

开发顺序建议（同一套 S 逻辑，一次一页）：先收尾原计划里不阻塞的 **P08 答题 → P09 成绩 → P10 系统**，再补 **P14 预警 → P15 向量 → P16 培训**，最后把 P03/P06/P07/P02 的扩展项并入对应页。P15 需你启动 Milvus(19530) + Ollama(11434)。

---

## 3. 数据范围真相表（决定页面口径怎么写）

| 接口组 | 行级过滤 | 证据 | UI 必须怎么写 |
|---|---|---|---|
| `/api/dashboard/overview` | 是 | `dashboard_service.apply_scope`，按 resume/match 取更大范围 | 显示"本部门 / 全公司 / 本人" |
| `/api/resumes*` | 是 | `resume_service` 的 `apply_scope` + `_visible` | 显示当前范围 |
| `/api/matching/lists` | 是 | `match_service.lists` 用 `apply_scope` | 显示当前范围 |
| `/api/matching/{id}` | 是（显式 403） | `detail()` 校验 `dept_id` / `created_by` | 403 文案区分"行级无权" |
| `/api/job-profiles*` | **否** | `list_jobs` / `get_job` 不接收 `user` | 写"全部岗位"，不写"本部门" |
| `/api/talent-profiles*` | **否** | `list_profiles(db, user, ...)` 收了 user 但未使用 | 写"全部画像" |
| `/api/exams*` | **否** | `list_exams` / `list_submissions` 不接收 `user` | 写"全公司测评" |
| `/api/system*` | 不适用 | 仅 `sys:view` | 仅 admin 可见 |
| `/api/job-profiles/alerts` / `/{id}/reserve` | 是 | `job_service` 用 `apply_scope` 统计可见简历 | 显示当前范围 |
| `/api/training*`（课程/诊断/计划/台账） | **否** | `list_courses` / `diagnose` / `list_plans` 不接收 `user` | 写"全平台培训"，不写"本部门" |
| `/api/resumes/semantic` / `/api/resumes/duplicates` | 是 | `vector_service` 用 `apply_scope`（resume/match） | 显示当前范围 |
| `/api/vector/status` / `/api/vector/index` | 不适用（全局） | 状态与重建索引不按人 | 建索引是全局动作，需 `resume:create` |

结论：**菜单级 RBAC 与行级数据范围不是一回事**。前端只做菜单/按钮显隐，不做"假过滤"；口径文案必须与上表一致，否则用户会以为被过滤了。

---

## 4. 导航与落地规则

1. 侧栏只渲染 `menus.allowed=true` 的项；显示顺序按业务链路固定为 工作台 → 简历 → 岗位条件 → 匹配 → 人才画像 → 测评 → 系统，不直接用后端 `sort`（`sort` 把后加的两个菜单排在系统管理之后）。
2. 落地页 = `menus` 中第一个 `allowed=true` 的 `path`，不是写死 `/dashboard`。实测：`hr_zhao`→`/dashboard`，`pm_wang`→`/matching`，`emp_chen`→`/dashboard`，`admin`→`/dashboard`。
3. 登录后回跳：`/login?returnTo=<原路径>`，只接受站内相对路径，防开放重定向。
4. 401：清 token → 跳 `/login?returnTo=`。403：跳 `/403?code=<权限码>&from=<原路径>`，页面必须解释，不留白。
5. 后端下发了 9 个菜单，其中培训/数据决策/知识库/Agent 无接口。admin 会看到这 4 项，`emp_chen` 会看到知识库；统一进 `/soon/{module}` 空态，不是死链。
6. 会话 480 分钟（`JWT_TTL_MINUTES=480`）；不做静默续期，过期按 401 处理。
7. 旧前端的 `/job-profiles` 不在后端菜单里（menu 10 是 MVP 扩展项），新前端保留该路由并在侧栏显示，权限 `job:view`。
8. 主题：Corporate Trust 全站浅色（Indigo `#4F46E5` + Violet `#7C3AED`）；`index.html` 固定 `data-theme="light"`，原白天/黑夜切换按钮已下线。细则见 `DESIGN.md` 顶部“当前状态”。

---

## 5. 五态字典（全站同一套触发方式）

| 态 | 视觉/内容要求 | 触发方式（可复现） |
|---|---|---|
| loading | 骨架行/骨架块，尺寸与真实内容一致，不塌布局，不用全屏 spinner | 节流网络到 Slow 3G，或首屏请求未返回时截屏 |
| empty | 一句解释＋一个可行的下一步（有权限时）；不显示 0 的假图表 | 用 `emp_chen` 看工作台；用空库看题库/试卷/答卷 |
| error | 错误码＋后端原文 `message`＋重试按钮；不吞错误、不弹无声 toast | 停掉后端（`stop.bat`）后刷新，或用不存在 id 触发 404 |
| no-permission | 跳 `/403`，显示权限码、当前角色、范围、返回入口 | `pm_wang` 访问 `/resumes`；`hr_zhao` 访问 `/system` |
| over-limit | 说清上限是多少、当前是多少、怎么处理 | 上传 >10MB 文件；出卷题数填大于题库总数；`page_size=201` |

---

## 6. 接口清单（45 个，前端归属）

| 模块 | 端点 | 权限 | 用在 |
|---|---|---|---|
| 认证 | `POST /api/auth/login` | 公开 | P00 |
| | `POST /api/auth/logout` | 登录态 | Shell |
| | `GET /api/auth/me` | 登录态 | 全局守卫、P11/P13 |
| 工作台 | `GET /api/dashboard/overview` | `dashboard:view` | P01 |
| 简历 | `POST /api/resumes/upload` | `resume:create` | P02 |
| | `GET /api/resumes/queue` | `resume:view` | P02 |
| | `POST /api/resumes/parse-next` | `resume:create` | P02 |
| | `GET /api/resumes` | `resume:view` | P02 |
| | `GET /api/resumes/file/{key}` | `resume:view` | P02 下载/预览 |
| | `GET /api/resumes/{id}` | `resume:view` | P02 详情 |
| | `PATCH /api/resumes/{id}` | `resume:edit` | P02 人工修正 |
| | `DELETE /api/resumes/queue/{task_id}` | `resume:delete` | P02 |
| 岗位 | `GET /api/positions` | `job:view` | P03 |
| | `GET /api/job-profiles` | `job:view` | P03、P04 选择器 |
| | `POST /api/job-profiles` | `job:create` | P03 |
| | `GET /api/job-profiles/{id}` | `job:view` | P03 |
| | `PUT /api/job-profiles/{id}` | `job:edit` | P03 |
| | `DELETE /api/job-profiles/{id}` | `job:delete` | P03（仅 admin） |
| | `GET /api/job-profiles/{id}/summary` | `job:view` | P03 |
| | `POST /api/job-profiles/{id}/dry-run` | `job:view` | P03 试算 |
| 匹配 | `POST /api/matching/run` | `match:create` | P04 |
| | `GET /api/matching/summary` | `match:view` | P04 |
| | `GET /api/matching/lists` | `match:view` | P04 |
| | `GET /api/matching/{match_id}` | `match:view` | P05 |
| 画像 | `GET /api/talent-profiles` | `talent:view` | P06 |
| | `POST /api/talent-profiles/generate` | `talent:create` | P06 |
| | `GET /api/talent-profiles/{id}` | `talent:view` | P06 抽屉 |
| | `GET /api/talent-profiles/meta/skills` | `talent:view` | P06 技能筛选 |
| 测评 | `GET /api/question-banks` | `exam:view` | P07 |
| | `POST /api/question-banks` | `exam:create` | P07 |
| | `GET /api/questions` | `exam:view` | P07 |
| | `POST /api/questions` | `exam:create` | P07 |
| | `GET /api/exams` | `exam:view` | P07 |
| | `POST /api/exams` | `exam:create` | P07 |
| | `GET /api/exams/{id}` | `exam:view` | P08 |
| | `POST /api/exams/{id}/submit` | `exam:view` | P08 |
| | `GET /api/exam-submissions` | `exam:view` | P07 |
| | `GET /api/exam-submissions/{id}` | `exam:view` | P09 |
| | `GET /api/wrong-questions` | `exam:view` | P09 |
| | `GET /api/review-plans` | `exam:view` | P09 |
| | `GET /api/ai/status` | `exam:view` | P07 能力口径 |
| 系统 | `GET /api/system/users` | `sys:view` | P10 |
| | `GET /api/system/roles` | `sys:view` | P10 |
| | `GET /api/system/operation-logs` | `sys:view` | P10 |
| 健康 | `GET /api/health` | 公开 | 启动自检（不上面） |

未使用的后端能力：`export` 动作有授权但没有导出端点，前端不做导出按钮。

---

## 7. 契约缺口与默认处理（每条都有默认，不阻塞）

| # | 缺口 | 影响 | 本期默认处理 | 待你确认 |
|---|---|---|---|---|
| G1 | `employee` 没有 `exam:view`，但答题/交卷接口要求 `exam:view` | 员工不能自助测评 | 本期测评定位为"HR 组织的内测"：由 HR 登录后开卷、代填考生姓名、代录成绩；页面写清"由 HR 代录"，不假装员工可登录答题 | 已确认（2026-11-03） |
| G2 | `biz` 没有 `dashboard:view`，但旧前端写死落地 `/dashboard` | 业务负责人一登录就 403 | 落地页按菜单计算（§4.2），`pm_wang` 落到 `/matching` | 否 |
| G3 | `admin` 会看到 4 个无接口菜单；`employee` 会看到知识库 | 死链 | 统一 `/soon/{module}` 空态，文案写"后续里程碑"，不放假数据 | 否 |
| G4 | `hr` 没有 `job:delete` | 删除按钮越权 403 | 按 `permissions` 隐藏；只有 admin 看到删除 | 否 |
| G5 | README 写"`pm_wang` 匹配只读"，但 `init_db` 给 role 3 授了 `match:create` | 文档与代码冲突 | 以接口为准：`pm_wang` 可执行匹配；在页面交付说明里注明 | 否 |
| G6 | 多处硬编码上限：最近操作 8、答卷 100、错题 200、复习计划 200、解析日志 20 | 用户以为看全了 | UI 明示"最近 N 条"；不做"加载更多"的假承诺 | 否 |
| G7 | 旧前端 401 只清 token 不跳转；403 无页面级解释 | 越权体验断 | 新前端全局拦截：401→登录、403→`/403` 带权限码 | 否 |
| G8 | 解析无进度推送，`parse-next` 一次只处理 1 份 | 批量上传后要轮询 | 前端串行轮询并显示"第 i/N 份"，可中止；不并发打接口 | 否 |
| G9 | 测评/画像/岗位接口忽略行级范围 | UI 口径会误导 | 按 §3 写"全部/全公司" | 否 |
| G10 | 后端无候选人主数据；`talent_profiles.candidate_id` 实际存 `parsed_resumes.id` | 画像与简历的对应关系不能按"候选人"讲 | UI 用"简历 / 画像"表述，不出现"候选人档案"这类超范围概念 | 否 |
| G11 | `/api/auth/me` 返回的 `data_scope` 是"所有权限里的最大值"（hr 因为有 `job:view=all`，会显示"全公司"），而登录接口返回的是 resume 范围 | 侧栏显示一个全局范围标签会误导，尤其简历页实际只到本部门 | 侧栏只显示部门名与角色，不显示全局数据范围；页面文案按 §3 的真实过滤口径写，不写"本部门" | 否 |
| G12 | 工作台的 `recent_operations` 与 `match` 统计（passed / failed / avg_score）不按数据范围过滤，`queue` 也不过滤 | 员工会看到别人的匹配汇总；HR 的简历计数是本部门，匹配计数却是全平台 | 队列改用 `files.by_status`（已按范围过滤）；无 `match:view` 的账号隐藏匹配块；操作日志只给 admin/hr 并标"全平台"；匹配计数口径写进 P01 交付说明 | 否 |
| G13 | `job_profiles` 没有 `updated_at`，只有 `created_at` | 列表无法展示"更新时间" | 表头改"创建时间"，按真实字段展示 | 否 |
| G14 | 后端硬条件白名单有"专业/城市"，但 `_hard_fail` 只判学历、技能、工作年限 | 提供专业/城市会让用户以为条件生效 | 编辑器只提供三个真正参与判定的字段，提示写明后端口径 | 否 |
| G15 | PRD 文案把"五维权重"写成技术深度/工程能力等画像维度，后端权重键是 education/skills/experience/project/other/ability | 用画像维度当权重会让 `_norm_weights` 归一化到未知键，匹配失真 | 权重按后端评分维度渲染（含已有的 ability 座位），画像五维放在"能力基线"；写进 P03 交付说明 | 否 |
| G16 | `/matching/summary` 不接收用户，统计全平台；`/matching/lists` 按数据范围过滤 | hr/biz 看到的"扫描/通过/未通过/平均分"可能大于名单实际条数 | 统计标注为"本岗位全部结果"；名单右上角显示过滤后条数；写进 P04 交付说明，待后端给 summary 加范围参数 | 否 |
| G17 | `/matching/{id}` 不返回 `job_profile_id`，只返回岗位名 | 详情页"返回名单"无法知道该回到哪个岗位的筛选 | 详情链接统一带 `?job=<id>`；直接打开无参数时回未筛选名单；不伪造岗位 id | 否 |
| G18 | 匹配详情不返回测评证据，`condition_detail` 只有硬条件、五维评分与能力基线 | COPY 里 P05 的"测评证据"没有数据来源 | P05 只展示能力基线；测评证据留到 P06/P07 的画像与测评接口 | 否 |
| G19 | `/talent-profiles` 列表与 `/{id}` 详情不接收范围过滤，返回全平台画像 | hr/biz 会看到别的部门的画像 | 前端不写"本部门"；按"平台画像库"口径展示，写进 P06 交付说明，待后端给 list/detail 加范围参数 | 否 |
| G20 | `talent_profiles.candidate_id` 存 `parsed_resumes.id`，同一人有多份简历会生成多张画像，同名不合并 | 列表出现同名重复卡片 | 前端按记录原样展示，不做合并；生成对话框明确"处理全部已解析简历"；写进 P06 交付说明 | 否 |
| G21 | 测评四个读接口（题库/题目/试卷/答卷）都不接收用户、不按数据范围过滤 | hr/biz 看到全平台题库与答卷 | 前端按"平台级测评库"口径展示，不写"本部门"；写进 P07 交付说明 | 否 |
| G22 | 文档称 68 条路由，运行中 `/openapi.json` 实为 59 条路径 | 若按 68 规划会多出 9 个不存在的端点 | 以 `/openapi.json` 为准；差异按 method 计数口径记，不阻塞 | 否 |
| G23 | `job_profiles.headcount`（名额）是新增字段，P03 编辑器未含 | 空缺预警无依据（名额缺失时按 1 计） | P03 编辑器补「名额」输入；P14 预警页直接读 `headcount` | 否 |
| G24 | 培训成长接口不按数据范围过滤（课程/诊断/计划/台账均不接收 user） | hr/biz 看到全平台课程与计划 | UI 写"全平台培训"；待后端给培训接口加范围参数 | 否 |
| G25 | 向量模块依赖 Milvus(19530) + Ollama(11434)，未启动时 `vector/status` 返回 `available:false` | 语义检索/查重/召回不可用 | P15 页面给"未启用"说明 + 建索引入口（disabled）；前端不自行拉起服务，用户需先启动 | 否 |
| G26 | 画像 `trend/analysis`、测评 `adaptive`、岗位 `parse-jd/summary/dry-run`、简历 `queue/{id}` DELETE 是既有页面的扩展 | 不开新页，但漏做会少功能 | 并入 P03/P06/P07/P02 对应页；P03 补名额字段 | 否 |
| G27 | 选择题标准答案混用格式：部分题存选项文本（如「快速排序」「PyTorch,TensorFlow」），部分存字母（如「B」） | 答题页统一提交选项文本，字母答案的题会被判错（实测 7 题里 4 题受此影响） | 前端按旧前端同口径提交选项文本；不猜答案、不改后端；写进 P08 交付说明，待后端统一答案格式或前端读答案（试卷接口不返答案） | 否 |
| G28 | `exam-submissions/{id}` 不返回 `exam_id`；`review-plans` 无 `exam_id`，只有题干文本 | 成绩页无法「再做一次」，复习计划只能按题干文本匹配本卷错题，同题干跨试卷会混入 | 复习计划按题干集合过滤并标「仅本卷相关」；不伪造 exam_id；写进 P09 交付说明 | 否 |
| G29 | admin 权限下发为通配符 `*:view/*:create/...`，不是 `sys:view` 这类精确码 | 前端用 `permissions.includes("x:y")` 会把 admin 误判成无权限（P10 首次暴露） | 已修：`lib/permission.ts` 的 `hasPermission` 同时匹配 `x:y` 与 `*:y`，与后端 `has_perm` 同口径；后续新页面必须用它 | 已修 |
| G30 | `job-profiles/{id}/reserve` 无分页、无 limit，`alerts` 也无分页；`/matching/lists` 最大 200 | 储备池全量返回；储备行跳匹配详情需按 `parsed_resume_id` 反查匹配列表，超过 200 条时部分行只能显示纯文本 | 储备池全量展示（演示 8 份）；姓名链接用 `page_size=200` 反查，查不到就退化为纯文本，不伪造 ID；写进 P14 交付说明 | 否 |
| G31 | 向量写入不幂等：`/vector/index`、`/resumes/duplicates`、`/job-profiles/{id}/semantic-candidates` 的 upsert 会追加行；查重只写 `id/vector/name` | 实测 6 条简历在多次查重后计数 6→18→36；缺字段的重复行会让召回结果的教育/年限/技能变成「暂无/0 年」 | 前端在重建确认里明示「会追加行」；演示前清空 `resume_vectors`/`job_vectors` 后重建（6/2）；要求后端改为 delete+insert 或按 id 真 upsert；写进 P15 交付说明 | 否 |
| G32 | `hr_zhao` 实际没有 `train:delete`（PAGE-MAP 原写「hr 全权」） | 课程列表对 hr 不显示「删除」，只有 admin 能删 | 前端按真实权限渲染；交付说明记录；要 hr 能删需后端补权限 | 否 |
| G33 | 培训数据有几处不自洽：计划任务可「已完成但 0 分钟 / 0%」；台账有同一考核的重复行；`assess` 只校验考生姓名，不校验提交是否属于任务的 `exam_id` | 台账会出现重复记录；考核可拿别的卷的提交；任务完成口径看起来矛盾 | UI 原样展示，不补假数据；考核入口只在「同候选人 + 同 exam_id 有提交」时出现，否则提示去做测评；写进 P16 交付说明 | 否 |

### 7.1 已拍板（2026-11-03）

| 项 | 决定 |
|---|---|
| G1 员工答题 | 按推荐执行：本期由 HR 代开卷、代录考生姓名与成绩，页面写清口径；不推动后端改权限 |
| P10 系统管理 | 按推荐执行：纳入本期，仅 `admin` 可见，三个标签（用户 / 角色 / 操作日志） |

---

## 8. 明确不在本期（无接口，不做页面，不做假数据）

培训课程、数据决策（NL2SQL/问数）、RAG 知识库问答、Agent 编排、候选人管理、面试与邀约、OCR 图片简历、查重合并、语义检索、导出、移动端/小程序、多语言。
处理方式：菜单进 `/soon?menu=<名称>` 空态，文案说明本期未做；不在本期验收范围内。

---

## 9. S5 逐页实现顺序（一次只做一页，做完即停）

1. 全局：Vite + React 19 + TS 脚手架（只有配置，无业务代码）→ `tokens.json` 生成 CSS 变量 → 根布局/字体 → `Shell`（侧栏、顶栏、范围标签、退出）
2. 原子组件：Button / Input / Select(listbox) / Table / Dialog / Drawer / Toast(live region) / Badge / ProgressBar / Tabs
3. P00 登录 → P01 工作台 → P02 简历 → P03 岗位 → P04 匹配 → P05 匹配详情 → P06 画像 → P07 测评中心 → P08 答题 → P09 成绩与错题 → P10 系统 → P11/P12/P13 异常与空态
4. 收尾：全站回归（4 账号 × 14 路由）、门禁三连、性能读数

每页交付物固定六件：文件清单、五态触发方式、权限缺省表现、文案 key、埋点事件名与字段、自检读数。

---

## 10. 本阶段没做的事

- 没有写任何代码，没有初始化 `package.json`，没有跑构建。
- 没有改后端、没有改旧前端。
- 没有定视觉方向（S3 才做），没有定 token 值（S2 才做）。
