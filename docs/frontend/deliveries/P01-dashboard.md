# P01 工作台 · 交付说明

路由：`/dashboard`
日期：2026-11-03
方向：A · 值班仪表。整页只回答一个问题：队列里有没有卡住的东西，最近一次匹配是什么结果。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/components/app-shell.tsx` / `.module.css` | 侧栏壳：分组导航、选中强调线、主题切换、账户与退出；未实现菜单落到 `/soon` |
| `src/pages/dashboard.tsx` / `.module.css` | 工作台装配：KPI、解析队列、最近匹配、最近操作 |
| `src/pages/forbidden.tsx` / `.module.css` | `/403` 基础版：账号、角色、回可用首页 |
| `src/pages/soon.tsx` / `.module.css` | `/soon` 占位：菜单指向未实现页面时使用，不造假数据 |
| `src/components/ui/panel.tsx` / `.module.css` | 面板容器：标题、说明、操作、等高层 |
| `src/components/ui/page-header.tsx` / `.module.css` | 页面标题 + 一句话结论 + 操作 |
| `src/components/ui/kpi-strip.tsx` / `.module.css` | 四格指标条，加载态骨架 |
| `src/components/ui/score-bar.tsx` / `.module.css` | 分数条 + 合格线刻度 + 差值判断 |
| `src/components/ui/data-table.tsx` / `.module.css` | 表格原语：加载、空、错误、右对齐数字 |
| `src/components/ui/badge.tsx` / `.module.css` | 状态徽标 |
| `src/components/ui/empty-state.tsx` / `.module.css` | 空态 |
| `src/components/ui/error-state.tsx` / `.module.css` | 错误态 + 重试 |
| `src/components/ui/skeleton.tsx` / `.module.css` | 骨架块 |
| `src/lib/format.ts` | 数字、分数、时间、耗时、头像字 |
| `src/lib/cx.ts` | 类名拼接 |
| `src/lib/analytics.ts` | 埋点，只写 `window.dataLayer` |
| `src/content/copy.ts` | 新增 `shell.*`、`dashboard.*`、`forbidden.*`、`soon.*`、`common.*`、`score.*` |
| `src/app.tsx` | 路由：登录 / 壳 / 工作台 / 403 / soon |
| `scripts/shot.mjs` | 截图与流程冒烟，新增 `--user`、`--after`、`--block`、`--metrics` |

---

## 2. 布局

- 侧栏 232px，两组：工作（工作台、简历、岗位、匹配）、人才（画像、测评）；系统管理只有 admin 可见。
- 主区最大 1180px，页面间距 24px；KPI 四格一条，队列与匹配两栏，最近操作整宽。
- 两个面板用 grid 拉伸保持等高；匹配面板把统计压到底部，队列面板按 5 行状态排布。
- 侧栏选中态：左侧 2px 品牌青竖线 + 图标着色 + 文字转主色，不加背景块。
- 断点 1100px：KPI 变 2×2，双栏变单栏。768 下侧栏仍为 232px。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次进入，`/dashboard/overview` 未返回；KPI 与面板显示骨架 | 本地接口约 100ms，静态截图需要节流 |
| empty | `emp_chen` 登录（self 范围、0 份简历、无 `match:view`） | 副标“当前账号暂无简历数据”，KPI 全 0，队列显示窄空态；匹配与操作两块按权限隐藏（`shots/dash-empty.png`） |
| error | CDP `Network.setBlockedURLs` 拦截 `*dashboard/overview*` 后登录 | 页面显示“工作台没加载出来”+ 中文说明 + 重试（`shots/dash-error.png`） |
| no-permission | `pm_wang` 直接访问 `/dashboard`（`biz` 无 `dashboard:view`） | 返回 403，页面显示“没有「工作台」权限”与缺失权限码（`shots/dash-403.png`） |
| over-limit | 不适用：本页没有输入框，最近操作固定 8 条，租户/配额概念后端未提供 | 交付说明即口径，不伪造触发方式 |

权限缺省：

- 菜单由 `/auth/me` 的 `menus[].allowed` 决定；没有 `dashboard:view` 的账号进不来。
- `resume:create` 不存在时，隐藏“处理下一份”，提示“只有 HR 或管理员能触发解析”，空态提示“简历由 HR 上传”。
- `match:view` 不存在时，隐藏整个匹配面板，队列面板占满宽度，避免露出别人的匹配汇总。
- 最近操作只给 `admin` / `hr`，标题写明“全平台”。

---

## 4. 文案 key

| key | 内容 |
|---|---|
| `dashboard.title` | 工作台 |
| `dashboard.sub.*` | 四句动态结论：有队列/无队列 × 有匹配/无匹配；空态区分有上传权限与无权限 |
| `dashboard.kpi.*` | 简历总数 / 已解析 / 在招岗位 / 队列待处理 |
| `dashboard.kpiNote.*` | 当前账号可见范围 / 已入库的简历 / 全公司在招 / N 份解析失败 / 队列是空的 |
| `dashboard.queueTitle` / `queueMeta(n)` | 解析队列 / 当前账号可见范围 · 共 N 份 |
| `dashboard.status.*` | 待解析 / 解析中 / 待 OCR / 失败 / 已完成 |
| `dashboard.processNext` / `processing` / `parseIdle` / `parseDone(n)` / `parseFailed` | 处理动作与结果 |
| `dashboard.matchTitle` / `matchMeta(name,n)` / `matchAvgLabel` | 最近一次匹配 / 岗位 + 本次 N 人 / 本次匹配平均分 |
| `dashboard.matchBelow(n)` / `matchAbove(n)` / `matchEqual` | 低于 / 高于 / 持平 |
| `dashboard.matchTopTitle` / `matchTopEmpty` | 分数前三 / 暂无可显示的候选 |
| `dashboard.opsTitle` / `opsMeta` / `opsColumns.*` | 最近操作 / 最近 8 条 · 全平台 / 六列表头 |
| `dashboard.opActions.*` / `opAuthLogin` / `opNoAccount` | 动作名映射；认证模块的动作固定为“登录”；空账号显示“未记录账号” |
| `dashboard.loadError` / `loadErrorHint` | 工作台没加载出来 / 没连上服务，稍后再试，或确认后端已启动 |
| `dashboard.noPermissionTitle` / `noPermissionHint` | 没有「工作台」权限 / 缺少 dashboard:view |
| `shell.*` | 跳到主要内容 / 主导航 / 未分配部门 |
| `soon.*` / `forbidden.*` | 未实现页面与 403 的文案 |

---

## 5. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入工作台 | `page: "dashboard"` |
| `queue_process_click` | 点“处理下一份” | `page`、`pending` |
| `queue_process_result` | 解析请求结束 | `page`、`status`（completed / failed / idle / error）、`confidence` |

不含姓名、账号、简历内容、岗位名称。

---

## 6. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 104.06 kB gzip；CSS 7.57 kB gzip |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（51 个文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`100vh`、`padStart`、字体族提示） |
| inspect（登录页） | `--app http://127.0.0.1:5174/login`：0 FAIL，1 WARN（tiny-text） |
| 工作台渲染读数 | 1440×900：469 字，<13px 占 41%，无横向滚动，可点目标无小于 24px |
| 对比度 | 沿用 S2 两套主题全部 required 通过 |
| 权限实测 | `pm_wang` → 403 文案；`emp_chen` → 空态且无匹配/操作块 |

