# P5 回归与交付报告

日期：2026-11-04
范围：P0–P4 已完成能力回归、六项后端场景 UI 验收、五态/响应式/键盘/门禁；**不新增业务功能**。

---

## 1. 结论

P0–P4 全部完成：

- 独立前端 `mvp/frontend-v2`，未修改 `mvp/frontend` 与 `mvp/backend`。
- 全站 Corporate Trust 浅色主题，固定 `data-theme="light"`。
- HR 侧：工作台、简历、岗位、匹配、画像、测评、系统管理、预警、语义、培训均回归通过。
- 员工侧：登录、落地 `/training`、我的计划、任务推进、成长台账、403 拦截、退出均通过。
- 全站 1910 / 1440 / 768 / 390 关键页无横向溢出；弹窗 390 无横向溢出。
- 最终门禁全绿。

未做：全站逐页移动端系统适配（用户已明确暂缓）；仅验证关键页 390 不溢出。

---

## 2. HR 主链路回归（1440）

| 页面 | 路由 | 实测结果 |
|---|---|---|
| 工作台 | `/dashboard` | h1 工作台，KPI 与解析队列正常，无溢出 |
| 简历筛选 | `/resumes` | 现行/历史切换正常，疑似重复提示正常 |
| 简历历史 | `/resumes?history=1` | 旧版灰行、已转正/已被替代徽标正常 |
| 岗位条件 | `/job-profiles` | 3 个岗位，硬条件/权重/合格线正常 |
| 岗位匹配 | `/matching` | 扫描 6、通过 2、未通过 4、均分 66.3 |
| 匹配详情 | `/matching/56` | 张伟 95.0 分，条件拆解正常 |
| 人才画像 | `/talent-profiles` | 5 张画像，雷达图与最强维度正常 |
| 智能测评 | `/exams` | 3 张试卷，测评任务/受众/导入入口正常 |
| 在线答题 | `/exams/1/take` | 题目、进度、计时、交卷正常 |
| 成绩报告 | `/exams/result/12` | 王峰 90/100 通过，查看简历入口正常 |
| 空缺预警 | `/vacancy` | 3 条预警，储备池正常 |
| 语义检索 | `/semantic` | 向量 6 / 3 条，`stale=false` |
| 培训成长 | `/training` | HR 四标签、5 门课程正常 |
| 系统管理 | `/system` | admin 可见，6 用户 / 4 角色 / 980 日志 |

所有页面 `scrollWidth == clientWidth`，`tinyTargets` 为空。

### API 回归读数

```text
dashboard:
  files.total=9, parsed_total=9, queue.completed=9
  active_jobs=3
  match: job=4 ai应用开发, passed=2, failed=4, avg=66.3

resumes:
  current=6
  include_superseded=1 → 9
  suspected=2
  duplicates threshold=0.5 → 9 对

job-profiles=3
talent-profiles=5
exams=3
exam-submissions=4
training-courses=5
prejob-plans=5
alerts=3
system users=6, roles=4, logs=980
vector: resume_count=6, job_count=3, expected=6, stale=false
```

---

## 3. 六项后端场景 UI 验收

| 场景 | UI 证据 | 真实返回 |
|---|---|---|
| ① 向量 brief | `p2-semantic-search.png` | 程磊 id 35：本科 / 软件工程 / skills_top 5 项 / `ai应用开发简历.pdf` / `accessible=true` |
| ② 同一人身份 | `p5/resumes-history.png`、`deliveries/P1-resumes.md` | `/resumes/1`：`is_current=false`、`superseded_by=6`、siblings 2 条 |
| ③ 查重可点详情 | `p2-semantic-duplicates.png` | 阈值 0.5 返回 9 对；A/B 两侧 brief 均能点开详情 |
| ④ 受众/绑定/已测评 | `p3-exams-full.png`、`p3-bind-result.png` | 3 条任务：王峰 submitted、李娜 submitted、程磊 cancelled；李娜简历显示已测评 |
| ⑤ 转正/员工培训 | `p4-employee-ledger.png` | 王峰 employee_user_id=20；summary plans=1/tasks=3/done=2/progress=67%/ledger=1 |
| ⑥ 题库文件导入 | `p3-import-draft3.png`、`p3-import-confirm.png` | source=ai、parsed_count=1；确认 created 0 / skipped 1 / failed 0（重复题干） |

补充真实流转：

```text
王峰 assignment 40 → exam 1 → submission 12，90/100 通过
李娜 assignment 38 → exam 20 → submission 11，0/120 未通过
张伟 assignment 39 → cancelled
王峰任务 39：记录 600 分钟 / 100% → 660/600，done
王峰任务 40：用 submission 12 考核通过，台账 48→59
```

409 / 冲突：

```text
重复转正：409 该候选人已转为正式员工，账号 13900000002
取消已提交任务：409 已提交的测评任务不能取消
重复提交已提交 assignment：409 该测评任务已是 submitted 状态，不能重复提交
```

---

## 4. 五态检查

