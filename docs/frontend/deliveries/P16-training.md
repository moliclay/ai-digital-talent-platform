# P16 培训成长 · 交付说明

路由：`/training`
日期：2026-11-03
页面任务：看出能力缺口，生成培养计划，跟踪到提能。

**范围**：只接后端已有的 12 条培训端点，没有新增课程报名、学习打卡、计划删除这类后端不存在的功能。

---

## 1. 后端端点 → 前端入口

| 端点 | 前端入口 |
|---|---|
| `GET /training-courses` | 课程列表 + 名称搜索 |
| `POST /training-courses` | 新建课程 |
| `PUT /training-courses/{id}` | 编辑课程 |
| `DELETE /training-courses/{id}` | 删除课程（仅 `train:delete`） |
| `GET /training/diagnose` | 缺口诊断 |
| `POST /prejob-plans/generate` | 生成培养计划 |
| `GET /prejob-plans` | 培养计划列表 |
| `GET /prejob-plans/{id}` | 计划详情抽屉 |
| `POST /prejob-plans/tasks/{id}/progress` | 记录学习进度 |
| `POST /prejob-plans/tasks/{id}/complete` | 完成任务 |
| `POST /prejob-plans/tasks/{id}/assess` | 课后考核 |
| `GET /training/ledger` | 成长台账 |

---

## 2. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/training.tsx` / `.module.css` | 四标签、课程 CRUD、诊断、计划列表、台账 |
| `src/pages/training/types.ts` | 课程/诊断/计划/任务/台账类型 |
| `src/pages/training/course-dialog.tsx` | 新建/编辑课程 |
| `src/pages/training/plan-drawer.tsx` | 计划详情、记录进度、完成、考核 |
| `src/pages/training/dialogs.module.css` | 弹层与抽屉样式 |
| `src/content/copy.ts` | 新增 `training.*` |
| `src/app.tsx` / `app-shell.tsx` | 路由 `/training`，菜单从 `/soon` 转正 |
| `PAGE-MAP.md` | 新增 G32、G33 |

---

## 3. 四个标签

- **课程**：名称搜索、新建（`train:create`）、编辑（`train:edit`）、删除（`train:delete`）；列：课程 / 分类 / 难度 / 学时 / 讲师 / 关联试卷 / 操作。
- **缺口诊断**：选候选人（人才画像）+ 目标岗位 → 五维当前/目标/缺口/程度/推荐课程；结果可「生成培养计划」（周期 1-12 周 + 带教人）。
- **培养计划**：计划 / 对象 / 岗位 / 进度条 / 带教人 / 查看；抽屉里目标、阶段、任务；待开始任务可记录进度、完成，关联试卷的任务可考核。
- **成长台账**：选候选人看维度、变化、来源、说明；只读。

---

## 4. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次打开 / 切标签 | 表格骨架、抽屉骨架 |
| empty | 无课程 / 未诊断 / 无计划 / 无台账 | 各自空态 |
| error | CDP 拦截 `*training-courses*` | 「课程没取到。」+ 重试（`shots/training-error.png`） |
| no-permission | `emp_chen` | 「没有培训成长的权限」（`shots/training-403.png`） |
| over-limit | 课程 50/页、计划/台账 20/页 | 演示数据未触发分页；组件已接 |
| 无任务计划 | 旧计划 `task_total=0` | 进度列显示「暂无任务」 |

---

## 5. 真实数据

### 5.1 课程 5 门

```
大模型微调实战 / 算法 / 高阶 / 4 学时 / 李工 / 关联「综合能力测评（五维）」
产品需求分析方法 / 产品 / 进阶 / 2 学时 / 王经理
系统性能与可观测性 / 工程 / 进阶 / 3 学时 / 张工
跨团队协作与冲突管理 / 协作沟通 / 进阶 / 2 学时 / 王经理
复盘方法论与个人成长 / 成长 / 进阶 / 1 学时 / 李工
```

新建课程真实验证：UI 填「临时课程QA / 工程 / 1 学时」→ 保存成功、列表出现；随后用 `DELETE` 清理（id 6），列表回到 5 门。

### 5.2 诊断（陈宇 × 高级算法工程师）

| 维度 | 当前 | 目标 | 缺口 | 程度 | 推荐课程 |
|---|---:|---:|---:|---|---|
| 业务理解 | 32 | 70 | 38 | 高 | 产品需求分析方法 |
| 工程能力 | 59 | 85 | 26 | 高 | 系统性能与可观测性 |
| 技术深度 | 73 | 90 | 17 | 中 | 大模型微调实战 |
| 协作沟通 | 63 | 70 | 7 | 低 | 跨团队协作与冲突管理 |
| 成长性 | 74 | 70 | 0 | 已达标 | 复盘方法论与个人成长 |

