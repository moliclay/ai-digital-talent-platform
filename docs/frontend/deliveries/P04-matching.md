# P04 岗位匹配 · 交付说明

路由：`/matching`（支持 `?job=<id>` 直达某岗位）
日期：2026-11-03
页面任务：选一个岗位跑匹配，看清谁过线、谁没过、为什么。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/matching.tsx` / `.module.css` | 岗位选择、运行匹配、统计条、筛选、名单、分页 |
| `src/components/ui/score-bar.tsx` | `label` 改可选，新增 `ariaLabel`；表格里只留数值、条与合格线刻度 |
| `src/components/ui/confirm-dialog.tsx` | 新增 `tone`（默认 primary）；删除确认显式传 `destructive` |
| `src/components/ui/badge.tsx` / `.css` | 结论徽标可带图标，补 `gap` |
| `src/components/ui/select.tsx` | 岗位名过长时加 `title`，悬停可看全称 |
| `src/content/copy.ts` | 新增 `matching.*` |
| `src/app.tsx` / `app-shell.tsx` | 路由 `/matching`，菜单转为已实现 |
| `PAGE-MAP.md` | 新增 G16（summary 不按范围过滤） |

---

## 2. 页面结构

- 标题 + 口径；右上岗位下拉（`/job-profiles?page_size=200`，默认最新一个）+「运行匹配」。
- 统计条五格：扫描 / 通过 / 未通过 / 平均分 / 合格线（合格线取当前岗位配置，不取匹配快照）。
- 统计条下方一行口径说明：统计含本岗位全部结果，名单按数据范围过滤（G16）。
- 名单卡片：分段筛选「全部 / 通过 / 未通过」，计数直接读统计接口；20 条一页。
- 表格七列：姓名 / 学历 / 工作年限 / 技能命中 / 分数 / 结论 / 原因。
- 分数列：数字 + 条 + 合格线刻度；结论列：图标 + 文字，不靠颜色单独表意。
- 原因列单行截断，`title` 给全文；完整原因留给 P05 详情。

无结果时：

- 没有岗位 → 「还没有岗位条件」+「去岗位条件」。
- 岗位没跑过 → 「这个岗位还没跑过匹配」+ 就地「运行匹配」。
- 筛选为空 → 「没有「通过」的记录。切回「全部」看完整名单。」

运行前：

- 已有结果 → 确认框「重新匹配会覆盖上一次结果」，写明岗位名与旧条数；按钮是普通主色，不是危险色。
- 没有结果 → 直接运行。
- 运行中按钮显示「正在匹配 N 份」，并禁用。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次进入 / 切岗位 | 岗位列表 6 行骨架；统计值骨架；名单 8 行骨架（代码路径，首屏 900ms 后已完成，未截到静态图） |
| empty | 新建一个无结果的临时岗位，`?job=5` | 「这个岗位还没跑过匹配」+ 就地运行；统计 0，合格线 60（`shots/matching-empty.png`）；截图后已删除该临时岗位 |
| error | CDP 拦截 `*matching/*` | 「匹配结果没取到。」+「没连上服务，稍后再试。」+ 重试（`shots/matching-error.png`） |
| no-permission | `emp_chen` 直接访问（无 `match:view`） | 「没有查看匹配结果的权限」+「需要「岗位匹配查看」权限。找管理员开通。」（`shots/matching-403.png`） |
| over-limit | 本页没有可触发的数量上限：后端一次重建该岗位全部结果，前端不分批 | 用「覆盖确认」做防护；>500 份没有单独拦截，列入已知缺口 |

补充：

- `?job=` 指向不存在 / 已删除的岗位时，回落到列表第一个岗位，并改写 URL，避免出现“选择框显示 A、统计是 B”的错位。
- 岗位下拉只列 `active` 岗位（后端已过滤 deleted）。

---

## 4. 权限

| 角色 | 能做什么 |
|---|---|
| admin | 看全部、可运行 |
| hr_zhao | 看本部门范围、可运行（`match:create`） |
| pm_wang | 可看、可运行（实测有 `match:create`），范围按部门 |
| emp_chen | 无 `match:view`，403 空态；侧栏没有入口 |

运行按钮只在 `match:create` 时渲染；没有权限的账号看不到按钮，也不会看到禁用按钮。

---

## 5. 真实链路

1. 进入 `/matching`，默认岗位「高级算法工程师(AI平台部)」，统计 6 份（P02 上传的测试简历还没进匹配）。
2. 点「运行匹配」→ 弹覆盖确认（旧 6 条）→「继续匹配」。
3. 返回 `scanned=8 / passed=2 / failed=6 / avg=45.4 / threshold=70`，顶部提示「已完成：扫描 8 份，通过 2 份。」。
4. 统计条变 8 / 2 / 6 / 45.4 / 70；名单 8 行，按分数降序：张伟 85、陈宇 81、张测试 69、刘洋 29、王峰 29、程磊 28、李娜 28、程磊 14。
5. 点「通过 2」→ 名单只剩张伟、陈宇，分页「共 2 条」；统计条仍是全量 8。
6. 空态：临时新建「空岗验证(临时)」→ 统计 0、合格线 60、空态文案正常 → 截图后用 admin 删除，岗位列表回到 2 条。

写入影响：job 3 的匹配结果被重建为 8 条（含 P02 的测试简历），这是运行匹配的预期行为；没有新增岗位（临时岗位已软删）。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `matching.title/sub/listTitle/totalLabel` | 标题、口径、名单标题、共 N 条 |
| `matching.jobLabel/run/running/runningCount` | 岗位选择、运行、进行中文案 |
| `matching.confirm*` | 覆盖确认标题 / 说明 / 按钮 |
| `matching.summary.*` | 扫描 / 通过 / 未通过 / 平均分 / 合格线 / 单位 / 口径说明 |
| `matching.filter.*` | 全部 / 通过 / 未通过 / 分组 aria-label |
| `matching.columns.*` | 七列表头 |
| `matching.years/skillHit/noSkill/pass/fail` | 年限、技能命中、未设技能、结论 |
| `matching.empty*` | 无岗位 / 无结果 / 筛选为空 |
| `matching.loadError*/retry/noPermission*` | 错误态与权限态 |
| `matching.runDone/runFailed/runNoResume` | 运行结果提示 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入页面 | `page` |
| `match_run_start` | 点运行（含确认前） | `page` |
| `match_run_done` | 运行成功 | `page`、`scanned`、`passed` |
| `match_run_failed` | 运行失败 | `page`、`status` |
| `match_filter` | 切换筛选 | `page`、`filter` |

不含候选人姓名、手机、邮箱、简历正文。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 122.40 kB gzip；CSS 10.66 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（84 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟） |
| 1440 | 1075 字，<13px 占 11%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；表格保留姓名 / 分数 / 结论 / 原因，隐藏学历 / 年限 / 技能命中 |
| 键盘 | 岗位下拉支持方向键 / Home / End / Enter / Esc；筛选是原生按钮，`aria-pressed` 跟随状态 |

---

## 9. 已知问题（不阻塞）

1. **G16：summary 不按数据范围过滤，lists 过滤。** 部门范围账号可能看到“扫描 8、名单 6”。已在统计条下明写口径；根治要后端给 summary 加用户范围参数。
2. **口径说明常显**：即使 admin（全部范围）也显示，属于解释性文案，不随权限隐藏。
3. **>500 份没有二次确认**：运行前只按“已有结果”确认一次；数量很大时没有额外提示。
4. **原因列截断**：单行 + `title`；完整原因在 P05 详情，桌面可悬停，键盘/触屏需进详情。
5. **分数条在 sm 尺寸只画合格线刻度，不写“合格线 70”文字**：表格里逐行加标签会噪；统计条已给出合格线。
6. **没有详情跳转**：P05 未做，行不可点；避免跳到不存在的路由。
7. **运行会重建结果**：会改变工作台的匹配统计；这是后端幂等设计的预期行为。
8. **loading 没截到静态图**：首屏 900ms 内完成；骨架代码在 `DataTable` 与统计条上，P02 已实测同款骨架。
9. **临时岗位**：空态验证建过 id 4 / 5，均已软删；列表只剩 2 条 active。
10. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/matching-1440.png` | 1440×900 暗色，8 条结果 |
| `shots/matching-1440-light.png` | 1440×900 浅色 |
| `shots/matching-768.png` | 768×1024，四列 |
| `shots/matching-run.png` | 运行完成提示 + 统计 8/2/6 |
| `shots/matching-confirm.png` | 覆盖确认（旧 6 条） |
| `shots/matching-filter.png` | 只看「通过」2 条 |
| `shots/matching-empty.png` | 无结果岗位（临时岗位，已删） |
| `shots/matching-error.png` | 请求失败 |
| `shots/matching-403.png` | 普通员工无权限 |
