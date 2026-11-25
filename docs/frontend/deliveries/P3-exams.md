# P3 测评域 · 交付

日期：2026-11-04
范围：受众、题库导入、测评任务、绑定/取消、答题 assignment 上下文、成绩/简历联动；**P4 未开工**。

---

## 1. 受众

- `QuestionBank` / `Exam` 新增 `audience: candidate | employee`。
- 测评页新增 `AudienceFilter`，同时约束：
  - 题库列表
  - 试卷列表
  - 测评任务列表（前端按 `ExamAssignment.audience` 过滤）
- 题库卡片、试卷表、任务表均显示受众徽标。
- 新建题库、出卷弹窗都新增「受众」选择；出卷时题库列表只列同受众题库。
- 当前筛选为「员工」且无员工数据时，题库/试卷/任务分别显示空态。

---

## 2. 题库文件导入

弹窗三步：

1. `FileDrop` 选一个文件（txt / md / csv / docx / pdf / xlsx）。
2. `POST /question-banks/{id}/import`，只生成草稿，**不落库**。
3. 逐题编辑后 `POST /question-banks/{id}/import/confirm`。

草稿编辑支持：

- 题型（单选/多选/填空/简答）
- 分值、难度
- 题干
- 选项（每行一个）
- 答案、知识点
- 移除单题

显示 `source=ai|rule`、`parsed_count`、`warnings`、`needs_review`；确认后显示 `created / skipped / failed`。

### 实测

```
文件：p3-import-sample.txt
source=ai, parsed_count=1
确认结果：已导入 0 题；跳过 1 题；失败 0 题
```

跳过原因是文件题干与题库已有题重复，验证了后端同题干幂等；没有向演示题库新增脏数据。

---

## 3. 测评任务

试卷上方新增「测评任务」面板：

- 列：候选人 / 试卷（含受众）/ 状态 / 截止 / 结果 / 操作
- 状态筛选：全部、待测评、已提交、已取消
- 待测评：`开始答题`、`取消`
- 已提交：`查看成绩`
- 已取消：无操作

### 绑定弹窗

- 只列已发布试卷
- 显示题量/合格分/时长
- 候选人复选、搜索、全选/清空
- 可选截止时间、备注
- 批量提交 `parsed_resume_ids`
- 返回 `created / existed / failed` 汇总

### 实测

```
绑定李娜到「张伟·自适应测评」（exam 20）
→ created_count=1, existed_count=0, failed_count=0
→ assignment id 38

取消张伟的「张伟·错题基线」绑定
→ 提示「已取消这条测评任务。」
→ assignment id 39 status=cancelled
```

---

## 4. 答题 assignment 上下文

从任务行点「开始答题」进入：

```
/exams/20/take?assignment_id=38&candidate=李娜
```

- 顶部提示「本次为绑定测评；提交后会回写候选人简历的测评状态。」
- 候选姓名由任务带入且锁定，提示「候选人由绑定任务带入，不能修改。」
- 草稿键为 `tl.exam.{examId}.{assignmentId}`，同试卷不同任务不串草稿。
- 交卷 body 带 `assignment_id`。
- 成功交卷后 invalidate `resumes`、`exam-assignments`、`exam-submissions`。

### 实测

```
assignment 38 提交后 status=submitted, submission_id=11
简历 4（李娜）exam_summary: state=submitted, label=已测评
成绩：0 / 120，未通过（本次测试选项未答对，链路正常）
```

---

## 5. 成绩与简历联动

- 成绩页新增「查看候选人简历」，跳 `/resumes?resume=<parsed_resume_id>`，复用全局详情弹窗。
- 简历列表「测评」列通过 `exam_summary` 显示「已测评」；李娜已从「未测评」变为「已测评」。

---

## 6. 门禁

```
tsc 0
lint_hardcodes 0 处（134 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
build JS 171.91 kB gzip / CSS 22.19 kB gzip
```

---

## 7. 已知

1. 演示库新增两条任务：李娜 `submitted`（id 38 / submission 11，0 分）、张伟 `cancelled`（id 39）。程磊原有 `cancelled`（id 32）。
2. 题库导入只验证了「重复题干 → skipped」；未向演示库新增真实题目，因此 `created > 0` 路径没有演示数据，但请求体与后端 `confirm()` 一致。
3. 当前无员工受众题库/试卷样本；员工分支只验证了筛选空态，未创建员工数据。
4. 答题测试只点了选项，未按正确答案作答，成绩 0 分；这是测试数据，不是评分链路问题。
5. 390 移动端未系统适配（用户已明确暂缓）。

---

## 8. 截图

| 文件 | 说明 |
|---|---|
| `shots/p3-exams-full.png` | 测评页全貌：任务/题库/试卷/答卷 |
| `shots/p3-bind-dialog.png` | 绑定测评弹窗 |
| `shots/p3-bind-result.png` | 绑定成功，李娜待测评 |
| `shots/p3-exam-take.png` | assignment 答题上下文与锁定姓名 |
| `shots/p3-result.png` | 成绩页与查看简历按钮 |
| `shots/p3-result-resume.png` | 成绩页跳简历详情弹窗 |
| `shots/p3-import-draft3.png` | 题库导入 AI 草稿 |
| `shots/p3-import-confirm.png` | 确认导入结果（跳过重复） |
| `shots/p3-audience-employee.png` | 员工受众空态 |
| `shots/p3-bank-dialog.png` | 新建题库受众 |
| `shots/p3-exam-dialog.png` | 出卷受众与题库过滤 |
