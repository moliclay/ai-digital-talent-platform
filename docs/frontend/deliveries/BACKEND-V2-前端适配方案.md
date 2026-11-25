# 后端优化项 · 前端适配方案

日期：2026-11-04
状态：**方案（未开工）**
范围：只改 `mvp/frontend-v2`，不改后端、不改旧前端。

---

## 0. 结论

六项后端优化需要前端适配 **8 个页面 + 3 个全局能力**：

| 类型 | 内容 |
|---|---|
| 页面 | P02 简历筛选、P15 语义检索、P07 智能测评、P08 在线答题、P09 成绩报告、P16 培训成长、P00 登录、AppShell / 路由 |
| 全局 | `landingPath` 角色落地、路由权限保护、全局简历详情弹窗 |
| 共用组件 | `ResumeBrief`、`AudienceFilter`、`QuestionImportDialog`、`AssignmentDialog`、`MyTrainingView` |

### 两个必须先修的阻塞项

1. **员工登录会落到 403**：`src/lib/api.ts` 的 `LANDING_ORDER` 没有 `/training`。员工 `emp_chen` 的菜单只有培训成长，当前 `landingPath()` 找不到匹配项，返回 `/403`。必须先改成“菜单里第一个 allowed 的 path”，或至少把 `/training` 加进顺序。
2. **员工能直接访问 HR 路由**：`app.tsx` 只有登录保护，没有路由级权限保护。员工直接输入 `/resumes`、`/exams` 仍会挂载 HR 页面。需要根据 `/auth/me` 的 `menus.allowed` 加路由守卫，员工只允许 `/training`。

### 一个架构决定

**简历详情不再由 P02 页面私有 state 控制，改为 AppShell 级全局弹窗，URL 参数 `?resume=<parsed_resume_id>`。**

原因：查重、语义检索、岗位召回都要能点进简历详情；如果复用 P02 的本地 `detailId`，跨页面点击必须跳转并丢失筛选上下文。全局 Host 可以：

- 在任意页面点击候选人 → `setSearchParams({ resume: id })`；
- 当前页上方打开同一个 880px 居中详情弹窗；
- 关闭后回到原页面、原筛选、原滚动位置；
- 直接访问 `?resume=6` 也能打开，便于验收和排障。

---

## 1. 后端能力 → 前端页面矩阵

| 后端优化 | 前端落点 | 关键改动 |
|---|---|---|
| ① 向量写入完整 brief | P15 | 统一 `ResumeBrief` 组件；检索/查重/召回都展示学历、专业、技能、文件 |
| ② 同一人取最新 | P02 | `include_superseded` 开关、旧版标记、详情版本时间轴 |
| ② 疑似重复 | P02 | 顶部提示条 + 疑似组弹窗；只报不合并 |
| ③ 查重/召回可点详情 | P15 + 全局 Host | brief 名称可点，`accessible=false` 置灰 |
| ④ 题库受众 + 绑定 + 已测评 | P07 / P08 / P09 / P02 | 受众筛选、测评任务、绑定对话框、答题携带 `assignment_id`、列表徽标 |
| ⑤ 转正建号 + 员工只有培训 | P02 / P00 / P16 | 转正按钮、一次性密码弹窗、员工自助培训、落地页与路由守卫 |
| ⑥ 题库文件导入 + AI | P07 | 上传 → 草稿可编辑 → warnings → 确认落库 |
| 向量索引过期 | P15 | `stale`/`expected_count` 状态、`reindex-if-stale` 修复按钮 |

---

## 2. 全局改造

### 2.1 角色落地与路由守卫

**现状**

```ts
// src/lib/api.ts
const LANDING_ORDER = ["/dashboard", "/matching", "/job-profiles", "/talent-profiles", "/exams", "/resumes", "/system"];
```

员工只有 `/training`，因此落到 `/403`。

**方案**

- `landingPath(me)` 改为：先按业务优先级找 allowed 的 path，找不到就取 `me.menus.find(m => m.allowed)?.path`，最后才 `/403`。
- 增加 `RequireMenu` 路由守卫：根据当前 URL 对应的一级菜单判断 `allowed`；不通过跳 `/403`。
  - `/exams/:id/take`、`/exams/result/:id` 归 `/exams`；
  - `/matching/:id` 归 `/matching`；
  - `/403`、`/soon` 不做守卫。
- 员工登录 → `/training`；HR → `/dashboard`；admin 仍按现顺序。

### 2.2 AppShell 全局简历详情 Host

新增 `src/components/resume-detail-host.tsx`，挂在 `AppShell` 的 `<Outlet />` 同级：

