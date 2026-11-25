# P08 答题 · 交付说明

路由：`/exams/:id/take`（从 P07 试卷行「答题」进入）
日期：2026-11-03
页面任务：HR 代开卷、代填考生姓名，在时限内答完并交卷。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/exam-take.tsx` / `.module.css` | 考生信息、倒计时、进度、题目、交卷确认、结果卡 |
| `src/pages/exams.tsx` | 试卷行新增「答题」操作（`exam:view` 可见） |
| `src/content/copy.ts` | 新增 `examTake.*`、`exams.take`、`exams.examColumns.action` |
| `src/app.tsx` | 路由 `/exams/:id/take` |
| `scripts/p08-submit.js` | 端到端提交脚本（真实 UI 填答→确认→交卷） |
| `scripts/p08-confirm.js` | 交卷确认弹窗截图脚本 |
| `scripts/shot.mjs` | 新增 `--evalFile`，可在截图前执行真实交互脚本 |
| `PAGE-MAP.md` | 新增 G27 |

---

## 2. 页面结构

- 标题 = 试卷名；副标 = 题数 · 时长 · 合格分 · 总分。
- 右上：`返回测评中心` + `交卷`（提交中禁用）。
- 考生信息卡：`考生姓名`（FormField 可见 label + 必填提示）、剩余时间（18px 等宽数字）、答题进度（已答 k/N）；HR 代考说明。
- 题卡：题号 + 题型徽标 + 分值 + 题干（16px）；单选 radio、多选 checkbox、填空 input、简答 textarea；选项整行可点，A/B/C/D 前缀。
- 底部：进度 + 「到点自动交卷」说明 + 交卷。
- 交卷确认：显示未答题数；交卷成功后在页顶显示结果卡（分数 / 通过 / 错题数）+ 返回。
- 草稿：`localStorage["tl.exam.{id}"]` 存考生姓名、答案、开始时间；提交成功后清除。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 直接打开 | 3 段骨架（代码路径） |
| empty | 试卷 0 题 | 「这份试卷没有题目」+ 找 HR 重新出卷（代码路径；演示卷都有题） |
| error | CDP 拦截 `*api/exams/2*` | 「试卷没取到。」+ 中文说明 + 重试（`shots/exam-take-error.png`） |
| no-permission | `emp_chen`（无 `exam:view`） | 「没有答题权限」+ 中文说明（`shots/exam-take-403.png`） |
| over-limit | 倒计时到 0 自动交卷；答案本地草稿 | 40/60 分钟演示卷未跑到 0，自动交卷是代码路径；草稿写入为代码路径（未做跨刷新实测） |

404：`/exams/999/take` → 「试卷不存在」+ 返回（`shots/exam-take-404.png`）。

---

## 4. 真实交互（不是只截图）

用 `--evalFile scripts/p08-submit.js` 在真实页面里完成：

```
填考生姓名「张伟」
选：PyTorch、TensorFlow、先确认对方担心的具体风险点、哪一步可以复用或改流程、
    链路追踪与慢查询、拆解线索质量与转化漏斗
填简答：Q/K/V、缩放点积、多头注意力
点「交卷」→ 点「确定交卷」
```

返回：

```
h1: 综合能力测评（五维）
交卷成功
62 / 140
通过
错题 6 道
答题进度: 已答 6 / 7 题
```

说明：

- 交卷真的写入了 `exam_submissions`（新增 1 条），P07 答卷数从 3 → 4。
- 交卷确认弹窗实测文案：「还有 5 题没答，会按 0 分计。确定交卷？」（`shots/exam-take-confirm.png`）。
- 62 分里包含简答的部分得分；后端按关键词 + AI 复核给分。

---

## 5. 权限与口径

| 角色 | 能否答题 |
|---|---|
| admin / hr_zhao | 可以（`exam:view`） |
| pm_wang | 可以（`exam:view`），但本期按「HR 代考」使用 |
| emp_chen | 无 `exam:view`，403 |

试卷接口不返回标准答案；答案在交卷时由后端比对。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `examTake.titleFallback/back/meta` | 标题、返回、元信息 |
| `examTake.candidate/candidatePanel/candidatePlaceholder/candidateHint/candidateNote` | 考生信息 |
| `examTake.timeLabel/progressLabel/progress/remaining/remainingWarn/timeUp` | 计时与进度 |
| `examTake.submit/submitting/confirmTitle/confirmWithMissing/confirmAllAnswered/confirm` | 交卷与确认 |
| `examTake.errorName/errorSubmit/errorSubmitHint` | 校验与失败 |
| `examTake.emptyTitle/emptyHint/doneTitle/doneScore/donePassed/doneFailed/doneWrong` | 空态与结果 |
| `examTake.question/points/essayPlaceholder/fillPlaceholder/autoSubmitNote` | 题卡 |
| `examTake.loadError/loadErrorHint/retry/forbidden*/notFound*` | 错误 / 403 / 404 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入答题页 | `page` |
| `exam_submit_done` | 交卷成功 | `page`、`exam_id`、`passed`、`score` |
| `exam_submit_failed` | 交卷失败 | `page`、`exam_id`、`status` |

不含考生姓名、答案正文。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 138.63 kB gzip；CSS 13.67 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（104 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟/计时） |
| 1440 | 585 字，<13px 占 21%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；单列题卡；考生卡与题卡同列 |

---

## 9. 已知问题（不阻塞）

1. **G27：选择题答案格式混用。** 种子题里有的标准答案是选项文本（「快速排序」「PyTorch,TensorFlow」），有的是字母（「B」）。答题页统一提交选项文本（与旧前端一致），字母答案的题会被判错——本次实测 7 题里 4 题受此影响。试卷接口不返答案，前端无法自动分流；待后端统一格式。
2. **自动交卷未实测**：演示卷 40/60 分钟，未等到 0；代码在 `expired && name` 时触发一次提交。
3. **草稿恢复未实测**：`localStorage` 写入是代码路径；跨刷新恢复没有在截图里验证。
4. **交卷后结果只在页内**：P09 未做，所以没有「查看成绩/错题」入口；结果卡给分数、通过、错题数。
5. **简答按关键词 + AI 复核**：AI 可用时取平均；不可用时只按关键词，页面未额外提示（P07 有 AI 状态黄条）。
6. **无题目导航/标记**：7 题一屏内可滚动，没做题号跳转与「标记待定」。
7. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/exam-take-1440.png` | 1440×1200 答题页 |
| `shots/exam-take-light.png` | 1440×1200 浅色 |
| `shots/exam-take-768.png` | 768×1200 单列 |
| `shots/exam-take-confirm.png` | 交卷确认（还有 5 题没答） |
| `shots/exam-take-done.png` | 交卷成功（62/140，通过，错题 6） |
| `shots/exam-take-error.png` | 试卷请求失败 |
| `shots/exam-take-403.png` | 普通员工无权限 |
| `shots/exam-take-404.png` | 试卷不存在 |
