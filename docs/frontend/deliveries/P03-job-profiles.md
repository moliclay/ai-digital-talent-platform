# P03 岗位条件 · 交付说明

路由：`/job-profiles`
日期：2026-11-03
页面任务：定义「这个岗位到底要什么」，并当场知道条件会不会太严。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/job-profiles.tsx` / `.module.css` | 列表、搜索、分页、权限动作、删除确认 |
| `src/pages/job-profiles/types.ts` | 岗位 / 条件 / 试算结果类型 |
| `src/pages/job-profiles/editor-dialog.tsx` / `.css` | 新建 / 编辑：基本信息、硬条件行、权重、合格线、能力基线 |
| `src/pages/job-profiles/trial-dialog.tsx` / `.css` | 试算结果：扫描 / 过线 / 不过 / 平均分 / 合格线、五档分布、前五 |
| `src/components/ui/modal.tsx` / `.css` | 新增 `lg` 尺寸（880），两栏编辑器用 |
| `src/content/copy.ts` | 新增 `jobProfiles.*` |
| `src/app.tsx` / `src/components/app-shell.tsx` | 路由 `/job-profiles`、菜单改为已实现 |
| `tokens.json` | 新增 `primitive.scale.size.880`、`component.dialog.width-lg`（426 个令牌） |

---

## 2. 页面结构

- 标题 + 口径 + 右上「新建岗位条件」。
- 列表：搜索岗位名、7 列（岗位 / 硬条件 / 权重 / 合格线 / 状态 / 创建时间 / 操作）。
- 岗位名是链接：HR 点名字直接进编辑；只读账号是普通文本。
- 硬条件列只显示第一条 + 「另有 N 条」，完整内容在 `title` 与编辑器里。
- 权重列：五段条 + 最高项百分比 + 「共 5 项」；悬停显示完整五项。
- 操作：`试算`、`编辑`（`job:edit`）；`删除`（仅 `job:delete`，hr 默认没有）。
- 编辑器：880 宽两栏。左栏硬条件，右栏权重 + 合计 + 合格线 + 能力基线；底部固定取消 / 保存。
- 试算：结果只读展示，不落库。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次列表 / 打开编辑 | 列表 6 行骨架；编辑器骨架 |
| empty | 搜索「不存在」 | 「没有匹配的岗位」+ 清空；计数「筛选结果 0 个」（`shots/jobs-empty.png`） |
| error | CDP 拦截 `*job-profiles?*` | 「岗位列表没取到。」+「没连上服务，稍后再试。」+ 重试（`shots/jobs-error.png`） |
| no-permission | `emp_chen` 直接访问（无 `job:view`） | 「没有查看岗位条件的权限 / 需要 job:view」（`shots/jobs-403.png`） |
| over-limit | 硬条件行上限 20（前端策略）；权重合计 ≠ 1.00 时保存被拦 | 20 行按钮禁用与权重校验是代码路径，本轮没有逐条点到 20 行；权重校验在读数为 1.00 时通过（`shots/jobs-editor.png` 的「合计 1.00」） |

权限缺省：

- `job:view` 才有页面；`emp_chen` 403。
- `job:create` 才有「新建」；`job:edit` 才有「试算 / 编辑」；`job:delete` 才有「删除」。
- `pm_wang` 有 `job:view`，列表只读，没有操作列。
- 删除是软删（`status=deleted`），列表接口过滤 deleted。

---

## 4. 文案 key

| key 组 | 内容 |
|---|---|
| `jobProfiles.title/sub/listTitle/create` | 岗位条件 / 口径 / 岗位列表 / 新建岗位条件 |
| `jobProfiles.columns.*` | 岗位 / 硬条件 / 权重 / 合格线 / 状态 / 创建时间 / 操作 |
| `jobProfiles.conditionMore(n)` | 另有 N 条 |
| `jobProfiles.weightTop/weightMore` | 最高 {维度} {n}% / 共 5 项 |
| `jobProfiles.empty*/loadError*/noPermission*` | 空态与错误态 |
| `jobProfiles.editor.*` | 基本信息、硬条件、权重、合计、合格线、能力基线、校验与保存 |
| `jobProfiles.trial.*` | 扫描 / 过线 / 不过 / 平均分 / 合格线 / 五档分布 / 分数前五 |
| `jobProfiles.remove.*` | 删除确认与结果 |

---

## 5. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入岗位页 | `page: "job-profiles"` |
| `job_editor_open` | 新建 / 编辑 | `page`、`mode` |
| `job_saved` | 保存成功 | `page`、`mode` |
| `job_trial_open` | 打开试算 | `page` |
| `job_deleted` | 删除成功 | `page` |

不含岗位说明全文、候选人姓名。

---

## 6. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 119.78 kB gzip；CSS 10.20 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（82 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟） |
| 1440 列表 | 195 字，<13px 占 37%，无横向滚动，无 <24px 点击目标 |
| 768 列表 | 无横向滚动；隐藏权重/状态/创建/操作，保留岗位/硬条件/合格线 |
| 编辑器 | 880×~820 两栏，五项能力基线一行显示，底部无遮挡 |
| 对比度 | 沿用 S2 两套主题全部 required 通过 |

真实动作：

1. **试算**：打开「高级算法工程师(AI平台部)」的试算，返回 `scanned=8 / passed=2 / failed=6 / avg=45.4 / threshold=70`，五档 `5/1/0/2/0`，前五含张伟 85、陈宇 81（`shots/jobs-trial.png`）。
2. **保存链路**：用 UI 相同的 payload（中文条件 key、技能数组、年限数字、权重小数、能力基线）对 job 3 发 `PUT /api/job-profiles/3`，返回 `code=0`，字段回读一致。没有在页面上点保存，避免覆盖演示数据。
3. **权重读取**：种子权重是 30/30/30/10 的整数，编辑器按比例归一化为 0.30/0.30/0.30/0.10，合计 1.00；保存时把已有的 `ability` 座位原样带回。

---

## 7. 已知问题（不阻塞）

1. **G13：没有 `updated_at`。** 列表用「创建时间」，不伪造更新时间。
2. **G14：后端只判学历、技能、工作年限。** 专业/城市虽在白名单但不参与硬条件，编辑器不提供，避免假开关。
3. **G15：PRD 的「五维权重」写的是画像维度**（技术深度等），后端权重键是 education/skills/experience/project/other/ability。编辑器按后端键渲染，画像五维放在「能力基线」。
4. **不同岗位的权重键数量不同。** 种子岗位有 4 个键（含 ability），新建默认 5 个；编辑器按实际键展示并归一化，不强行补齐。
5. **权重取整**：显示两位小数并归一化，合计允许 ±0.01；保存后由后端再归一化。
6. **试算只针对已保存岗位**，不支持“未保存草稿试算”。
7. **删除是软删**，没有恢复入口；只有 admin 有 `job:delete`。
8. **768 隐藏操作列**：编辑入口是岗位名链接；试算/删除在 768 不可用。
9. **390 未适配**（2026-11-03 决定暂缓），本轮不验收。

---

## 8. 截图

| 文件 | 说明 |
|---|---|
| `shots/jobs-1440.png` | 1440×900 暗色列表 |
| `shots/jobs-1440-light.png` | 1440×900 浅色列表 |
| `shots/jobs-768.png` | 768×1024 精简列 |
| `shots/jobs-editor.png` | 编辑对话框（两栏、合计 1.00、五项基线） |
| `shots/jobs-trial.png` | 试算结果（8 份 / 2 过 / 6 不过 / 五档 / 前五） |
| `shots/jobs-empty.png` | 搜索无结果 |
| `shots/jobs-error.png` | 列表请求失败 |
| `shots/jobs-403.png` | 普通员工无 job:view |
