# P14 空缺预警 · 交付说明

路由：`/vacancy`
日期：2026-11-03
页面任务：哪个岗位要招、缺几人、储备池里谁最接近。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/vacancy.tsx` / `.module.css` | KPI、岗位预警卡、储备池、预警口径 |
| `src/components/app-shell.tsx` | 新增「空缺预警」菜单项（前端合成，后端菜单表没有该路径） |
| `src/content/copy.ts` | 新增 `vacancy.*` |
| `src/app.tsx` | 路由 `/vacancy` |
| `PAGE-MAP.md` | 新增 G30 |

**菜单说明**：后端 `/auth/me` 的菜单表没有 `/vacancy`，页面只对 `job:view` 角色显示；`AppShell` 在 `GROUPS` 里合成这一项，不让它落到 `/soon`。

---

## 2. 页面结构

- 标题 + 口径。
- KPI：在招岗位 / 有空缺岗位 / 空缺合计 / 高预警（有高预警时附「需优先补人」）。
- 左栏「岗位预警」：按 high → medium → low → none 排序；每张卡是按钮，显示岗位名、等级徽标（图标 + 文字）、名额 / 已通过 / 空缺、合格线 / 通过率；选中卡有品牌色描边。
- 右栏「储备池」：跟随选中岗位，两段
  - 接近合格线：候选人 / 分数 / 差多少 / 卡在哪；姓名按 `parsed_resume_id` join `/matching/lists` 得到匹配 id 后链到 `/matching/:id?job=...`。
  - 画像达标未投递：候选人 / 画像能力（按岗位基线维度展示）。
  - 两段都为空 → 「这个岗位暂时没有储备人选。」
- 右栏底部「预警口径」：高 / 中 / 低 / 正常的判定规则 + 通过率分母说明。
- 口径小字：「空缺 = 名额 − 已通过。」

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 直接打开 | 3 张卡骨架 + 面板骨架（代码路径） |
| empty | 没有 active 岗位 | 「还没有在招岗位。」（代码路径） |
| error | CDP 拦截 `*job-profiles/alerts*` | 「预警没取到。」+ 重试（`shots/vacancy-error.png`） |
| no-permission | `emp_chen`（无 `job:view`） | 「没有查看预警的权限」（`shots/vacancy-403.png`） |
| over-limit | 储备池后端无分页、无 limit | 全量展示；不截断、不伪造分页（G30） |
| 无预警 | 所有岗位 `alert=none` | 「当前没有岗位缺人。」绿色提示条（代码路径） |
| 储备为空 | 接近线与画像池都为空 | 实际命中：清理后算法岗储备池为空 |

---

## 4. 真实数据

### 4.1 清理临时岗位后的最终状态

```
在招岗位 2 个 / 有空缺 1 个 / 空缺合计 1 人 / 高预警 0 个

高级算法工程师(AI平台部)  low   名额 3  已通过 2  空缺 1  合格线 70  通过率 33.3%
AI 产品经理              none  名额 2  已通过 2  空缺 0  合格线 65  通过率 33.3%

储备池（算法岗）：接近线 0 人，画像达标未投递 0 人 → 空态
```

### 4.2 为覆盖四级预警临时造的 QA 数据（已删除）

| 临时岗位 | id | 等级 | 名额 | 通过 | 空缺 | 合格线 | 储备池 |
|---|---|---|---|---|---|---|---|
| 储备验证(临时) | 6 | high | 2 | 0 | 2 | 98 | 接近线：张伟 96（差 2）、陈宇 93（差 5） |
| 中预警验证(临时) | 7 | medium | 3 | 1 | 2 | 95 | 接近线：陈宇 93（差 2） |
| 储备池验证(临时) | 8 | high | 2 | 0 | 2 | 80 | 画像达标未投递：张伟（工程 88 / 技术 96）、程磊（工程 100 / 技术 94） |

截图完成后 `DELETE /job-profiles/{6,7,8}`，`alerts` 回到 2 个岗位；这 3 个岗位的匹配行留在库里但不再被 active 查询使用。

---

## 5. 权限

| 角色 | 能看 |
|---|---|
| admin / hr_zhao / pm_wang | 可看（`job:view`） |
| emp_chen | 403 |

`pm_wang` 只读（没有 `job:create`，页面本来也没有写操作）。

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `vacancy.title/sub` | 标题与口径 |
| `vacancy.kpi.*` | 四个 KPI + 单位 + 高预警提示 |
| `vacancy.level.*` | 高 / 中 / 低 / 正常 |
| `vacancy.card.*` | 名额 / 已匹配 / 已通过 / 空缺 / 合格线 / 通过率 |
| `vacancy.reserveTitle/reserveMeta` | 储备池标题与接近线 |
| `vacancy.near*` / `qualified*` | 两段表头与说明 |
| `vacancy.blockedHard/scoreBelow` | 「卡在哪」的兜底 |
| `vacancy.legend*` / `passRateNote` | 预警口径与通过率分母 |
| `vacancy.*Empty/loadError*/noPermission*` | 空态与错误 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入空缺预警 | `page` |

不含候选人姓名、分数。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 145.49 kB gzip；CSS 15.07 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（111 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟） |
| 1440（QA 五岗位） | 498 字，<13px 占 38%，无横向滚动，无 <24px 点击目标 |
| 1440（最终两岗位） | 296 字，<13px 占 42%，无横向滚动，无 <24px 点击目标 |
| 768 | 无横向滚动；预警卡单列，储备池与口径在下方 |

---

## 9. 已知问题（不阻塞）

1. **G23 仍未补**：P03 编辑器没有「名额」字段，只能读后端 seed 的 `headcount`；新建岗位默认名额由后端给。P14 已按 G23 直接读 `headcount`。
2. **G30 无分页**：`reserve` 全量返回，`alerts` 全量返回；演示 8 份简历不构成问题，数据量上来要后端补 limit。
3. **储备行链接是前端 join**：用 `/matching/lists?job_profile_id=X&page_size=200` 把 `parsed_resume_id` 映射到匹配 id；超过 200 条时部分行退化为纯文本。
4. **画像达标未投递无详情入口**：没有 `parsed_resume_id` 对应的简历路由，只展示能力值。
5. **通过率分母是「已匹配」**：不是名额，卡片小字 + 口径卡都写明，避免把 2/6 误读成招满。
6. **「卡在哪」只有硬条件/缺技能/总分三类**：后端 `fail_items` / `missing_skills` 为空时统一显示「总分未达合格线」。
7. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/vacancy-levels.png` | 1440×1300 四级预警 + 接近线（临时 QA 数据） |
| `shots/vacancy-1440.png` | 1440×1000 清理后的真实两岗位 + 储备池空态 |
| `shots/vacancy-qualified.png` | 1440×1200 画像达标未投递（张伟 / 程磊） |
| `shots/vacancy-light.png` | 1440×1300 浅色 |
| `shots/vacancy-768.png` | 768×1400 单列 |
| `shots/vacancy-403.png` | 普通员工无权限 |
| `shots/vacancy-error.png` | 预警请求失败 |
