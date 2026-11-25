# GLASS-P01 · 壳层 + 工作台

回归对象：`mvp/frontend-v2` 的 `/dashboard` 与全局壳层。
本轮只把「壳层 + 工作台」切到玻璃质感；其余页面仍保持 Corporate Trust 浅色，逐页迁移。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/styles/glass-app.css` | 新增工作台玻璃作用域：L0 背景、L1 侧栏、L2 顶栏/卡片/面板、暗色语义令牌映射 |
| `src/components/app-shell.tsx` | 只在 `/dashboard` 挂 `.glass-app`，并加光斑背景、`glass-side` / `glass-nav` / `glass-main` 作用点 |
| `src/pages/dashboard.tsx` | Panel 增加 `glassPanel`；KPI 数字增加计数生长 |
| `src/pages/dashboard.module.css` | 顶栏、KPI、队列、匹配、表格的玻璃外观与进场编排 |
| `tokens.json` / `src/styles/tokens.css` | 新增 `semantic.glass.warn-soft`、`neutral-soft`、`glow` |
| `public/glass-noise.svg` | 复用登录页的 160px `feTurbulence` 噪点 |

路由、权限、接口、上传、队列处理、最近匹配和最近操作表全部未改。

## 2. 层次与玻璃数量

| 层 | 元素 | 做法 |
|---|---|---|
| L0 | 页面底色 | `--glass-page-bg` 深底 + 三枚大光斑 + 极淡噪点；光斑 `blur(80px)`，透明度统一走令牌 |
| L1 | 侧栏 | 白 5.5% 玻璃 + `blur(18px)` + 单层软阴影；当前项改用更亮玻璃 + 右侧 accent 圆点 |
| L2 | 顶栏、4 张 KPI、队列/匹配/最近操作 3 个面板 | 白 9.5% 玻璃 + `blur(24px)` + 双层阴影；KPI hover 上浮 |
| L3 | 本轮未新增 | 工作台没有弹层；后续页面沿用现有 Modal/Drawer 升级 |

同屏 `backdrop-filter` 元素：侧栏 1 + 顶栏 1 + KPI 4 + 面板 3 = **9 个**，低于 8–12 上限；表格行、标签、按钮均不单独模糊。

## 3. 壳层细节

- 网格列：`232px + 16px = 248px`，符合侧栏 240–260px 规范。
- 侧栏 sticky，顶部/底部留 16px，玻璃圆角 22px。
- 当前导航项：白色 6% 底 + 顶边 1px 内高光 + 右侧 6px accent 圆点；没有整条填充色块。
- 导航图标与文字间距 10px，行高 38–40px。
- 移动端 ≤900px：侧栏改为顶部横向玻璃条，菜单横向滚动，主内容单列。
- 顶栏高 48px，左标题 16px/600，右侧只保留「上传简历」，不超过 5 个元素。

## 4. 工作台内容

- KPI：标签 12px ink-2（在偏亮玻璃上仍可读）；数值 30px/600、`tabular-nums`；单位 12px ink-2；说明 12px ink-2。
- KPI hover：`translateY(-3px)`；只改 transform，不重绘背景滤镜。
- 队列：底槽白色 6%，填充按状态走 accent / ink-3 / warn / danger，不额外加 glow。
- 最近匹配：分数用 accent / danger，分割线统一白色 7%。
- 最近操作表：表头 12px ink-3、行高 48px、行 hover 白色 4.5%、无逐行玻璃。
- 禁用按钮：改用玻璃字段底、ink-3 文字、白色 12% 边框，不再出现浅色白底。

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 侧栏 | 0ms | 620ms | 18px |
| 顶栏 | 110ms | 620ms | 18px |
| KPI 1–4 | 165 / 220 / 275 / 330ms | 620ms | 18px |
| 队列、匹配、最近操作 | 390ms | 620ms | 18px |
| KPI 数值 | 数据到达后 | 900ms | 0 → 终值，四次缓出 |

- 曲线统一 `--ease-expo`；只动 `transform` / `opacity`。
- `prefers-reduced-motion: reduce`：侧栏、顶栏、KPI、面板动画全部关闭；KPI 直接显示终值。
- 全屏落定约 1.0s；KPI 计数最长 0.9s。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1910 × 974 | 1910 / 1910 | 无页面横向溢出 |
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；内容高度 1490 |
| 768 × 900 | 768 / 768 | 侧栏横向化，内容单列 |
| 390 × 844 | 390 / 390 | 无页面横向溢出；顶部导航在自身容器内横向滚动 |

说明：390 的导航链接 `right` 坐标会超出视口，但被 `.glass-nav` 的 `overflow-x: auto` 收纳，页面本身不横向滚动；这是移动端规范要求的横向滚动导航。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 579 tokens defined.
dist/assets/index-CXVIY8zc.css  166.00 kB │ gzip:  25.88 kB
dist/assets/index-DxmTIs6C.js   577.11 kB │ gzip: 172.75 kB
✓ built in 3.54s
```

## 8. 截图

- `shots/glass-dashboard-1440.png`
- `shots/glass-dashboard-1910.png`
- `shots/glass-dashboard-768.png`
- `shots/glass-dashboard-390.png`

## 9. 已知边界

- 只有 `/dashboard` 挂 `.glass-app`；点其他菜单会回到旧浅色壳层与旧页面。这是逐页迁移的临时状态，不是遗漏。
- 工作台没有 L3 弹层；详情弹窗仍走旧浅色样式，等对应页面迁移时统一升级。
- KPI 四张卡的色温会随背后光斑轻微变化（玻璃折射），玻璃材质本身一致；如仍觉得差异过大，下一轮可进一步降低到 0.3。
- 本轮未改后端；数据仍是演示库（现行简历 10 条、在招岗位 3 个、队列 0）。
