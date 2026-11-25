# GLASS-P03 · 岗位条件

本轮把 `/job-profiles` 接到玻璃壳层：页头、岗位列表和权重条统一到 L1/L2，新建/编辑、试算、删除确认统一到 L3。岗位 CRUD、搜索、分页和权限分支未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/job-profiles` |
| `src/pages/job-profiles.tsx` | 页头包 `pageHead`；岗位列表 Panel 加 `glassTable` |
| `src/pages/job-profiles.module.css` | 页头 L2、表格 L1、权重条、动效和移动端样式 |
| `src/styles/glass-app.css` | 二级按钮改用 `--glass-control-bg` / `--glass-control-hover`，深色玻璃上不再像禁用 |
| `tokens.json` / `src/styles/tokens.css` | 新增 `semantic.glass.control-bg`、`control-hover`；令牌总数 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、岗位列表表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影；表格行不单独模糊 |
| L2 | 页头 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 新建/编辑岗位、试算结果、删除确认 | `blur(34px)` + 白 14% + 暗色遮罩；portal 走 `body.glass-route` |

同屏玻璃元素：侧栏 1 + 页头 1 + 表格 1 = **3 个**；打开弹层后 4 个。

## 3. 页面

- 页头：16px/600 标题、12px ink-2 副标题、右侧青色主按钮「新建岗位条件」。
- 搜索：玻璃输入框 + 二级按钮；二级按钮底色从 4% 提到 7%，hover 11%，不再像 disabled。
- 表格：L1 容器、表头 12px ink-2、行高 48px、行 hover 白 4.5%。
- 岗位名：可编辑权限下使用 accent 链接色；无权限时保持正文 ink。
- 权重条：轨道高 4px → 8px，五段权重用同一 accent 的不同透明度区分，仍只保留一个强调色。
- 合格线、创建时间、分页：ink-2 + 等宽数字。

## 4. 浮层

| 浮层 | 结果 |
|---|---|
| 新建/编辑岗位 | 880px L3；双栏字段、硬条件行、权重合计、能力基线全部深色玻璃字段 |
| 试算结果 | 640px L3；扫描/过线/不过/平均分/合格线统计、五档分布、前五名单均深色可读 |
| 删除确认 | 共用 ConfirmDialog，自动 L3；破坏性按钮保持 destructive 语义 |

390 下新建弹窗自动单列，内容区可滚动，底部「取消 / 保存岗位条件」始终可见。

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 岗位列表 | 165ms | 620ms | 18px |

- 只动 `transform` / `opacity`，`animation-fill-mode: backwards`。
- reduced-motion：两处动画全部关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出 |
| 768 × 900 | 768 / 768 | 顶部导航横向化，表格隐藏权重/状态/时间/操作列 |
| 390 × 844 | 390 / 390 | 无页面横向溢出；保留岗位/硬条件/合格线三列 |

搜索回归：输入 `ai` 后显示「筛选结果 3 个」；输入 `AI产品` 显示无匹配空态，清空后恢复 3 个。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-NOV70F8r.css  177.48 kB │ gzip:  27.44 kB
dist/assets/index-Doo3tHmF.js   578.08 kB │ gzip: 173.06 kB
✓ built in 12.43s
```

## 8. 截图

- `shots/glass-jobs-1440.png`
- `shots/glass-jobs-768.png`
- `shots/glass-jobs-390.png`
- `shots/glass-job-editor-1440.png`
- `shots/glass-job-editor-390.png`
- `shots/glass-job-trial-1440.png`
- `shots/glass-jobs-search.png`

## 9. 已知边界

- 目前只有 `/dashboard`、`/resumes`、`/talent-profiles`、`/job-profiles` 挂玻璃壳层；其余页面仍是旧浅色。
- 390 下硬条件列只保留首条并以省略号截断，完整条件在 `title` 中；这是原表格窄屏策略，不是本轮新增问题。
- 权重条五段共用 accent，仅用透明度区分，避免引入第二个彩色系列。
- 本轮未改后端和岗位 CRUD 逻辑。
