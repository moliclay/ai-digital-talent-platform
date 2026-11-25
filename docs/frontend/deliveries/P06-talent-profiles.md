# P06 人才画像 · 交付说明

路由：`/talent-profiles`
日期：2026-11-03
页面任务：把简历与测评证据合成一张能解释的画像，决定怎么用这个人。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/talent-profiles.tsx` / `.module.css` | 卡片列表、搜索、生成入口、分页 |
| `src/pages/talent-profiles/types.ts` | 画像 / 测评证据 / 生成结果类型 + 数据源解析 |
| `src/pages/talent-profiles/generate-dialog.tsx` / `.css` | 生成范围、AI/测评开关 |
| `src/pages/talent-profiles/profile-drawer.tsx` / `.css` | 五维、优势/待验证/建议、标签、测评证据 |
| `src/components/ui/switch.tsx` / `.css` | 新原语 `Switch`（`role=switch`） |
| `src/content/copy.ts` | 新增 `talent.*`、`common.loading` |
| `src/app.tsx` / `app-shell.tsx` | 路由 `/talent-profiles`，菜单转为已实现 |
| `scripts/shot.mjs` | 新增 `--scrollSelector/--scrollTop`，用于抽屉内滚动截图 |
| `PAGE-MAP.md` | 新增 G19、G20 |

---

## 2. 页面结构

- 标题 + 口径；右上搜索（姓名/标签/画像标题）+「生成画像」。
- 卡片两列网格（不是三等分阵列）：头像 + 姓名 + 画像类型 + 来源徽标（AI 润色 / 规则生成）+ 两行摘要 + 五维条 + 标签 +「查看画像」。
- 生成对话框：生成范围（全部已解析简历 N 份 / 单份简历）+ 两个开关（AI 润色、测评证据）+ 说明。
- 画像抽屉：AI/规则说明、摘要、五维能力、优势、待验证、用人建议、标签、测评证据表（维度 / 简历 / 测评 / 合成 / 题 / 权重）。
- 12 张一页；>50 份时生成对话框提示「可能要点时间」。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首进 | 6 张卡片骨架（代码路径） |
| empty | 搜索「不存在」 | 「没有匹配的画像」+「没有找到「不存在」相关的画像。」+ 清空（`shots/talent-empty.png`）；真正 0 画像态后端无删除接口、演示库有 7 张，未实测，代码路径存在 |
| error | CDP 拦截 `*talent-profiles?*` | 「画像列表没取到。」+ 中文说明 + 重试（`shots/talent-error.png`） |
| no-permission | `emp_chen`（无 `talent:view`） | 「没有查看人才画像的权限」+ 中文说明（`shots/talent-403.png`） |
| over-limit | 一次 `generate` 处理全部可见已解析简历，无上限 | 对话框显示「全部已解析简历（8 份）」；>50 份提示是代码路径（演示库 8 份未触发） |

---

## 4. 真实数据

1. **列表**：7 张画像，两列卡片；来源徽标随 `data_sources` 的 `ai` 字段展示「AI 润色」/「规则生成」。
2. **生成（单份）**：用 UI 相同的 payload 对 `resume_id=8`（张测试）发 `POST /talent-profiles/generate`（`use_ai=false, use_exam=true`），返回 `total=1, created=1, ai_used=0, ai_available=true, exam_used=0`。列表随即出现「张测试 · 技术深度型」卡片，标「规则生成」，摘要为模板句。
3. **抽屉（有测评）**：张伟。五维 96/88/29/67/77；测评证据 `1 次提交 · 单维最多加权 30%`，五行：技术深度 简历 100 / 测评 87 / 合成 96 / 3 题 / 30% 等。
4. **抽屉（无测评）**：李娜。「这个候选人还没有测评证据。」（`shots/talent-drawer-noexam-bottom.png`）。
5. **生成对话框**：显示「全部已解析简历（8 份）」，与列表「共 7 张」是两个口径（已解析简历数 vs 已生成画像数），符合"生成覆盖全部已解析简历"。

生成未在页面上点「开始生成」提交（避免把 8 份全部重建、且会为重复简历多建画像，见 G20）；后端以同一 payload 实测通过。

---

## 5. 权限

| 角色 | 能做什么 |
|---|---|
| admin | 看、可生成（`talent:create`） |
| hr_zhao | 看、可生成 |
| pm_wang | 可看（`talent:view`），不可生成；后端列表不过滤范围，看到全平台 |
| emp_chen | 无 `talent:view`，403 |

生成按钮只在 `talent:create` 时渲染。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `talent.title/sub/generate/search*` | 标题、口径、生成、搜索 |
| `talent.count/filteredCount/clearSearch` | 计数与清空 |
| `talent.ruleBadge/aiBadge/view` | 来源徽标与查看 |
| `talent.empty*/loadError*/retry/noPermission*` | 空态 / 错误 / 权限 |
| `talent.generated/aiFallback/generateError` | 生成结果提示 |
| `talent.generateTitle/Desc/scope*/singleLimit/largeScope` | 生成对话框 |
| `talent.toggleAi/toggleExam` | 开关 |
| `talent.drawerTitle/Meta/dimsTitle/strengths/weaknesses/recommendation/tags/exam*` | 抽屉 |
| `talent.examColumns.*` | 测评证据表头 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入 | `page` |
| `talent_search` | 搜索提交 | `page`、`hasKeyword` |
| `talent_generate_open` | 打开生成 | `page` |
| `talent_generate_submit` | 提交生成 | `page`、`scope`、`use_ai`、`use_exam` |
| `talent_generate_done` | 生成成功 | `page`、`total`、`ai_used`、`exam_used` |
| `talent_generate_failed` | 生成失败 | `page`、`status` |

不含姓名、手机、邮箱、摘要正文。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 131.14 kB gzip；CSS 12.56 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（95 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟） |
| 1440 | 1331 字，<13px 占 36%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；单列卡片；搜索/生成换行正常 |
| 抽屉 | 六列测评表无横向溢出；`[role=dialog]` 内部滚动 |

---

## 9. 已知问题（不阻塞）

1. **G19：列表与详情不过滤数据范围。** hr/biz 看到全平台画像；前端按"平台画像库"口径展示，不写"本部门"。根治要后端给 `list_profiles` / `get_profile` 加范围参数。
2. **G20：同一人多份简历会生成多张画像。** `candidate_id` 是 `parsed_resumes.id`，同名不合并；前端原样展示，生成对话框已写"处理全部已解析简历"。
3. **生成对话框只打开、未提交。** 提交用同一 payload 走后端实测通过；全量生成会为重复简历多建画像，故不在演示库执行。
4. **真正的 0 画像空态未实测**：后端无删除画像接口，演示库有 7 张；搜索无结果态已覆盖。
5. **`meta/skills`（技能目录）未接入**：PAGE-MAP 列为技能筛选，本期卡片不做技能筛选，端点保留未用。
6. **抽屉需滚动**：摘要 + 五维 + 优势/待验证/建议 + 标签 + 测评表超过一屏，正文可滚动；顶部截图只到"标签"标题，底部截图可见标签与测评表。
7. **生成中无逐份进度**：一次返回汇总数，不做"3/8"进度条。
8. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/talent-1440.png` | 1440×900 列表 7 张，张测试标「规则生成」 |
| `shots/talent-1440-light.png` | 1440×900 浅色 |
| `shots/talent-768.png` | 768×1024 单列 |
| `shots/talent-generate.png` | 生成对话框（8 份 / 两个开关） |
| `shots/talent-drawer.png` / `-bottom.png` | 张伟抽屉（有测评证据，上/下） |
| `shots/talent-drawer-noexam.png` / `-bottom.png` | 李娜抽屉（无测评证据） |
| `shots/talent-empty.png` | 搜索无结果 |
| `shots/talent-error.png` | 列表请求失败 |
| `shots/talent-403.png` | 普通员工无权限 |
