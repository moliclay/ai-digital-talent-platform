# TODOLIST · 后端 v2 前端适配

> 历史资料：原始路径、设计范围和验收记录仅用于追溯。当前目录和启动方式以 [项目 README](../../README.md) 为准。

> 状态：**未开工**，仅方案拆解
> 方案：`deliveries/BACKEND-V2-前端适配方案.md`
> 约定：只改 `mvp/frontend-v2`，不改后端、不改旧前端；完成一项勾一项，验收以真实接口输出为准。

---

## P0 基础能力（阻塞项，先做）

- [x] **T0.1 角色落地修复**（S）
  - 改 `src/lib/api.ts`：`landingPath` 支持 `/training`，并回退到 `me.menus` 第一个 `allowed` 的 path。
  - 验收：`emp_chen` 登录后落 `/training`，不是 `/403`；`hr_zhao` 仍落 `/dashboard`。

- [x] **T0.2 路由权限守卫**（M）
  - `app.tsx` 增加 `RequireMenu`，按 `/auth/me` 的 `menus.allowed` 拦 HR 路由。
  - `/exams/:id/take`、`/exams/result/:sid` 归 `/exams`；`/matching/:id` 归 `/matching`；`/403`、`/soon` 放行。
  - 验收：员工直接输入 `/resumes`、`/exams`、`/talent-profiles` → `/403`，不请求业务接口。

- [x] **T0.3 共享契约类型**（M）
  - 新增 `ResumeBrief`、`ExamSummary`、`ExamSummaryItem`、`ResumeIdentity`、`ExamAssignment`、`QuestionDraft`、`ImportResult`、`MyTraining*`、`Audience`。
  - 补齐 `VectorStatus.milvus.expected_count/stale`、`ResumeRow/Detail` 新字段。
  - 验收：`tsc --noEmit` 0；旧页面不因字段新增报错。

- [x] **T0.4 共用组件**（M）
  - `ResumeBriefCell`：名称可点/置灰、学历、专业、年限、skills_top + `+N`、文件名。
  - `ExamStateBadge`：none / assigned / submitted 三态。
  - `AudienceFilter`：全部/候选人/员工。
  - 验收：三个组件在 390/768/1440 下无溢出，键盘可操作。

- [x] **T0.5 全局简历详情 Host**（M）
  - 新增 `src/components/resume-detail-host.tsx`，挂在 AppShell，读 `?resume=<id>`。
  - 关闭时删除 query，保留当前页面和筛选；`onSaved` 刷新 `["resumes"]`。
  - P02 行点击改为写 query，移除本地 `detailId` 依赖。
  - 验收：任意页 `?resume=6` 能打开详情；关闭后回原页；无权限 id 有错误态。

---

## P1 简历域（identity + onboard）

- [x] **T1.1 列表现行/历史**（S）
  - 加「显示历史版本」开关；请求 `include_superseded=1`；查询 key 带 history；切换重置 page。
  - 验收：默认 6 条现行；开启后出现旧版；旧版置灰 + 「已被新版本替代」。

- [x] **T1.2 列表徽标**（M）
  - 姓名旁显示「已转正」（`employee_user_id` 非空）。
  - 新增「测评」列：`exam_summary.label` 三态徽标，hover 展示试卷分数。
  - 验收：none/assigned/submitted 三态在真实数据中正确显示。

- [x] **T1.3 疑似重复提示**（M）
  - 调 `GET /resumes/identity/suspected`；`total>0` 显示顶部 warning banner。
  - 弹窗按组展示姓名/学历/专业/ids；组内可点详情；不出现自动合并按钮。
  - 「重新计算身份」放进二次确认，调 `POST /identity/reconcile`；展示 total/keyed/superseded。
  - 验收：当前库 2 组（陈宇、王峰）可见；reconcile 幂等。

- [x] **T1.4 详情两栏重构**（L）
  - 880px 弹窗改主栏 + 侧栏；390 堆叠。
  - 主栏：基本信息、技能、优势、解析记录、简历原文。
  - 侧栏：身份与版本、测评状态、转为正式员工。
  - 编辑态收起侧栏；旧版本禁止编辑并提示「已被新版本替代」。
  - 验收：1440/1910 两栏比例正常；390 单列可滚动；原修正档案流程不回归。

- [x] **T1.5 身份时间轴**（M）
  - `identity.siblings` 按新到旧展示；现行高亮；旧版点击可查看，但禁用编辑。
  - 旧版顶部提供「查看现行版本」→ `superseded_by`。
  - 验收：陈宇两份版本可切换；现行/旧版标识正确。

- [x] **T1.6 详情测评摘要**（M）
  - `exam_summary.items` 渲染试卷名、受众、状态、分数/合格线、deadline。
  - submitted 且有 submission_id → `/exams/result/{sid}`；无绑定显示空态 + 「去测评页」。
  - 验收：none/assigned/submitted 三种详情均可读。