### 5.3 计划 4 条

```
程磊 · AI 产品经理        0/3（本次 UI 真实生成，4 周，带教王工）
陈宇 · 高级算法工程师      3/3（100%；本次实测完成第 2 个任务）
张伟 · 高级算法工程师      1/2（50%）
陈宇岗前培养方案           暂无任务
```

抽屉真实任务：

| 任务 | 维度 | 状态 | 学时 | 进度 |
|---|---|---|---|---|
| 学习《产品需求分析方法》 | 业务理解 | 已完成 | 999/120 分钟 | 100% |
| 学习《系统性能与可观测性》 | 工程能力 | 待开始 → 已完成 | 0/180 → 200/180 | 0% → 100% |
| 学习《大模型微调实战》 | 技术深度 | 已完成 | 0/240 分钟 | 0% |

实测操作：打开抽屉 → 记录进度（200 分钟 / 100%）→ 完成 → 计划变为 3/3、任务按钮消失。另用 UI 走通「程磊 × AI 产品经理 → 生成计划（4 周 / 王工）」：新计划 12 生成，3 个任务、0/3。

### 5.4 台账（陈宇）

8 条记录，全部「技术深度 73→81 +8 / 课后考核」，时间 14:49–16:41。重复行是历史测试反复触发考核留下的，见 G33。

---

## 6. 权限

| 角色 | 实测 |
|---|---|
| admin | 200，全量 |
| hr_zhao | 200；`train:create/edit` 有，`train:delete` **没有** |
| pm_wang | 200，只读（无 create/edit/delete） |
| emp_chen | 403 |

---

## 7. 文案 key

| key 组 | 内容 |
|---|---|
| `training.title/sub/tabs` | 标题与四标签 |
| `training.difficulty/status/source/severity` | 枚举中文 |
| `training.courses.*` / `training.courseForm.*` | 课程表与表单 |
| `training.diagnose.*` | 诊断、生成计划 |
| `training.plans.*` | 计划列表、抽屉、任务、进度 |
| `training.ledger.*` | 台账 |
| `training.noPermission*` | 403 |

---

## 8. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入培训成长 | `page` |

不含候选人姓名、分数、课程内容。

---

## 9. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 155.93 kB gzip；CSS 16.23 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（119 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟） |
| 1440 课程 | 203 字，<13px 占 10%，无横向滚动，无 <24px 点击目标 |
| 1440 计划 | 211 字，<13px 占 29% |
| 768 | 无横向滚动；课程表隐藏讲师/关联试卷，诊断栏换行 |

---

## 10. 已知问题（不阻塞）

1. **G32 hr 没有 `train:delete`**：PAGE-MAP 写「hr 全权」，实际只有 admin 能删课程；前端按真实权限隐藏删除。
2. **G33 考核关联不校验 `exam_id`**：`assess_task` 只比考生姓名。前端只在「同候选人 + 同 `exam_id` 有提交」时才给考核入口；陈宇的任务关联试卷 2，但他没有这份卷的提交，因此考核入口显示「先去智能测评」。
3. **G33 任务数据不自洽**：《大模型微调实战》已完成但 0/240 分钟、0%；UI 原样展示，未改数据。
4. **G33 台账重复行**：同一考核 73→81 有 7 条重复记录，来自历史测试；UI 不聚合、不隐藏。
5. **无计划删除**：后端没有删除端点，页面不提供。
6. **已达标维度仍有推荐课程**：后端 `diagnose` 对五维都给 `recommended_courses`，UI 原样展示；是否只在缺口>0 时推荐需产品确认。
7. **390 未适配**（既定暂缓）。

---

## 11. 截图

| 文件 | 说明 |
|---|---|
| `shots/training-courses.png` | 1440×1100 课程（5 门） |
| `shots/training-course-dialog.png` | 新建课程弹窗 |
| `shots/training-diagnose.png` | 1440×1100 陈宇五维诊断 |
| `shots/training-generate.png` | 生成培养计划弹窗 |
| `shots/training-plans.png` | 1440×1100 计划列表（4 条） |
| `shots/training-generated.png` | UI 生成「程磊 × AI 产品经理」后的抽屉 |
| `shots/training-plan-drawer.png` | 计划抽屉（记录前进度 2/3） |
| `shots/training-plan-complete.png` | 记录进度 + 完成后 3/3、按钮消失 |
| `shots/training-ledger.png` | 陈宇成长台账 |
| `shots/training-light.png` | 浅色课程 |
| `shots/training-768.png` | 768 课程 |
| `shots/training-403.png` | 普通员工无权限 |
| `shots/training-error.png` | 课程请求失败 |
