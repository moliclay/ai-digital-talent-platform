# P05 匹配详情 · 交付说明

路由：`/matching/:id`（从 P04 名单点姓名进入，链接带 `?job=<id>`）
日期：2026-11-03
页面任务：回答"为什么是这个分、为什么过/没过"，并给出可核对的原始依据。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/match-detail.tsx` / `.module.css` | 结论、硬条件、评分构成、候选人信息、能力基线、技能命中、简历原文 |
| `src/pages/matching.tsx` / `.module.css` | 姓名改成链接，带 `?job=` 进入详情；新增 `viewDetail` 文案 |
| `src/content/copy.ts` | 新增 `matchDetail.*` |
| `src/app.tsx` | 路由 `/matching/:id` |
| `scripts/shot.mjs` | 截图指标增加 `overflow` 元素清单，便于定位横向溢出 |
| `PAGE-MAP.md` | 新增 G17、G18 |

---

## 2. 页面结构

- 标题：`{姓名} · 匹配详情`；副标题：岗位名 · 附件名。
- 右上：`返回名单`（按 `?job=` 回到对应岗位名单）、`下载简历`（带 Bearer 取 blob）。
- 人工修正提示：`manually_fixed=true` 时置顶黄条，明确"修正后没重跑匹配，分数仍是修正前的"。
- 左栏：
  1. **结论**：最终得分 + 合格线条 + 结论徽标 + 后端 `reason` 原文；硬条件失败时加"按基础分 55% 折算并压在合格线下"的说明。
  2. **硬条件逐条判定**：条件 / 实际 / 要求 / 结论；实际值按学历、年限、技能从档案取，要求值按后端条件渲染。
  3. **评分构成**：维度 / 得分 / 权重 / 贡献，底部"基础分"与"最终分"两行；权重为 0 的维度不占行，用一行脚注说明。
- 右栏：
  1. **候选人信息**：学历、专业、年限、手机、邮箱、附件、档案来源。
  2. **能力基线**：基线 / 实际 / 达成率；未设基线或没画像各有独立说明。
  3. **技能命中**：要求技能逐项标命中/未命中，带图标与 `aria-label`。
  4. **简历原文**：默认 120 字预览 + `展开全文`；展开后限高滚动，键盘可聚焦滚动。
- 768：单栏，顺序为结论 → 硬条件 → 评分 → 信息 → 能力 → 技能 → 原文；表格不横向溢出。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 直接打开详情 | 标题下 3 段骨架（代码路径，未截静态图） |
| empty / 404 | `/matching/999999` | 「匹配记录不存在」+「可能已经被重新匹配覆盖。回名单重新选一条。」+ 返回（`shots/match-detail-404.png`） |
| error | CDP 拦截 `*matching/219*` | 「这条匹配没取到。」+「没连上服务，稍后再试。」+ 重试（`shots/match-detail-error.png`） |
| no-permission | `pm_wang` 打开 219（部门范围不符） | 「看不了这条匹配记录」+ 范围/权限说明 + 返回（`shots/match-detail-403.png`）；`emp_chen` 无 `match:view`，接口 403 同页 |
| over-limit | 本页无输入与数量上限；超长原文用预览 + 展开滚动 | 不适用；长文不做一次性全展开 |

补充：

- `pm_wang` 的 403 来自行级数据范围（`无权访问该匹配记录`），不是权限码缺失；页面统一用中文说明，不透出后端权限码。
- `emp_chen` 的 403 是 `无权限：match:view`；同一个页面承接两种 403，文案不区分技术原因。

---

## 4. 真实数据

| 场景 | 记录 | 结果 |
|---|---|---|
| 通过 | 219 张伟 | 85.0 分 / 合格线 70 / 通过；基础分 84.8，最终 85.0；画像契合 100×10%；硬条件三条全过 |
| 未通过（硬条件失败） | 218 刘洋 | 29.0 分 / 未通过；基础分 53.4，×55% = 29.37 → 29；学历（本科 < 硕士）与技能（未命中 PyTorch）两条失败；黄条提示折算规则 |
| 能力基线 | 219 | 工程能力 85→88（100%）、技术深度 90→96（100%）；达成率按基线封顶 |
| 技能命中 | 219 | 3 / 5：PyTorch、Python、大模型命中；机器学习、深度学习未命中 |
| 下载 | 219 | `GET /api/resumes/file/...pdf` 带 Bearer 返回 `200 application/pdf`，文件 3,121 字节 |
| 人工修正 | 演示库 8 条 | 全部 `manually_fixed=false`，黄条是代码路径，未实测 |

分数口径：

- 贡献 = 维度得分 × 权重；四项贡献合计 84.8，取整得到最终 85.0。
- 硬条件失败：最终分 = min(round(基础分 × 0.55), 合格线 − 1)，所以 53.4 → 29.37 → 29。

---

## 5. 文案 key

| key 组 | 内容 |
|---|---|
| `matchDetail.title/sub/back/download/downloadError` | 标题、副标、返回、下载 |
| `matchDetail.conclusion/scoreLabel/scoreUnit` | 结论、最终得分、单位 |
| `matchDetail.hardTitle/hardMeta/noConditions/conditionColumns/op/ok/fail` | 硬条件表与运算符 |
| `matchDetail.scoringTitle/scoringMeta/scoringColumns/base/final/zeroWeight` | 评分构成与脚注 |
| `matchDetail.skillsTitle/skillsMeta/noSkills/hitLabel/missingLabel` | 技能命中 |
| `matchDetail.infoTitle/info.*/years/sourceManual/sourceParsed` | 候选人信息 |
| `matchDetail.manualFixed` | 人工修正提示 |
| `matchDetail.abilityTitle/abilityMeta/abilityNone/abilityNoProfile/abilityColumns` | 能力基线 |
| `matchDetail.resumeTitle/resumeMeta/resumeEmpty/expand/collapse` | 简历原文 |
| `matchDetail.notFound*/forbidden*/loadError*/retry` | 404 / 403 / 错误 |

---

## 6. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入详情（含 403/404，用于统计入口量） | `page: "match-detail"` |

不含姓名、手机、邮箱、简历正文、匹配 id。

---

## 7. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 126.36 kB gzip；CSS 11.36 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（86 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟） |
| 1440×1200 | 926 字，<13px 占 19%，无横向滚动，无 <24px 点击目标；整页高 1200，无纵向滚动 |
| 768×1200 | 736 字，<13px 占 24%，无横向滚动；单栏顺序正常 |
| 溢出检查 | 修复前 768 有两列表格溢出 8px；改为 ≤900px 单栏后 `scrollWidth == clientWidth` |

---

## 8. 已知问题（不阻塞）

1. **G17：详情不返回 `job_profile_id`。** 返回名单依赖链接上的 `?job=`；直接打开无参数会回未筛选名单。
2. **G18：没有测评证据。** 详情 `detail` 只有硬条件、五维评分、能力基线；COPY 里的"测评证据"没有数据源，留到 P06/P07。
3. **403 文案统一**：不区分"数据范围不符"和"缺权限码"，避免把内部权限码暴露给业务用户。
4. **硬条件 `ok` 由后端按 key 子串匹配失败项生成**：同一岗位出现两个同 key 条件时可能误判；前端不改写后端结论。
5. **简历原文只预览 120 字**：展开后限高滚动；不在首屏一次性渲染全文。
6. **手机、邮箱明文展示**：匹配查看权限内可见；埋点不带 PII。
7. **人工修正黄条未实测**：演示库没有 `manually_fixed=true` 的档案。
8. **768 仍保留固定侧栏**（移动端适配既定暂缓），主区约 488px。
9. **下载依赖附件存在**：没有附件时只显示附件名，不渲染下载按钮。

---

## 9. 截图

| 文件 | 说明 |
|---|---|
| `shots/match-detail-1440.png` | 1440×1200 通过案例（张伟） |
| `shots/match-detail-fail.png` | 1440×900 硬条件失败（刘洋，含 55% 折算提示） |
| `shots/match-detail-light.png` | 1440×1200 浅色 |
| `shots/match-detail-768.png` | 768×1200 单栏 |
| `shots/match-detail-403.png` | 业务负责人跨部门 403 |
| `shots/match-detail-404.png` | 记录不存在 |
| `shots/match-detail-error.png` | 请求失败 |