- [x] **T1.7 转正建号**（L）
  - 仅 `canEdit && !employee_user_id && phone` 可点；无手机号禁用 + 提示。
  - 二次确认 → `POST /resumes/{id}/onboard`，不选部门，默认沿用后端。
  - 成功弹窗展示账号=手机号、一次性初始密码、复制按钮；关闭后清空 state，不写 localStorage。
  - 400/409 原样展示；409 刷新详情。
  - 验收：成功只显示一次密码；重复转正 409；无手机号 400；列表出现「已转正」。

- [x] **T1.8 旧版行跳转**（S）
  - 旧版姓名点击打开 `superseded_by` 的现行详情；没有现行则保持只读并提示。
  - 验收：旧版行不会误开旧版编辑。

---

## P2 语义检索 / 向量

- [x] **T2.1 P15 brief 类型替换**（M）
  - `SearchItem/DuplicatePair/Candidate` 改为 `ResumeBrief`；删掉 `skills: string` 的旧字段。
  - 验收：真实 `/resumes/semantic`、`/duplicates`、`/semantic-candidates` 直接映射无 undefined。

- [x] **T2.2 语义检索表**（M）
  - 姓名 → `?resume=id`；学历、专业、年限、skills_top chips + `+N`、文件名；相似度保留。
  - `accessible=false` 置灰不可点，`title` 说明无权。
  - 验收：程磊/张伟结果可点，详情在语义页上方打开；删除技能字段不再显示「暂无」。

- [x] **T2.3 查重 A/B**（M）
  - A/B 两列都用 `ResumeBriefCell`，相似度独立列；两侧可分别点击。
  - 1440/768 隐藏次要信息但不隐藏姓名/相似度。
  - 验收：`a=1 b=4` 两侧均可打开详情；无权限侧置灰。

- [x] **T2.4 岗位召回**（S）
  - 使用同一 brief 组件；`similarity` 展示，不误用 `score`。
  - 验收：岗位召回列表字段完整、无「暂无」学历。

- [x] **T2.5 向量状态过期提示**（M）
  - 状态卡显示 `resume_count / expected_count`；`stale=true` 黄色提示 + 「修复过期索引」。
  - 调 `POST /vector/reindex-if-stale`；`rebuilt=false` 提示「本来是最新的」；成功后刷新 status/检索/查重/召回。
  - 原「重建索引」改为「全量重建」，与修复区分。
  - 验收：当前 `6/6 stale=false`；模拟过期时修复返回 rebuilt 与计数。

---

## P3 测评域

- [x] **T3.1 受众筛选与类型**（M）
  - `Bank/Exam` 加 audience；题库、试卷查询传 `?audience=`；显示受众徽标。
  - 验收：全部/候选人/员工切换后列表正确，当前库 candidate 显示正常。

- [x] **T3.2 创建题库/试卷受众**（M）
  - `BankDialog` 增加受众；`ExamDialog` 增加受众，题库按受众过滤。
  - 不同受众题库混选时阻止提交并提示；不再静默继承第一个题库。
  - 验收：新建候选/员工题库各一条；混选不可提交。

- [x] **T3.3 题库导入 Dialog**（L）
  - 三步：选文件（txt/md/csv/docx/pdf/xlsx，≤10MB）→ 草稿预览 → 确认导入。
  - 草稿表格可展开编辑题干/选项/答案/分值/知识点/难度；`needs_review` 高亮。
  - warnings 逐条展示；`source=rule` 明确「AI 未参与」；`parsed_count=0` 禁用确认。
  - confirm 后展示 created/skipped/failed，刷新题库与题目。
  - 验收：txt/docx/xlsx 可走通；重复确认 skipped；警告不隐藏。

- [x] **T3.4 测评任务面板**（L）
  - P07 页头下新增 Panel；状态筛选（全部/pending/submitted/cancelled）+ 试卷筛选。
  - 列：候选人（开详情）、试卷+受众、状态、deadline、结果、操作。
  - 验收：当前 `assignment 32 cancelled` 可见；状态/试卷筛选真实生效。

- [x] **T3.5 绑定测评 Dialog**（L）
  - 选 published 试卷；多选当前简历（最多 200）；deadline + note；批量 `parsed_resume_ids`。
  - 结果展示 created/existed/failed；失败逐条；成功后刷新任务与简历列表。
  - 验收：批量绑定 3 人 → 3 条 pending；重复绑定返回 existed 不报错。

- [x] **T3.6 取消绑定**（S）
  - 仅 pending 可取消；二次确认 `DELETE /exam-assignments/{id}`；409 展示「已提交不能取消」。
  - 验收：pending → cancelled；submitted 取消 409。

- [x] **T3.7 答题 assignment 上下文**（M）
  - 从任务行跳 `/exams/{exam}/take?assignment_id=&candidate=`。
  - 有 assignment：顶部绑定提示、姓名只读、提交带 `assignment_id`、草稿 key 加 assignment id。
  - 无 assignment：保留「练习/不回写」提示。
  - 提交成功/失败刷新简历、任务、答卷。
  - 验收：提交后简历从「待测评」变「已测评」；409 正确提示。

