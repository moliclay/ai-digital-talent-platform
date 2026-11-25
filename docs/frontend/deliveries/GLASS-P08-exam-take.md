# GLASS-P08 · 在线答题

本轮把 `/exams/:id/take` 接到玻璃壳层：页头、考生信息、题目区和交卷确认统一到玻璃语言。答题、计时、草稿、提交和自动交卷逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/exams/:id/take` 正则；`/exams/result/:sid` 不匹配 |
| `src/pages/exam-take.tsx` | 5 类返回的页头统一包 `pageHead`；结果 Panel、考生 Panel 加 `glassPanel` |
| `src/pages/exam-take.module.css` | 页头 L2、考生信息 L2、题目/选项玻璃字段、选中态、计时与动效 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏 | `blur(18px)` + 白 5.5% |
| L2 | 页头、考生信息、交卷结果 | `blur(24px)` + 白 9.5% + 双层阴影 |
| 内容面 | 题目卡、选项行 | 玻璃字段底 + 1px 白 9% 边框，**不加 blur** |
| L3 | 交卷确认 | `blur(34px)` + 白 14% + 暗色遮罩 |

题目卡不加 `backdrop-filter` 是刻意的：一套卷 8–20 题，每个题卡都模糊会直接把同屏玻璃数打爆，也会让滚动掉帧。题目用玻璃字段面，考生信息与结果用真正的 L2 玻璃。

同屏玻璃元素：侧栏 1 + 页头 1 + 考生信息 1 = **3 个**；出结果后 4 个；确认弹窗打开 5 个。

## 3. 页面

- 页头：试卷名 16px/600；副标题题量/时长/合格线/总分；返回 + 青色「交卷」。
- 任务提示：绑定任务为 accent 信息条；未绑定为玻璃字段条，文案保留。
- 考生信息：L2 玻璃卡；姓名输入深色玻璃字段；剩余时间与答题进度在右侧。
- 计时：正常 ink、≤5 分钟 warn、超时 danger；`role="timer"` 和 `aria-live` 保留。
- 题目：20 分/题型徽标/题干；选项为玻璃字段面，hover 白 4.5%，选中 accent 软底 + accent 文字/描边。
- 结果面板：分数、通过徽标、错题数、返回按钮；L2 玻璃。
- 底部交卷行：进度、自动交卷说明、主按钮；上边框改为玻璃分隔线。

## 4. 浮层

交卷确认：L3；未答题数、0 分提示、取消/确定交卷完整保留。本轮只打开截图，没有点「确定交卷」，没有写库、没有创建 submission。

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 答题主体（含考生卡、题目、底部行） | 165ms | 620ms | 18px |

- 动画挂在 `.body` 外层，题目卡本身不参与 transform。
- reduced-motion：页头和主体关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 44% |
| 390 × 844 | 390 / 390 | 无页面横向溢出；选项和计时完整显示 |

390 下考生信息自动单列，姓名输入、计时、进度、题目和选项都在容器内。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-BEgSC568.css  189.19 kB │ gzip:  28.48 kB
dist/assets/index-Bvmi8CfH.js   579.70 kB │ gzip: 173.32 kB
✓ built in 3.96s
```

## 8. 截图

- `shots/glass-exam-take-1440.png`
- `shots/glass-exam-take-390.png`
- `shots/glass-exam-take-confirm-1440.png`

## 9. 已知边界

- 只接入 `/exams/:id/take`；`/exams/result/:sid` 仍是旧页面，P09 处理。
- 题目卡使用玻璃字段面而非独立 L2 模糊卡；这是为了控制长卷的同屏玻璃数和滚动性能。
- 本轮没有提交答卷，演示库没有新增 submission。
- 未改答题提交、判分、草稿和自动交卷逻辑。
