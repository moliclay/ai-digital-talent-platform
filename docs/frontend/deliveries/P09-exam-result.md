# P09 成绩与错题 · 交付说明

路由：`/exams/result/:sid`（从 P07 答卷行点考生姓名进入）
日期：2026-11-03
页面任务：这份卷子得了多少、错在哪、接下来复习什么。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/exam-result.tsx` / `.module.css` | 成绩结论、本卷错题表、本卷复习计划 |
| `src/pages/exams.tsx` / `.module.css` | 答卷行考生姓名改为链接，进入成绩页 |
| `src/content/copy.ts` | 新增 `examResult.*` |
| `src/app.tsx` | 路由 `/exams/result/:sid` |
| `PAGE-MAP.md` | 新增 G28 |

---

## 2. 页面结构

- 标题：`{考生} · 成绩`；副标：试卷名 · 满分 · 合格分。
- **本次成绩**：大字分数 / 满分 + 通过徽标 + 一句话结论 + 后端建议 + 「该考生累计错题 N 道（含其他试卷）」。
- **错题**：本卷 `score < max_score` 的题；表头 题目 / 你的答案 / 标准答案 / 得分 / 解析；未作答显示「未作答」；无解析或评语时显示「暂无解析」。
- **复习计划**：按本卷错题题干匹配该考生的 `review-plans`，表头 复习时间 / 题目 / 状态；状态 `scheduled` → 「已安排」。
- 错题表下脚注：标准答案按题库记录原样展示；字母表示选项序号。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 直接打开 | 3 段骨架（代码路径） |
| empty | 全对 → 本卷无错题 | 「这份卷子没有错题。」（代码路径；演示卷有错题） |
| error | CDP 拦截 `*api/exam-submissions/4*` | 「成绩没取到。」+ 中文说明 + 重试（`shots/exam-result-error.png`） |
| no-permission | `emp_chen`（无 `exam:view`） | 「没有查看成绩的权限」（`shots/exam-result-403.png`） |
| over-limit | 后端错题/复习各 limit 200；本页再按本卷题干过滤 | 复习计划标「仅本卷相关」，不显示「最近 200 条」的全量口径 |

404：`/exams/result/99999` → 「答卷不存在」+ 返回（`shots/exam-result-404.png`）。

---

## 4. 真实数据（P08 真交卷的那一份）

```
submission id=4
张伟 · 综合能力测评（五维）
62 / 140，合格 60，通过
错题 6 道（本卷 score < max 的题）
该考生累计错题 9 道（含其他试卷）
复习计划：该考生共 9 条，按本卷题干过滤后 6 条（截图首屏可见 3 条）
```

错题明细（真实返回）：

| 题目 | 你的答案 | 标准答案 | 得分 |
|---|---|---|---|
| 跨部门方案评审会… | 先确认对方担心的具体风险点 | B | 0 / 10 |
| 项目复盘里最有价值的一条… | 哪一步可以复用或改流程 | B | 0 / 10 |
| 时间复杂度 O(n log n)… | 未作答 | 快速排序 | 0 / 20 |
| 线上服务 P99 延迟… | 链路追踪与慢查询 | B | 0 / 10 |
| 业务方案「更多线索」… | 拆解线索质量与转化漏斗 | B | 0 / 10 |
| 简述 Transformer 注意力机制 | Q/K/V、缩放点积、多头注意力 | 要点：Q/K/V、缩放点积、多头 | 42 / 60 |

其中「标准答案是 B」的题是 G27 的种子数据问题（答案混用字母/文本），不是前端判错。

---

## 5. 权限

| 角色 | 能看 |
|---|---|
| admin / hr_zhao | 全部（`exam:view`） |
| pm_wang | 可看（`exam:view`） |
| emp_chen | 无 `exam:view`，403 |

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `examResult.title/sub/back/summaryTitle` | 标题、副标、返回、成绩卡标题 |
| `examResult.conclusion/recommendation/cumulativeWrong` | 结论、建议、累计错题 |
| `examResult.wrongTitle/wrongCount/wrongColumns/noAnswer/noAnalysis/scoreOf` | 错题表 |
| `examResult.standardNote` | 标准答案脚注 |
| `examResult.reviewTitle/reviewMeta/reviewColumns/statusScheduled/reviewEmpty` | 复习计划 |
| `examResult.wrongEmpty/notFound*/forbidden*/loadError*/retry` | 空态与错误 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入成绩页 | `page` |

不含考生姓名、答案正文。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 140.49 kB gzip；CSS 14.05 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（106 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟） |
| 1440 | 915 字，<13px 占 13%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；错题表隐藏「标准答案/解析」，保留题目/你的答案/得分 |

---

## 9. 已知问题（不阻塞）

1. **G27：标准答案混用字母/文本。** 表中「标准答案 B」与「你的答案 文字」不可直接对照；已加脚注说明，根治要后端统一答案格式。
2. **G28：没有 `exam_id`。** 成绩页无法「再做一次」（详情不返 exam_id），复习计划只能按题干文本匹配本卷错题；同题干跨试卷可能混入。
3. **累计错题含其他试卷**：明确标注「含其他试卷」，不与本卷 6 道混为一谈。
4. **复习计划时间相同**：交卷时批量生成，时间都是同一时刻 + 1 天。
5. **全对空态未实测**：演示答卷都有错题；代码路径存在。
6. **无错题详情跳转**：错题表已展开题干/答案/解析，不再单独做详情页。
7. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/exam-result-1440.png` | 1440×1200 成绩页（62/140，6 道错题） |
| `shots/exam-result-light.png` | 1440×1200 浅色 |
| `shots/exam-result-768.png` | 768×1200 单列 |
| `shots/exam-result-403.png` | 普通员工无权限 |
| `shots/exam-result-404.png` | 答卷不存在 |
| `shots/exam-result-error.png` | 成绩请求失败 |