```tsx
const [params, setParams] = useSearchParams();
const resumeId = Number(params.get("resume")) || null;
<ResumeDetailModal
  open={resumeId !== null}
  resumeId={resumeId}
  onClose={() => {
    const next = new URLSearchParams(params);
    next.delete("resume");
    setParams(next, { replace: true });
  }}
/>
```

- P02 表格点击姓名不再 `setDetailId`，改为写 `?resume=id`。
- P15 三个 tab 的 brief 点击统一写 `?resume=id`。
- 详情弹窗的 `onSaved` 通过 `queryClient.invalidateQueries({ queryKey: ["resumes"] })` 刷新列表。
- 旧版简历行点击时写 `?resume=<superseded_by>`，打开现行版本；详情里仍能看到版本时间轴。
- 可选：增加 `/resumes/:id` 别名路由，重定向到 `/resumes?resume=id`，满足后端文档里的链接习惯。

### 2.3 共享类型

新增 `src/lib/api-types.ts`（或 `src/lib/backend-types.ts`）：

```ts
export type ResumeBrief = {
  parsed_resume_id: number;
  resume_file_id: number;
  name: string;
  education: string;
  major: string;
  years_experience: number;
  skills_top: string[];
  skills_count: number;
  filename: string;
  created_at: string;
  accessible: boolean;
};

export type ExamSummaryItem = {
  exam_id: number;
  exam_name: string;
  audience: "candidate" | "employee";
  state: "assigned" | "submitted";
  assignment_id: number | null;
  submission_id: number | null;
  score: number | null;
  max_score: number | null;
  pass_score: number | null;
  passed: boolean | null;
  deadline: string | null;
  submitted_at: string | null;
};

export type ExamSummary = {
  state: "none" | "assigned" | "submitted";
  label: string;
  total: number;
  passed: number;
  items: ExamSummaryItem[];
};

export type ResumeIdentity = {
  key: string;
  is_current: boolean;
  superseded_by: number | null;
  siblings: Array<{
    parsed_resume_id: number;
    name: string;
    is_current: boolean;
    created_at: string;
    filename: string;
  }>;
};
```

其他类型：

- `ResumeRow` 增加 `is_current`、`superseded_by`、`identity_key`、`employee_user_id`、`exam_summary`。
- `ResumeDetail` 增加 `exam_summary`、`identity`、`employee_user_id`、`onboarded_at`。
- `Bank`、`Exam` 增加 `audience: "candidate" | "employee"`。
- `Submission` 增加 `parsed_resume_id: number | null`、`audience`。
- `VectorStatus.milvus` 增加 `expected_count`、`stale`。
- 新增 `ExamAssignment`、`QuestionDraft`、`ImportResult`、`MyTrainingSummary`、`MyTrainingPlan`、`MyTrainingLedger`。

### 2.4 共用展示组件

| 组件 | 用途 |
|---|---|
| `ResumeBriefCell` | 名称（可点/置灰）、学历、专业、年限、`skills_top` chips + `+N`、文件名 |
| `ExamStateBadge` | `none` 灰「未测评」；`assigned` 蓝「待测评」；`submitted` 绿「已测评」 |
| `AudienceFilter` | 全部 / 候选人 / 员工，题库与试卷共用 |
| `CopyableSecret` | 转正一次性密码：只读输入 + 复制按钮 + 提示 |
| `TaskProgressDialog` | 员工记录学习分钟/进度 |

---

## 3. 页面级方案

### 3.1 P02 简历智能筛选

#### 列表

- 请求默认不传 `include_superseded`，由后端只返回现行简历。
- 工具栏新增开关「显示历史版本」：
  - 开启：`?include_superseded=1`，查询 key 加 `history`；
  - 关闭：回现行；切换时 `page=1`。
- 姓名单元格：
  - 姓名左侧保留头像/姓名；
  - `employee_user_id` 非空 → 「已转正」小徽标；
  - `is_current=false` → 整行低饱和 + 「已被新版本替代」徽标；姓名点击打开 `superseded_by` 现行版本。
- 新增「测评」列：
  - `exam_summary.label` 出 `ExamStateBadge`；
  - hover/`title` 展示各试卷名称、分数/合格线；
  - 详情弹窗里有完整列表，列表只做轻量状态。
- 顶部「疑似重复」提示：
  - 调 `GET /resumes/identity/suspected`；
  - `total > 0` 时显示警告条：「发现 N 组疑似重复，建议人工核对」+「查看」；
  - 弹窗按组展示姓名、学历、专业、ids；每组可点进详情；
  - **不提供自动合并按钮**；如需维护，单独放「重新计算身份」二次确认，调 `POST /resumes/identity/reconcile`，只做重算，不删数据。