- [x] **T3.8 成绩页适配**（S）
  - `Submission` 加 `parsed_resume_id`/`audience`；候选人可点进详情；显示受众。
  - 验收：新提交成绩页能打开简历详情；历史 null 不报错。

- [x] **T3.9 简历测评摘要联动**（S）
  - P02 列表/详情使用新的 `exam_summary`，与 T3.7 提交后刷新联动。
  - 验收：提交后列表徽标变为「已测评」，详情分数正确。

---

## P4 员工端

- [x] **T4.1 员工/HR 分流**（M）（P0 已提前落地基础分流，待 P4 联调）
  - 抽出 `HrTrainingPage`，新增 `MyTrainingView`；`/training` 按 employee 角色分支。
  - 员工分支不请求 `/talent-profiles`、`/job-profiles`、`/training-courses`、`/prejob-plans` 等 HR 接口。
  - 验收：员工登录只发 3 条 `/my/training/*` 请求；HR 仍四标签。

- [x] **T4.2 员工概览 + 计划**（M）
  - `summary` 五指标；计划卡片含任务；`onboarded=false` 空态「还没有培养计划，请联系 HR」。
  - 验收：`emp_chen` 未转正显示空态；转正账号显示计划与任务。

- [x] **T4.3 员工任务操作**（M）
  - 记录进度（分钟/百分比）、完成；后端 400 原样提示；成功后刷新 summary/plans/ledger。
  - 不提供候选人下拉、诊断、课程管理、考核选择。
  - 验收：员工能推进自己的任务；操作别人的任务 403；完成后进度正确。

- [x] **T4.4 员工成长台账**（S）
  - 台账表（时间/维度/变化/delta/source/note）；空态；没有分页接口时按后端返回全量。
  - 验收：真实台账行显示；无数据不报错。

- [x] **T4.5 转正账号登录端到端**（M）
  - 用 T1.7 生成的手机号 + 一次性密码登录；落 `/training`；菜单只有培训。
  - 验收：登录成功、菜单正确、直接访问 HR 页 403。

- [x] **T4.6 员工路由/菜单回归**（S）
  - AppShell 菜单仅培训；直接 URL 拦截；退出后登录页正常。
  - 验收：无空白页、无死循环、无 403 闪烁。

---

## P5 回归与交付

- [x] **T5.1 HR 主链路回归**（M）
  - P01/P02/P03/P04/P05/P06/P07/P08/P09/P10/P14/P15/P16 原有功能不回归。
  - 验收：列表、筛选、详情、匹配、画像、系统管理至少各走一遍真实接口。

- [x] **T5.2 六项后端场景 UI 验收**（L）
  - 向量 brief、身份、查重点击、受众/绑定/已测评、转正/员工培训、题库导入。
  - 验收：按方案 §6 的表格逐项勾选，记录真实返回。

- [x] **T5.3 五态检查**（M）
  - 每个改动页：loading / empty / error / 403 / over-limit 或 409。
  - 验收：错误文案来自后端；无空白页、无控制台报错。

- [x] **T5.4 响应式检查**（M）
  - 1910 / 1440 / 768 / 390；弹窗、表格、雷达、导入草稿编辑均不横向溢出。
  - 验收：`scrollWidth == clientWidth`，关键点击区 ≥24px，正文对比度达标。

- [x] **T5.5 键盘与焦点**（M）
  - 全局详情弹窗、一次性密码、导入对话框、绑定对话框：Esc 关闭、焦点陷阱、焦点归还。
  - 验收：Tab 可走完；关闭后回到触发按钮。

- [x] **T5.6 门禁与交付**（M）
  - `tsc`、`vite build`、`lint_hardcodes`、`check_no_emoji`、taste lint、令牌校验。
  - 更新 `deliveries/` 对应说明与截图；记录真实接口读数。

---

## 依赖关系

```
T0.1/T0.2 ─┬─> T4.*（员工端）
T0.3 ──────┼─> T1.* / T2.* / T3.*
T0.4 ──────┼─> T2.* / T3.*
T0.5 ──────┴─> T1.4 / T2.2 / T2.3 / T3.8
T1.1/T1.2 ───> T3.9
T3.5 ────────> T3.7 ─> T3.9
T1.7 ────────> T4.5
```

## 不做的项

- [ ] 不自动合并疑似重复（只提示）。
- [ ] 不做扫描件 PDF OCR。
- [ ] 不做员工自助答题。
- [ ] 不做旧简历物理删除。
- [ ] 不新增后端不存在的部门/绑定查询接口。
- [ ] 不改 `mvp/frontend`、`mvp/backend`。

---

## 当前已知阻塞

1. `landingPath` 缺少 `/training` → 员工登录 403（T0.1）。
2. 前端路由没有菜单级守卫 → 员工可直达 HR 页面（T0.2）。
3. 简历详情仍由 P02 私有 state 控制 → 跨页 brief 无法复用（T0.5）。
