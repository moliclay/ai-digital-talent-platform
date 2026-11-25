# P07 测评中心 · 交付说明

路由：`/exams`
日期：2026-11-03
页面任务：有题库、能出卷、看得到谁交了卷。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/exams.tsx` / `.module.css` | 三区（题库 / 试卷 / 答卷）、题库选择、题目表、分页 |
| `src/pages/exams/types.ts` | 题库 / 题目 / 试卷 / 答卷类型 |
| `src/pages/exams/bank-dialog.tsx` | 新建题库（名称 + 说明，可见 label） |
| `src/pages/exams/question-dialog.tsx` | 新建题目（题库 / 题型 / 题干 / 选项 / 答案 / 分值 / 难度 / 知识点，均带可见 label） |
| `src/pages/exams/exam-dialog.tsx` | 出卷（名称 / 分类 / 题库复选 / 抽题数 / 合格分 / 时长，均带可见 label + 题库题数提示） |
| `src/pages/exams/dialogs.module.css` | 三个对话框共享样式 |
| `src/content/copy.ts` | 新增 `exams.*` |
| `src/app.tsx` / `app-shell.tsx` | 路由 `/exams`，菜单转为已实现 |
| `PAGE-MAP.md` | 新增 G21 |

---

## 2. 页面结构

- 标题 + 口径；AI 不可用时顶部黄条「简答题仅按关键词评分」（读 `/ai/status`）。
- 三区各有一个 `h2`（Panel 的 `id` + `aria-labelledby`）：
  1. **题库**：题库卡片（名称 / 说明 / 题数，点选切换）+「新建题库」；下方题目表（题型 / 题干 / 分值 / 难度 / 知识点 / 标准答案，50 条/页）+「新建题目」。
  2. **试卷**：试卷表（名称 / 分类 / 题数 / 总分 / 合格分 / 时长 / 交卷）+「出卷」。
  3. **答卷**：答卷表（考生 / 试卷 / 得分 / 结论 / 建议），右上标「最近 100 条」。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首进 | 题库/题目/试卷/答卷骨架（代码路径） |
| empty | 无题库 / 无试卷 / 无答卷 | 三种空态各有下一步文案；演示库三者都有数据，未实测（代码路径） |
| error | CDP 拦截 `*question-banks*` | 「测评数据没取到。」+ 中文说明 + 重试（`shots/exams-error.png`） |
| no-permission | `emp_chen`（无 `exam:view`） | 「没有查看测评的权限」（`shots/exams-403.png`） |
| over-limit | 出卷 `question_count` 大于题库总数 | 后端取 min，前端对话框提示「所选题库共 N 题；超过就取满」，出卷后回显实际题数 |

---

## 4. 真实数据

1. **列表**：1 个题库（算法基础题库，7 题）、3 张试卷（含本次验证新增的「出卷验证(临时)」）、3 条答卷。
2. **题目表**：7 题，题型 / 难度 / 知识点 / 标准答案齐全；长答案与长题干 `title` 给全文。
3. **出卷 over-limit 实测**：用 UI 相同的 payload 发 `POST /exams`，`question_count=99`（题库只有 7 题），返回 `total_questions=7`——后端取满，前端对话框提示口径与之一致。新增的验证试卷留在列表第 1 行（后端无删除接口）。
4. **答卷**：最近 100 条（后端硬编码），右上标注口径；3 条里 2 条通过（张伟 107/140、程磊 80/100）、1 条（陈宇 92/100）。
5. **AI**：`/ai/status` 返回 `available=true`，黄条不显示；AI 不可用提示是代码路径（演示环境网关在线）。

三个创建对话框只打开、未在页面上提交（提交用同一 payload 走后端实测通过，避免在演示库新增题库/题目）。

---

## 5. 权限

| 角色 | 能做什么 |
|---|---|
| admin | 看、可建库 / 建题 / 出卷（`exam:create`） |
| hr_zhao | 看、可建库 / 建题 / 出卷 |
| pm_wang | 可看（`exam:view`），无创建按钮 |
| emp_chen | 无 `exam:view`，403 |

创建按钮只在 `exam:create` 时渲染。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `exams.title/sub/aiOnlyKeyword` | 标题、口径、AI 降级提示 |
| `exams.banksTitle/examsTitle/submissionsTitle` | 三区标题 |
| `exams.newBank/newQuestion/newExam` | 三个创建按钮 |
| `exams.*Empty/*Hint/bankCount/questionCount` | 空态与计数 |
| `exams.*Columns.*` | 三张表表头 |
| `exams.questionTypes/difficulty` | 题型 / 难度中文映射 |
| `exams.duration/submissionsCount/score/passed/failed` | 时长、交卷数、得分、结论 |
| `exams.bankDialogTitle/bankName/bankDesc/confirm` | 建库 |
| `exams.questionDialogTitle/q*` | 建题（每个控件有 label 文案） |
| `exams.examDialogTitle/e*` | 出卷 |
| `exams.examDone/loadError*/noPermission*/createError` | 结果与错误 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入 | `page` |
| `exam_bank_open` | 打开建库 | `page` |
| `exam_question_open` | 打开建题 | `page` |
| `exam_create_open` | 打开出卷 | `page` |

（创建成功/失败在对话框内未单独埋点，后续补 `exam_*_submit/done/failed`；不含题干、答案、考生姓名。）

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 135.56 kB gzip；CSS 13.02 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（102 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟） |
| 1440 | 574 字，<13px 占 15%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；三区单列；长文本省略号截断 |

---

## 9. 已知问题（不阻塞）

1. **G21：四个读接口不过滤数据范围。** hr/biz 看到全平台题库与答卷；前端按"平台级测评库"口径展示，不写"本部门"。
2. **三种空态未实测**：演示库题库 / 试卷 / 答卷都有数据，且后端无删除接口；空态代码路径存在。
3. **AI 不可用黄条未实测**：网关在线，`available=true`；黄条逻辑在 `ai.isSuccess && !available`。
4. **出卷验证新增了一张试卷**（「出卷验证(临时)」），后端无删除接口，留在列表；不影响功能。
5. **答卷无分页**：后端固定返回最近 100 条，前端按此展示并标注，不做二次分页。
6. **建题对话框选项是单个文本框按行拆**：不是逐项输入；够用但更精细的交互可后续迭代。
7. **`meta/skills`、`wrong-questions`、`review-plans`、`exams/{id}`、`submit` 等端点留给 P08/P09**，本页不引用。
8. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/exams-1440.png` | 1440×1200 三区完整 |
| `shots/exams-light.png` | 1440×1200 浅色 |
| `shots/exams-768.png` | 768×1200 单列 |
| `shots/exams-bank-dialog.png` | 新建题库对话框 |
| `shots/exams-question-dialog.png` | 新建题目对话框（全字段带 label） |
| `shots/exams-exam-dialog.png` | 出卷对话框（全字段带 label + 题库题数） |
| `shots/exams-error.png` | 请求失败 |
| `shots/exams-403.png` | 普通员工无权限 |