| 状态 | 证据 | 结果 |
|---|---|---|
| loading | `Skeleton` 分支（工作台/简历/画像/测评/培训） | 正常导航未出现空白页；未单独造慢网截图 |
| empty | `p4-employee-empty.png`、`p3-audience-employee.png` | 未转正「还没有培养计划」；员工受众题库/试卷空态 |
| error | `state-error.png` | 阻断 `/api/dashboard/overview` 后显示「工作台没加载出来」+ 重试 |
| 403 | `state-403.png` | pm_wang 访问 `/resumes` → `/403`「权限不足」 |
| 409 | API 实测 | 重复转正 / 取消已提交任务 / 重复提交均返回后端原文 |

正常页截图未出现 `PAGE-EXCEPTION` 或 `NET-FAIL` 日志。

---

## 5. 响应式

### 5.1 页面级

| 宽度 | 检查页 | 结果 |
|---|---|---|
| 1910 | dashboard / talent / exams / training / employee-training | `scrollWidth == clientWidth` |
| 1440 | 全部 HR 页面 + 员工培训 | `scrollWidth == clientWidth` |
| 768 | dashboard / resumes / talent / exams / training | `scrollWidth == clientWidth` |
| 390 | dashboard / resumes / talent / exams / training / semantic / employee-training | `scrollWidth == clientWidth` |

### 5.2 390 弹窗

- 简历详情：`resume-modal-390.png`，无横向溢出。
- 画像详情：`talent-modal-390.png`，无横向溢出。
- 绑定测评：`bind-modal-390.png`；底部「取消 / 确认绑定」固定可见，候选人列表内部滚动。
- 导入题库：`import-modal-390.png`；底部操作区固定，草稿区滚动。

### 5.3 对比度

实测脚本（可见正文/标签）：

```text
员工培训：低于 4.5:1 的可见项 = 0
工作台：低于 4.5:1 的可见项 = 2
  两项均为「处理下一份」禁用按钮（WCAG 对 disabled 控件豁免）
```

本轮调整：

- `semantic.text.secondary` 由 slate500 改为 slate600（#475569）。
- neutral badge 文本改为 `secondary-strong`（#334155）。
- score tick label 改为 `secondary-strong`。
- 登录错误文案改用 `feedback-error-text`（#b91c1c）。

---

## 6. 键盘与焦点

实测脚本：

```text
简历详情：
opened=true, focusInside=true, aria-modal="true",
Esc 后 closed=true, focusReturned=true

绑定测评：
opened=true, focusInside=true,
Esc 后 closed=true, focusReturned=true
```

导入题库使用同一 `Modal` / `useFocusTrap` 原语；Tab 循环、背景 inert、滚动锁由该 hook 统一处理。本轮未做逐项 Tab 顺序录屏。

---

## 7. 门禁

```text
tsc 0
lint_hardcodes 0 处（134 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
validate_tokens 499 tokens OK
build JS 172.01 kB gzip / CSS 22.22 kB gzip
```

`tokens.css` 由 `tokens.json` 生成，当前 319 个变量 / 58 个 dark override；全站固定浅色，dark 仅保留不启用。

---

## 8. 交付与已知

### 已交付

- `deliveries/P0-backend-v2-baseline.md`
- `deliveries/P1-resumes.md`
- `deliveries/P2-semantic.md`
- `deliveries/P3-exams.md`
- `deliveries/P4-employee-training.md`
- `deliveries/P5-regression.md`（本文件）
- 截图目录：`shots/p5/`

### 已知

1. 全站移动端系统适配未做；只验证关键页 390 无横向溢出。
2. 演示库有测试数据：王峰 employee 20、任务 39/40、台账 1 条、assignment 38/39/40、submission 11/12；后端无删除接口，保留可追溯。
3. 任务 40 为「考核通过」而非学习完成，后端返回 `study_minutes=0`、`progress=0`，页面按真实字段显示，属 G33。
4. 演示库简历/疑似重复数量在测试期间有变化，本报告以最后一轮接口读数为准。
5. `loading` 态未单独造慢网截图，代码路径为各页 `Skeleton` 分支。
6. 对比度脚本按最近不透明背景估算；禁用控件不计入正文要求。

### 截图索引

| 文件 | 说明 |
|---|---|
| `shots/p5/dashboard.png` | 工作台回归 |
| `shots/p5/resumes-history.png` | 历史版本回归 |
| `shots/p5/matching.png`、`match-detail.png` | 匹配与详情 |
| `shots/p5/talent.png`、`talent-modal-390.png` | 画像与弹窗 |
| `shots/p5/exams.png`、`bind-modal-390.png`、`import-modal-390.png` | 测评、绑定、导入 |
| `shots/p5/exam-take.png`、`exam-result.png` | 答题与成绩 |
| `shots/p5/vacancy.png`、`semantic.png`、`system.png` | 预警、语义、系统 |
| `shots/p5/training-hr.png`、`employee-training-390.png` | HR 培训、员工培训 |
| `shots/p5/state-error.png`、`state-403.png` | 错误与 403 |
| `shots/p5/focus-esc.png`、`focus-bind.png` | 焦点与 Esc |
| `shots/p5/contrast3.png`、`contrast-employee4.png` | 对比度脚本 |
