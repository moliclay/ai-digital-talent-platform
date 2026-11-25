# GLASS-P09 · 成绩报告

本轮把 `/exams/result/:sid` 接到玻璃壳层：页头、成绩概览、错题表和复习计划统一到 L1/L2。成绩计算、错题/复习数据、回写逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/exams/result/` 前缀 |
| `src/pages/exam-result.tsx` | 404/403/加载错误/加载中/正常五类返回的页头统一包 `pageHead`；概览 Panel 加 `glassPanel`，错题/复习 Panel 加 `glassTable` |
| `src/pages/exam-result.module.css` | 页头 L2、概览 L2、两张表 L1、文字/表格/分数状态与动效 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、错题表、复习计划表 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头、本次成绩概览 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 本轮无弹层 | 页面只有成绩、错题和复习表 |

同屏玻璃元素：侧栏 1 + 页头 1 + 成绩概览 1 + 错题表 1 + 复习表 1 = **5 个**。

## 3. 页面

- 页头：16px/600 标题「王峰 · 成绩」，副标题试卷名/满分/合格线；右侧查看简历 + 返回按钮。
- 成绩概览：大字分数 90 / 100，通过/未通过徽标，结论、建议、累计错题；通过 accent、未通过 danger。
- 错题表：L1；题目、你的答案、标准答案、得分、解析；标准答案为题库原样展示，附说明。
- 复习计划：L1；只显示与本卷错题题干匹配的计划，保留「仅本卷相关」口径。
- 390 下隐藏标准答案/解析列，保留题目/你的答案/得分，长答案自动换行。
- 404/403/网络错误空态沿用原组件，仅换玻璃 token。

## 4. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 成绩主体（概览 + 两张表） | 165ms | 620ms | 18px |

- 动画挂在 `.body` 外层，表格卡不参与 transform。
- reduced-motion：页头和主体关闭；CDP 实测 `getAnimations().length === 0`。

## 5. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 40% |
| 390 × 844 | 390 / 390 | 无页面横向溢出；错题表三列完整 |

真实数据：王峰，submission id `12`，算法工程师内测，90 / 100，合格线 60，通过。

## 6. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-1mRXnz3p.css  191.13 kB │ gzip:  28.70 kB
dist/assets/index-BrPLp0o3.js   580.15 kB │ gzip: 173.40 kB
✓ built in 4.68s
```

## 7. 截图

- `shots/glass-exam-result-1440.png`
- `shots/glass-exam-result-390.png`

## 8. 已知边界

- `/exams/result/38` 等旧 submission id 已不存在，访问会显示「答卷不存在」空态；当前演示用 `id=12`。
- 复习计划仍按「本卷错题题干」匹配，这是后端缺口 G28 的前端兜底，不是本轮新增逻辑。
- `/exams/result/:sid` 没有 L3 弹层；页面本身是整页报告。
- 未改后端判分、错题统计和复习计划接口。
