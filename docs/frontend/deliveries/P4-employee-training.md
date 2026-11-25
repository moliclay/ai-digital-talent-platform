# P4 员工培训端 · 交付

日期：2026-11-04
范围：员工登录落地、我的培训概览/计划/任务/台账、任务推进、路由与菜单；**P5 未开工**。

---

## 1. 员工与 HR 分流

`/training` 同一路由按角色分支：

- HR / admin：原四标签「课程 / 缺口诊断 / 培养计划 / 成长台账」，继续使用 `prejob-plans` 等 HR 接口。
- 员工：`MyTrainingView`，只调用：
  - `GET /my/training/summary`
  - `GET /my/training/plans`
  - `GET /my/training/ledger`

实测员工登录后资源请求：

```
/api/auth/login
/api/auth/me
/api/my/training/summary
/api/my/training/plans
/api/my/training/ledger
```

除认证外只有 3 条培训请求，没有 `talent-profiles`、`job-profiles`、`training-courses`、`prejob-plans`。

---

## 2. 概览与计划

- 五张指标卡：培养计划、学习任务、已完成、待完成、台账记录。
- 总进度条：按已完成任务数 / 总任务数。
- 计划卡：计划名称、岗位、周数、任务完成数、进度、培养目标、任务列表。
- `onboarded=false`：显示「还没有培养计划 / 请联系 HR 为你生成培养计划」。

实测未转正账号 `emp_chen`：

```
/training
h1=我的培训
还没有培养计划
请联系 HR 为你生成培养计划。
```

---

## 3. 任务推进

员工可对本人任务：

- 记录进度：分钟 + 百分比；前端把进度限制在 0–100。
- 完成学习：需 `progress >= 100` 且 `study_minutes >= required_minutes`。
- 完成后刷新 summary / plans / ledger。
- 后端 400 原样展示；失败不清空弹窗输入。

实测王峰任务 39：

```
记录前：60 / 600 分钟，50%
提交：600 分钟，100%
完成后：660 / 600 分钟，100%，任务状态 done
summary：已完成 1 / 3，总进度 33%
```

归属校验实测：用王峰账号操作程磊计划的任务 31/32/33，均返回：

```
HTTP 403 {"code":403,"message":"无权操作该任务"}
```

---

## 4. 成长台账

台账列：时间 / 维度 / 变化 / 增幅 / 来源 / 说明。

- `source` 映射：`prejob_assessment` → 岗前考核。
- 空态：还没有成长记录 + 完成培养计划后留下能力变化。
- 无分页接口，按后端返回全量渲染。

真实记录（王峰，由 HR 用测评提交 12 对任务 40 考核通过后写入）：

```
时间：今天 16:03
维度：业务理解
变化：48 → 59
增幅：+11
来源：岗前考核
说明：业务理解考核通过，48→59
```

---

## 5. 转正账号端到端

测试账号（演示环境）：

```
账号：13900000002
密码：Test1234
姓名：王峰
```

- 登录成功，落地 `/training`。
- 左侧菜单只有「培训成长」一项。
- `/auth/me` 菜单中仅 `/training` 为 `allowed=true`。
- 直接访问 `/resumes` → `/403`，页面 h1「权限不足」。
- 退出后回登录页，未出现空白页或 403 闪烁。

---

## 6. HR 回归

`hr_zhao /training` 仍显示四标签、5 门课程、课程表格与操作，未受员工分支影响。

---

## 7. 门禁

```
tsc 0
lint_hardcodes 0 处（134 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
build JS 172.00 kB gzip / CSS 22.19 kB gzip
```

---

## 8. 数据变更

本轮端到端测试新增/修改了演示数据：

- `resumes/7` 王峰转正，`employee_user_id=20`，账号 `13900000002`。
- 任务 39：`study_minutes=660`，`progress=100`，`status=done`。
- 任务 40：由测评提交 12 考核通过，`status=done`；写入成长台账 1 条（业务理解 48→59，来源 `prejob_assessment`）。
- 测评任务 40、提交 12：王峰 / 算法工程师内测，90 分通过。

---

## 9. 已知

1. 任务 40 是「考核通过」而非学习完成：后端返回 `status=done`，但 `study_minutes=0`、`progress=0`，页面按真实字段显示「0/120 分钟，0%」，与「已完成」状态并存。这是 G33 数据不自洽，前端没有伪造学习时长。
2. 任务 39 记录 600 分钟后累计 660/600 分钟，超过要求学时；页面按真实累计值显示。
3. 员工分支未做移动端系统适配（用户已明确暂缓）。
4. 测试账号 `Test1234` 仅用于本地演示，不写入任何生产配置。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/p4-employee-training.png` | 员工初始培训页（0/3） |
| `shots/p4-employee-progress.png` | 记录进度并完成 1 个任务 |
| `shots/p4-employee-ledger.png` | 2/3 完成 + 真实成长台账 |
| `shots/p4-employee-empty.png` | emp_chen 未转正空态 |
| `shots/p4-employee-403.png` | 员工直达 HR 路由被拦截 |
| `shots/p4-employee-logout.png` | 员工退出后回到登录页 |
| `shots/p4-hr-training.png` | HR 四标签回归 |
