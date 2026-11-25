# GLASS-P05 · 匹配详情

本轮把 `/matching/:id` 接到玻璃壳层：页头、结论卡、硬条件表、评分构成和右侧信息面板统一到 L1/L2/L3。页面没有新增弹层，评分和判定逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 覆盖 `/matching/`；该路由挂 `glass-match-detail`，单独压低光斑 |
| `src/pages/match-detail.tsx` | 404/403、加载错误、加载中、正常四类返回的页头统一包 `pageHead`；7 个 Panel 加 `glassPanel` / `glassTable` |
| `src/pages/match-detail.module.css` | 页头 L2、表格 L1、右侧信息卡 L2、文字/表格/chips/原文样式与动效 |
| `src/styles/glass-app.css` | 匹配详情作用域光斑 0.28；右栏青色光斑再压到 45%；所有面板统一叠 22% 深色 tint |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、硬条件表、评分构成表 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头、结论卡、候选人信息、能力基线、技能命中、简历原文 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 本轮无新增弹层 | 返回/名单导航仍走页面跳转 |

同屏玻璃元素：侧栏 1 + 页头 1 + 结论 1 + 2 张表 + 4 张右侧信息卡 = **9 个**，低于 12 上限。

## 3. 页面

- 页头：16px/600 标题，副标题保留「岗位名 · 文件名」；返回名单 / 下载简历为二级 + 主按钮。
- 人工修正提示：琥珀色警示条，保持警示语义，不加 blur。
- 结论卡：最终得分 85.0、合格线 65、通过徽标；分数条轨道深色、填充 accent、阈值刻线 ink。
- 硬条件表：表头 ink-2，实际/要求/结论四列；通过 accent、失败 danger。
- 评分构成：维度/得分/权重/贡献四列，`tfoot` 基础上限与最终分；0 权重维度保留脚注说明。
- 右侧信息：候选人信息、能力基线、技能命中、简历原文四张 L2 卡；技能标签命中 accent、未命中玻璃字段。
- 原文预览保持 242 字折叠，展开后限高滚动，不截断半行。

## 4. 视觉调整

- 详情页单屏面板多，默认光斑 0.4 会让左栏偏蓝、右栏偏青绿；该路由把光斑降到 **0.28**，并把右栏青色光斑再压到 45%。
- 所有详情面板叠 **22% 深色 tint**，把左右栏的色相拉回同一冷色体系；玻璃半透明、细边框、顶边高光和双层阴影仍保留。
- 结论卡与右侧卡片不是同一个背景色温，但差异已收敛为辅助层级差，不再是两种材质。

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 结论卡 / 右侧卡 | 165ms | 620ms | 18px |
| 硬条件表 / 评分表 | 255ms | 620ms | 18px |

- 只动 `transform` / `opacity`，`animation-fill-mode: backwards`。
- reduced-motion：页头、卡片、表格全部关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 33% |
| 390 × 844 | 390 / 390 | 无页面横向溢出；单列后正文和表格仍在容器内 |

真实数据：`刘洋`，匹配记录 id `133`，岗位 `2`（AI 产品经理），最终得分 85.0 / 合格线 65 / 通过。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-B8qCAGjN.css  183.83 kB │ gzip:  28.02 kB
dist/assets/index-Bmpx3iTY.js   578.95 kB │ gzip: 173.20 kB
✓ built in 5.50s
```

## 8. 截图

- `shots/glass-match-detail-1440.png`
- `shots/glass-match-detail-390.png`

## 9. 已知边界

- 目前 `/dashboard`、`/resumes`、`/talent-profiles`、`/job-profiles`、`/matching`、`/matching/:id` 已玻璃化；其余页面仍是旧浅色。
- 这次截图用的记录是演示库当前 `id=133`；旧的 `id=56` 已被重新匹配覆盖，访问会显示「匹配记录不存在」的 404 空态。
- 页面没有 L3 弹层，详情本身是整页；如果后续要改成弹窗，需要单独评审，不在本轮范围。
- 未改匹配算法、分数折算和权限逻辑。