- 表格列在 1440/768 下的隐藏规则要重排：保留姓名、学历、年限、技能、测评、状态；专业/文件/时间在窄屏隐藏，确保测评列可见。

#### 详情弹窗（沿用现有 880px 居中弹窗）

建议改为左右两栏，宽度不变：

```
┌ 标题 / 来源文件 / 状态 / 下载原文 ─────────────┐
│ 主栏（约 1.4fr）           │ 侧栏（约 0.8fr）      │
│ 基本信息                   │ 身份与版本            │
│ 技能                       │ 测评状态              │
│ 优势                       │ 转为正式员工          │
│ 解析记录                   │                       │
│ 简历原文                   │                       │
└ 关闭 / 修正档案 ──────────────────────────────┘
```

- 侧栏「身份与版本」：
  - `identity.key`、`is_current`；
  - `siblings` 时间轴：现行高亮，旧版灰；点旧版可切换查看，但旧版**禁用编辑**；
  - 旧版顶部提示「已被新版本替代」+「查看现行版本」按钮。
- 侧栏「测评状态」：
  - `exam_summary.items` 每行：试卷名、受众徽标、状态、分数/合格线、截止时间；
  - submitted 且有 `submission_id` → 链接 `/exams/result/{sid}`；
  - 没有绑定 → 空态「还没有绑定测评」+「去测评页」。
- 侧栏「转为正式员工」：
  - 仅 `canEdit && !employee_user_id && phone` 可点；
  - 无手机号 → 按钮禁用 + 一行「请先补全 11 位手机号」；
  - 点击二次确认，默认部门沿用后端，不选部门（避免新增部门接口）；
  - 成功后打开**一次性密码弹窗**：账号（手机号）、初始密码、复制按钮、醒目提示「只显示这一次」；
  - 关闭后清空密码 state，不写 localStorage；
  - 400/409 原样显示后端 message；409 时刷新详情。
- 编辑态：暂时收起侧栏，保留现有两列表单；保存后刷新详情。

### 3.2 P15 语义检索

- 三个 tab 的返回类型统一改成 `ResumeBrief`。
- `ResumeBriefCell`：
  - 名称可点 → `?resume=<id>`；
  - `accessible=false` → 文字灰、不可点、`title="无权查看该简历"`；
  - 技能显示 `skills_top` chips；`skills_count > 5` 显示 `+N`；
  - 文件名可作为副标题，不再显示「暂无」。
- 语义检索表：姓名、学历、专业、年限、技能、相似度；1440 下保留专业，768 隐藏专业/年限。
- 查重：A/B 两列都用 `ResumeBriefCell`，中间相似度；两侧均可点；`accessible` 独立判断。
- 岗位召回：同样用 `ResumeBriefCell`，显示 `similarity`。
- 索引状态卡：
  - 显示 `resume_count / expected_count`；
  - `stale=true` 时黄色提示「索引已过期，建议修复」；
  - 新增按钮「修复过期索引」→ `POST /vector/reindex-if-stale`；
  - 原「重建索引」保留为「全量重建」，两者文案明确区分；
  - 修复返回 `{rebuilt, count, expected}`，`rebuilt=false` 时提示「索引本来是最新的」。
- 所有 brief 点击都走全局 Host，不需要跳页。

### 3.3 P07 智能测评

#### 受众

- 题库列表与试卷列表加共享 `AudienceFilter`：全部 / 候选人 / 员工。
- `GET /question-banks?audience=`、`GET /exams?audience=` 传参。
- 题库卡片/表格显示受众徽标；创建题库增加受众选择。
- 创建试卷：
  - 增加受众选择；
  - 题库列表按已选受众过滤；
  - 若选了不同受众的题库，阻止提交并提示；不静默继承第一个题库。

#### 新增「测评任务」区块

在页头下方、题库之前新增一个 `Panel`（不把页面拆成新路由）：

- 标题「测评任务」，右侧「绑定测评」主按钮。
- 筛选：状态（全部/待测/已提交/已取消）、试卷（可选）。
- 表格：
  - 候选人（点击打开简历详情）
  - 试卷 + 受众
  - 状态（pending/submitted/cancelled）
  - 截止时间
  - 结果（score/max，passed）
  - 操作：待测 →「开始答题」「取消」；已提交 →「查看成绩」；已取消 → 无操作。
- 「绑定测评」对话框：
  - 选择试卷（只列 published）；
  - 候选人复选列表（`/resumes?page_size=200`，当前简历），支持按姓名过滤；
  - 可选 deadline（`datetime-local`）和 note；
  - 提交 `parsed_resume_ids` 批量；
  - 结果展示 `created_count / existed_count / failed_count`，失败逐条原因；
  - 绑定成功后刷新测评任务与简历列表。