工作台没有跑 `inspect.mjs`：该脚本不支持登录态，直接跑会被重定向到 `/login`，量到的是登录页。工作台的尺寸、字号与溢出改用 `scripts/shot.mjs --flow login --metrics` 在真实登录后测量，读数见上表。

---

## 7. 已知问题（不阻塞）

1. **G12：工作台的 `recent_operations` 与 `match` 统计不按数据范围过滤。** 操作日志标题写“全平台”，且只给 admin/hr；员工不显示。匹配计数（6 人）是全平台，而“分数前三”走 `/matching/lists` 是部门范围，极端情况下两者口径会不一致。已在 PAGE-MAP G12 记录，等后端加过滤后去掉这段说明。
2. **登录事件没有账号。** 后端审计在登录请求上没有 token，`username` 写空；表格显示“未记录账号”，动作按模块显示“登录”，没有编造账号。
3. **最近操作 8 条在 900 高首屏只看到 3 条**，页面高 1229px，需要滚动；没有做表格内分页。
4. **768 下侧栏占 30%（232/768）**，正文 488px，无横向滚动、无破词，但整页高 2174px。
5. **未实现的菜单统一进 `/soon`**，没有做假页面；`/soon` 是占位，不属于本期功能页。
6. **390 移动端未适配**（用户 2026-11-03 决定暂缓），本轮不验收。
7. **error 态用 CDP 拦截接口验证**，没有停后端进程。

---

## 8. 截图

| 文件 | 说明 |
|---|---|
| `shots/dash-1440.png` | 1440×900 暗色，hr_zhao |
| `shots/dash-1440-light.png` | 1440×900 浅色，hr_zhao |
| `shots/dash-768.png` | 768×1024 暗色，hr_zhao |
| `shots/dash-empty.png` | 1440×900 员工空态 |
| `shots/dash-403.png` | 1440×900 无 dashboard:view |
| `shots/dash-error.png` | 1440×900 接口被拦截 |
