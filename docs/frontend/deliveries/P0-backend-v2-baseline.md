# P0 基础能力 · 交付

日期：2026-11-04
范围：后端 v2 前端适配的 P0；**P1 及之后未开工**。

---

## 1. 已完成

### P0.1 员工落地页

- `LANDING_ORDER` 增加 `/training`；
- `landingPath()` 在业务优先级找不到时，回退到 `me.menus` 第一个 `allowed` 的 path；
- 员工登录实测落到 `/training`，HR 仍落 `/dashboard`。

### P0.2 路由守卫

按权限码增加菜单级保护：

| 路由 | 权限 |
|---|---|
| `/dashboard` | `dashboard:view` |
| `/resumes` | `resume:view` |
| `/job-profiles` | `job:view` |
| `/matching` | `match:view` |
| `/talent-profiles` | `talent:view` |
| `/exams`、`/exams/...` | `exam:view` |
| `/vacancy` | `job:view` |
| `/semantic` | `resume:view` |
| `/training` | `train:view` |
| `/system` | `sys:view` |

`/403`、`/soon`、`/` 放行；员工直达 `/resumes` 实测跳 `/403`。

### P0.3 共享契约

新增 `src/lib/api-types.ts`：

- `ResumeBrief`、`ExamSummary`、`ResumeIdentity`
- `ExamAssignment`
- `QuestionDraft`、`QuestionImportResult`、`QuestionImportConfirmResult`
- `MyTrainingSummary`、`MyTrainingPlan`、`MyTrainingTask`、`MyTrainingLedgerRow`
- `VectorStatus`

### P0.4 共用组件

- `src/components/resume-brief-cell.tsx`：名称可点/无权限置灰、学历/专业/年限、`skills_top` + `+N`、文件名。
- `src/components/exam-state-badge.tsx`：未测评/待测评/已测评三态。
- `src/components/audience-filter.tsx`：全部/候选人/员工 segmented control。
- 均走语义令牌，无硬编码。

### P0.5 全局简历详情 Host

- 新增 `src/components/resume-detail-host.tsx`，挂在 `AppShell`；
- 任意页面 `?resume=<id>` 打开同一个居中详情弹窗；
- 关闭只删除 `resume` 参数，保留当前页面与筛选；
- P02 行点击改为写 query；移除页面私有 `detailId`。

### 额外：员工端基础壳层

由于员工落地 `/training` 后不能继续看到 HR 培训管理页（含课程编辑按钮），**提前落了一个最小员工视图**：

- `TrainingPage` 按角色分流：HR → `HrTrainingPage`，员工 → `MyTrainingView`；
- 员工只请求 `/my/training/summary|plans|ledger`，不加载课程/诊断/岗位接口；
- `onboarded=false` 显示「还没有培养计划，请联系 HR」；
- 完整任务记录/完成与转正账号联调仍属于 P4，本次未做端到端验收。

---

## 2. 实测

| 场景 | 结果 |
|---|---|
| `emp_chen` 登录 | `/training`，h1 `我的培训` |
| `emp_chen` 直达 `/resumes` | `/403`，h1 `权限不足` |
| HR `/resumes?resume=8` | 程磊详情弹窗正常叠在简历页上 |
| HR `/semantic?resume=8` | 语义检索页上正常叠出程磊详情 |
| 390 员工落地 | `scrollWidth 390`，无横向滚动 |

---

## 3. 门禁

```
tsc 0
lint_hardcodes 0 处（130 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
tokens 497 defined
build JS 161.94 kB gzip · CSS 20.05 kB gzip
```

---

## 4. 已知

1. 员工培训页目前只验证了 `onboarded=false` 的空态；转正账号的计划/进度/完成属于 P4。
2. 全局 Host 的 `?resume=` 是前端约定；后端文档里的 `/resumes/{id}` 仍是 API 路径，不冲突。
3. 本轮没有改后端、旧前端或业务流程。

---

## 5. 截图

| 文件 | 说明 |
|---|---|
| `shots/p0-employee-landing.png` | 员工 `/training` 空态 |
| `shots/p0-employee-guard.png` | 员工直达简历页 403 |
| `shots/p0-resume-host.png` | 简历页 `?resume=8` 全局弹窗 |
| `shots/p0-semantic-host.png` | 语义页 `?resume=8` 全局弹窗 |
| `shots/p0-employee-390.png` | 390 员工空态 |