- 取消：二次确认调 `DELETE /exam-assignments/{id}`；409 显示「已提交不能取消」。

#### 题库导入

- 题库区块增加「导入题库」按钮（`exam:create`）。
- `QuestionImportDialog` 三步：
  1. 选择文件（`txt/md/csv/docx/pdf/xlsx`，≤10MB），显示格式提示；
  2. 上传 `POST /question-banks/{id}/import`，展示 `source` 徽标、`parsed_count`、`warnings`；
  3. 草稿预览：表格列（题型、题干摘要、答案、分值、状态），点击行展开编辑题干/选项/答案/分值/知识点/难度；
  - `needs_review=true` 行黄色高亮；
  - `source=rule` 显示「AI 未参与，已用规则解析」；
  - 确认 `POST .../import/confirm`，提交修改后的 `questions`；
  - 结果 `created/skipped/failed` 展示；重复确认同题干会 skipped，不重复插入；
  - 0 题时禁用确认，展示 warnings 建议。
- 成功后刷新题库列表与当前题库题目。

### 3.4 P08 在线答题

- 路由支持 `?assignment_id=...&candidate=...`。
- 从「测评任务」点「开始答题」时带上参数：
  ```
  /exams/9/take?assignment_id=32&candidate=程磊
  ```
- 有 `assignment_id`：
  - 顶部显示绑定上下文「测评任务 · 程磊 · 试卷名」；
  - 候选人姓名只读（不再允许改错人）；
  - 提交 body 带 `assignment_id`；
  - 提交成功/失败刷新 `resumes`、`exam-assignments`、`exam-submissions`；
  - 草稿 key 加 assignment 维度：`tl.exam.{id}.{assignment_id}`，避免不同绑定共用答案。
- 没有 `assignment_id`：
  - 保留现有「练习/未绑定」提示：本次成绩不会回写候选人测评状态；
  - 仍允许提交，兼容旧入口。
- 409：显示「这份测评已提交/已取消」，不重试；若已有 submission 给结果链接。

### 3.5 P09 成绩报告

- `Submission` 类型补 `parsed_resume_id`、`audience`。
- 成绩页抬头显示受众徽标；有 `parsed_resume_id` 时候选人姓名可点开简历详情。
- 从测评任务「查看成绩」进入时，返回路径保留；无 `parsed_resume_id` 的历史答卷继续显示姓名纯文本。

### 3.6 P16 培训成长（员工端）

`TrainingPage` 拆成两个视图，按角色分支，**员工不加载 HR 的课程/诊断/计划列表请求**：

- HR/admin：保持现有四标签页面。
- employee：
  - 新 `src/pages/training/my-training.tsx`，路由仍是 `/training`（与后端菜单一致）；
  - 数据只来自：
    - `GET /my/training/summary`
    - `GET /my/training/plans`
    - `GET /my/training/ledger`
  - 页面结构：
    - 概览：计划数、任务数、已完成、待办、进度百分比；
    - 「我的计划」：计划卡片 + 任务列表；任务显示维度、要求学时、已学、进度条、状态；
    - 任务操作：记录进度（分钟 + 百分比）、完成（后端校验 100% 与学时；失败内联展示后端 message）；
    - 「成长台账」：before/after/delta/source/note；
  - `onboarded=false`：不显示空表格，直接空态「你还没有培养计划，请联系 HR」；
  - 不显示候选人下拉、不显示诊断、不显示课程管理、不显示考核选择；
  - 员工无 `exam:view`，不提供测评/答卷入口，考核由 HR 侧完成。
- 员工菜单和落地页由 §2.1 统一处理。

### 3.7 P00 登录

- 登录页不新增表单字段；员工用手机号 + 初始密码直接登录。
- 登录成功按 `landingPath` 跳转：员工 `/training`，HR `/dashboard`。
- 登录页演示账号提示保留；新员工账号不在演示列表中出现。
- 登录失败 401/403 逻辑不变。

---

## 4. 交互与错误态约定

