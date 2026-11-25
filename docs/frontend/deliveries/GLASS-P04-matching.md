# GLASS-P04 · 岗位匹配

本轮把 `/matching` 接到玻璃壳层：页头、岗位选择、五项统计、匹配名单和分数条统一到 L1/L2，重新匹配确认弹窗走 L3。匹配计算、筛选、分页、岗位切换和权限分支未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/matching` |
| `src/pages/matching.tsx` | 页头包 `pageHead`（含 403 / 加载错误分支）；匹配名单 Panel 加 `glassTable` |
| `src/pages/matching.module.css` | 页头/统计卡 L2、名单 L1、筛选器、分数条上下文、动效与移动端 |
| `src/styles/glass-app.css` | 补 `--score-track`、`--score-fill`、`--score-threshold`、`--score-pass-text`、`--score-fail-text` 的玻璃直连覆盖 |
| `tokens.json` | 令牌总数仍为 583，本轮只新增组件令牌映射 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、匹配名单表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头、五项统计条 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 重新匹配确认 | `blur(34px)` + 白 14% + 暗色遮罩 |

同屏玻璃元素：侧栏 1 + 页头 1 + 统计条 1 + 名单 1 = **4 个**；确认弹窗打开后 5 个。

## 3. 页面

- 页头：16px/600 标题、12px ink-2 副标题；右侧岗位选择器 + 青色「运行匹配」主按钮。
- 统计条：5 格 L2 玻璃，扫描/通过/未通过/平均分/合格线；数字 18px/600，单位 12px ink-2。
- 统计说明：ink-2，不再用低对比三级灰。
- 筛选器：玻璃字段底；激活项改为 accent 14% 底 + accent 文字 + accent 描边，和主按钮同一语义。
- 表格：L1 容器、表头 ink-2、行高 48px、行 hover 白 4.5%。
- 分数条：轨道改深色字段底，填充改 accent，阈值刻度用 ink；此前共享 token 在作用域内仍解析成旧浅色/靛蓝，本轮直连覆盖修掉。
- 结论徽标：通过 accent、未通过 danger；原因列 ink-2，超长省略并保留 `title`。

## 4. 浮层

重新匹配确认：L3；文案、覆盖提示、取消/继续匹配按钮完整保留；本轮只打开截图，没有点「继续匹配」，未写库。

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 统计条 | 165ms | 620ms | 18px |
| 匹配名单 | 390ms | 620ms | 18px |

- 只动 `transform` / `opacity`，`animation-fill-mode: backwards`。
- reduced-motion：三处动画全部关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 16% |
| 768 × 900 | 768 / 768 | 顶部导航横向化，表格隐藏学历/年限/技能列 |
| 390 × 844 | 390 / 390 | 无页面横向溢出；表格在容器内横向滚动 |

390 统计条改为 2 列 + 「合格线」整行，没有空单元格；匹配名单保留姓名/分数两列。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-Ii9SNMsV.css  180.96 kB │ gzip:  27.75 kB
dist/assets/index-Do-dEH6K.js   578.39 kB │ gzip: 173.10 kB
✓ built in 10.92s
```

## 8. 截图

- `shots/glass-matching-1440.png`
- `shots/glass-matching-768.png`
- `shots/glass-matching-390.png`
- `shots/glass-matching-confirm-1440.png`
- `shots/glass-matching-filter.png`

## 9. 已知边界

- 目前 `/dashboard`、`/resumes`、`/talent-profiles`、`/job-profiles`、`/matching` 已玻璃化；`/matching/:id` 匹配详情仍是旧页面，下一轮处理。
- 390 下名单只保留姓名/分数，其他列在响应式规则中隐藏。
- 本轮没有真正执行「继续匹配」，避免覆盖演示库已有 6 条结果。
- 未改后端和匹配算法。
