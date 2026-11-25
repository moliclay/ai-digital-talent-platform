# P10 系统管理 · 交付说明

路由：`/system`
日期：2026-11-03
页面任务：谁能进系统、谁能干什么、刚才谁动了什么。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/system.tsx` / `.module.css` | 三标签（用户 / 角色 / 操作日志）+ 三张表 + 分页 |
| `src/lib/permission.ts` | **新增** `hasPermission`，兼容 admin 的 `*:action` 通配符 |
| `src/pages/{dashboard,exams,job-profiles,matching,resumes,talent-profiles,system}.tsx` | 全部改用 `hasPermission`，修掉 admin 被误判无权限 |
| `src/content/copy.ts` | 新增 `system.*` |
| `src/app.tsx` / `app-shell.tsx` | 路由 `/system`，菜单转为已实现 |
| `PAGE-MAP.md` | 新增 G29 |

---

## 2. 页面结构

- 标题 + 口径；`tablist`（用户 / 角色 / 操作日志），方向键 / Home / End 切换，`tabIndex` 跟随选中项。
- **用户**：账号 / 姓名 / 部门 / 邮箱 / 状态；20 条/页；状态 active → 「启用」。
- **角色**：角色 / 代码 / 数据范围 / 说明；`all/dept/self` 映射中文；全量（4 条）。
- **操作日志**：时间 / 账号 / 模块 / 动作 / 方法 / 路径 / 结果 / 耗时；20 条/页；只记录写操作。
  - 账号为空 → 「未记录账号」（登录请求没有 Authorization，审计表 username 为空）。
  - 动作：`/auth/login` → 「登录」；其余 create/update/delete/export → 新增/修改/删除/导出。
  - 结果 success → 「成功」，其余 → 「失败」。
  - 时间用 `<time dateTime>`，显示沿用全站「今天 HH:mm」口径。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 切标签首次加载 | 表格骨架（代码路径） |
| empty | 无用户 / 无角色 / 无日志 | 三种空态各自文案（演示库都有数据，代码路径） |
| error | CDP 拦截 `*system/users*` | 「系统数据没取到。」+ 重试（`shots/system-error.png`） |
| no-permission | `hr_zhao`（无 `sys:view`） | 「没有系统管理的权限」（`shots/system-403.png`） |
| over-limit | 用户/日志 20 条/页（后端上限 200） | 日志 629 条 → 32 页（截图底部为「1 / 32」）；分页在表格下方 |

---

## 4. 真实数据

```
用户 4 条：admin / hr_zhao / pm_wang / emp_chen，全部「启用」
角色 4 条：admin(all) / hr(dept) / biz(dept) / employee(self)
操作日志 629 条（截图时刻；每次登录都会增加），最近一条：今天 19:55 认证 登录 POST /api/auth/login 成功 310ms
```

日志观察：

- 登录日志 `username` 为空 → 显示「未记录账号」；动作按 `/auth/login` 映射为「登录」。
- 有一条 `hr_zhao` 的「新增」指向 `POST /api/job-profiles/3/dry-run`——后端把 dry-run 也记成 create，这是审计口径问题，不是前端映射错误。

---

## 5. 权限

| 角色 | 能看 |
|---|---|
| admin | 可看（`sys:view` 由 `*:view` 覆盖） |
| hr / biz / employee | 403 |

**本轮修掉的真问题（G29）**：admin 的权限是 `*:view/*:create/...`，前端此前用 `permissions.includes("sys:view")` 精确匹配，导致 admin 打开系统管理被判无权限。现在统一走 `hasPermission()`，同时匹配 `x:y` 与 `*:y`，与后端 `has_perm` 同口径。这一改动同时修复了 admin 在简历/岗位/匹配/测评等页面看不到「新建/编辑/删除」按钮的问题；已实测 admin 在岗位条件页能看到「新建岗位」。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `system.title/sub/tabs` | 标题、口径、三标签 |
| `system.usersMeta/rolesMeta/logsMeta` | 计数与口径 |
| `system.userColumns/roleColumns/logColumns` | 三张表表头 |
| `system.statusActive/statusDisabled/logSuccess/logFailed/unknownUser` | 状态 |
| `system.actions.*` | 动作映射 |
| `system.scope.*` | 数据范围映射 |
| `system.logsNote` | 只记录写操作 |
| `system.*Empty/loadError*/noPermission*` | 空态与错误 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入系统管理 | `page` |

不含账号、邮箱、日志正文。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 142.30 kB gzip；CSS 14.23 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（109 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟） |
| 1440 用户 | 165 字，<13px 占 15%，无横向滚动，无 <24px 点击目标 |
| 1440 日志 | 1004 字，<13px 占 11%，八列完整，分页 1 / 32 |
| 768 日志 | 无横向滚动；隐藏模块/方法/路径/耗时，保留时间/账号/动作/结果 |

---

## 9. 已知问题（不阻塞）

1. **G29 已修**：`hasPermission` 兼容 `*:action`；后续新页面禁止再用 `permissions.includes` 精确匹配。
2. **审计日志口径**：`dry-run`（POST 但不写库）也被记成「新增」；动作映射只按 method/action，不猜业务语义。
3. **没有搜索/筛选**：后端 users/logs 只有分页，没有 keyword 参数，页面不放假搜索框。
4. **只读**：用户/角色没有增删改接口，页面不提供编辑按钮。
5. **角色没有权限明细**：接口只给 code/name/data_scope/description，不展示逐条权限码。
6. **时间为相对口径**：今天/昨天 + HH:mm，来自全站 `formatDateTime`；审计追溯可接受。
7. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/system-users.png` | 1440×1200 用户标签 |
| `shots/system-roles.png` | 1440×1200 角色标签 |
| `shots/system-logs.png` | 1440×1400 操作日志（含分页） |
| `shots/system-light.png` | 1440×1200 浅色日志 |
| `shots/system-768.png` | 768×1200 日志标签 |
| `shots/system-403.png` | HR 无权限 |
| `shots/system-error.png` | 用户请求失败 |