| 场景 | 处理 |
|---|---|
| `accessible=false` brief | 置灰、不可点、`title` 说明无权；不伪造详情 |
| 已提交/已取消绑定再次提交 | 409，显示后端 message，不重试 |
| 重复转正 | 409，显示已有账号；刷新详情 |
| 手机号缺失/不足 11 位 | 转正按钮禁用 + 补手机号提示；后端 400 也原样显示 |
| 导入空文件/格式不支持 | 400/413 message 内联在 import dialog |
| 导入 `parsed_count=0` | 确认按钮禁用，展示 warnings |
| 导入 `source=rule` | 明确提示「AI 未参与」，不伪装 AI |
| 向量不可用 | 保留现有不可用状态，修复/重建按钮禁用 |
| 员工访问 HR 路由 | 路由守卫 → `/403`，不请求业务接口 |
| 员工无计划 | `onboarded=false` 空态，不报 404 |
| 旧版本简历 | 列表置灰、详情只读、可跳现行版本 |
| 疑似重复 | 只提示、只查看，不自动合并 |

---

## 5. 实施顺序

### P0 基础（先做，阻塞后续）

1. `landingPath` 支持 `/training` + 路由守卫。
2. 共享 types / `ResumeBrief` / `ExamStateBadge`。
3. 全局 `ResumeDetailHost` + `?resume=`。

### P1 简历域

4. 列表：现行/历史、测评列、转正徽标。
5. 疑似重复提示与组弹窗。
6. 详情：两栏、身份时间轴、测评状态、转正 + 一次性密码。

### P2 语义域

7. P15 brief 三处统一。
8. 向量 stale / expected_count / 修复按钮。

### P3 测评域

9. 受众筛选 + 创建/出卷受众。
10. 题库导入。
11. 测评任务 + 绑定/取消。
12. P08 assignment 上下文与提交回填。
13. P09 受众/候选人链接 + P02 测评摘要复用。

### P4 员工端

14. `MyTrainingView` 概览/计划/台账。
15. 记录进度/完成 + 错误态。
16. 转正账号登录 → 落地 `/training` 端到端。

### P5 回归

17. HR 全页面回归 + 员工全链路 + 六项后端验收脚本对应的 UI 场景。
18. 1910/1440/768/390、五态、键盘/对比度、硬编码/token/taste 门禁。

---

## 6. 验收口径（用真实接口）

| 场景 | 期望 |
|---|---|
| 简历列表 | 默认 6 条现行；开启历史版本后出现旧版标记；点旧版进现行 |
| 疑似重复 | 当前库 2 组（陈宇、王峰）；提示条出现，组内可点详情 |
| 简历详情 | 身份 sibling 时间轴；`employee_user_id` 状态正确；测评为空/待测/已测评三态可显示 |
| 转正 | 无手机号 400；重复 409；成功弹出一次性密码；账号=手机号；关闭后无法再取 |
| brief | 语义检索/查重/岗位召回都能显示学历、专业、skills_top、文件名；点击打开详情；无权限灰 |
| 向量 | 状态 `6 / 6`、`stale=false`；模拟过期时修复按钮返回 `rebuilt` 与计数 |
| 测评受众 | 全部/候选人/员工过滤生效；新建题库/试卷受众正确 |
| 绑定 | 批量绑定 3 人 → 3 条 pending；列表简历变「待测评」；提交后变「已测评」 |
| 答题 | 带 assignment_id 提交流转；不带时明确提示不回写；409 正确展示 |
| 导入 | txt/docx/xlsx 草稿可编辑、warnings 可见、needs_review 高亮、重复确认 skipped |
| 员工 | 菜单只有培训；登录落 `/training`；无计划空态；能记录自己的任务；访问 HR 页 403 |
| 兼容 | P01/P03/P04/P05/P06/P10/P14 原功能回归 |

---

## 7. 明确不做 / 边界

- **不做自动合并**疑似重复；不伪造「合并」按钮。
- **不支持扫描件 PDF OCR**；导入时按后端 warning 提示。
- **不做员工自助答题**；员工端只做培训。
- **不做删除旧简历**；旧版只标记、可查。
- **不新增后端没有的接口**；部门选择、删除绑定等不做超出后端能力的扩展。
- **不改旧前端 `mvp/frontend`**。
- 一次性密码不写 localStorage、不写 URL、不写日志。
- `exam_summary` / brief 的字段全部来自后端，不用前端拼假数据。

---

## 8. 需要你拍板的 3 个默认选择

方案里已经按推荐值写，若无异议直接按此开工：

1. **测评任务的位置**：P07 页头下方新增独立 Panel（推荐），不把现有页面拆成新路由。
2. **员工培训视图**：同一 `/training` 路由内按角色分支（推荐），不新增 `/my-training` 路由；与后端菜单一致。
3. **转正初始密码**：只允许系统生成、只在成功弹窗显示一次（推荐）；不做 HR 自定义密码。

---

## 9. 产物

- 本方案：`deliveries/BACKEND-V2-前端适配方案.md`
- 可执行清单：`TODOLIST-后端优化-前端适配.md`
- 当前未改动任何前端业务代码。
