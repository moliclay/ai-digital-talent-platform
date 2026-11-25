# GLASS-P02 · 简历智能筛选

本轮把 `/resumes` 接到玻璃壳层，并把简历详情、上传、解析队列三个浮层统一到 L3；筛选、分页、历史版本、重复分组、转正等业务逻辑一行未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/resumes`；用 `useLayoutEffect` 在 `body` 挂 `.glass-route`，让 portal 里的弹层继承玻璃令牌 |
| `src/styles/glass-app.css` | 扩展输入框、开关、dropzone、feedback、dialog、drawer、select 弹层令牌；新增表格容器 L1 和 L3 弹层配方 |
| `src/components/ui/modal.tsx` | 弹层面板加稳定字面类 `glass-dialog`，只影响玻璃路由 |
| `src/components/ui/drawer.tsx` | 抽屉面板加 `glass-drawer`，保留右侧 absolute 定位 |
| `src/pages/resumes.tsx` | 页头包一层 `pageHead`；简历列表 Panel 加 `glassTable` |
| `src/pages/resumes.module.css` | 页头/概览 L2、表格 L1、动效与移动端样式 |
| `tokens.json` / `src/styles/tokens.css` | 新增 `semantic.glass.overlay`；令牌总数 580 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、简历列表表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影；表格行不单独模糊 |
| L2 | 页头、简历库概览 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 简历详情、上传、解析队列、确认框 | `blur(34px)` + 白 14% + 深层阴影 + 暗色遮罩；portal 通过 `body.glass-route` 继承令牌 |

同屏玻璃元素：侧栏 1 + 页头 1 + 概览 1 + 表格容器 1 = **4 个**；打开抽屉或详情后仍不超过 5 个。

## 3. 页面结构

- 页头：玻璃条，标题 16px/600，副标题 12px ink-2；上传按钮改为单一青色 accent 主按钮，不再出现旧的靛蓝。
- 重复提示：保留琥珀色警告，不加 blur，避免和主操作抢层级。
- 概览：大数字 30px/600，四项统计 12px 标签 + 20px 数值；口径仍是「当前可见 6 份 / 队列已完成 10」，不合并两个来源。
- 筛选：关键词输入、搜索、学历下拉、历史版本开关全部走玻璃字段令牌；输入框 10px 圆角，focus 青色描边。
- 表格：L1 容器、表头 12px ink-2、行高 48px、行 hover 白 4.5%；姓名链接保留 44px 最小点击区。
- 分页、空态、错误态沿用原组件，只由作用域令牌换色。

## 4. 浮层

| 浮层 | 结果 |
|---|---|
| 简历详情 `?resume=8` | 880px L3 弹窗；正文两栏、技能标签、解析日志、版本列表、测评侧栏全部深色可读 |
| 上传简历 | L3 弹窗；拖拽区改为玻璃字段底，不再有浅色块 |
| 解析队列 | L3 右侧抽屉；恢复 `position:absolute`，不再被误改成左上角 |
| 疑似重复 / 转正确认 | 共用 Modal / ConfirmDialog，自动获得 L3 |

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 概览 | 165ms | 620ms | 18px |
| 表格容器 | 390ms | 620ms | 18px |

- 只动 `transform` / `opacity`，`animation-fill-mode: backwards`。
- reduced-motion：页头、概览、表格动画全部关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 33% |
| 768 × 900 | 768 / 768 | 顶部导航横向化，表格隐藏次要列 |
| 390 × 844 | 390 / 390 | 无页面横向溢出；表格在自身 `overflow-x:auto` 内滚动 |

打开详情 `?resume=8` 后 390 宽仍为 390 / 390，弹窗铺满可用宽度，正文与技能标签自动换行。

搜索回归：输入「程磊」并触发检索，列表返回 1 份，概览文案切到「当前筛选结果」，分页回到 1 页。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 580 tokens defined.
dist/assets/index-qjKhqt2V.css  172.30 kB │ gzip:  26.77 kB
dist/assets/index-Bek6tJcB.js   577.48 kB │ gzip: 172.89 kB
✓ built in 11.68s
```

## 8. 截图

- `shots/glass-resumes-1440.png`
- `shots/glass-resumes-768.png`
- `shots/glass-resumes-390.png`
- `shots/glass-resume-modal-1440.png`
- `shots/glass-resume-upload-1440.png`
- `shots/glass-resume-queue-1440.png`
- `shots/glass-resume-modal-390.png`
- `shots/glass-resumes-search.png`

## 9. 已知边界

- 目前只有 `/dashboard`、`/resumes` 挂玻璃壳层；点其他菜单会回到旧浅色页面，这是逐页迁移的过渡态。
- `/resumes` 的概览「当前可见 6 份」与「已解析 10」来自不同统计：前者是列表总数，后者是解析队列累计完成数，不是同一口径。
- 390 下表格仍保留全部列，在表格容器内横向滚动；移动端系统性适配仍按用户要求暂缓。
- 本轮未改后端，也未改搜索、筛选、上传、删除、转正等业务逻辑。
