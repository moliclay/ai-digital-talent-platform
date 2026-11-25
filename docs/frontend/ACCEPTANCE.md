# ACCEPTANCE · 什么叫做完了

版本 v0.1 · S1 产物 · 2026-11-03
适用对象：`mvp/frontend-v2` 新前端（Vite 7 + React 19 + TS 5.9 SPA）。旧前端 `mvp/frontend`、后端 `mvp/backend` 只读。
规则：每条都能勾选、都能复现；**没有原始输出的条目不算通过**，写"应该没问题"按未完成处理。

---

## A. 全站基线（每一页都必须成立）

- [ ] A1 全站只有一套 token 主题：`tokens.json` 三层（Primitive → Semantic → Component），含 light/dark 两套映射；页面不得出现第二套色板
- [ ] A2 零硬编码：源码无裸 hex/rgb、无 px（1px 描边与断点除外）、无 ms；`python3 <kit>/scripts/lint_hardcodes.py src` 退出码 0
- [ ] A3 零 emoji、零 em dash / en dash：`python3 <kit>/scripts/check_no_emoji.py src` 退出码 0
- [ ] A4 字体 ≤2 族，`font-display: swap`；正文 16px 起，行高 ≥1.45
- [ ] A5 正文对比度 ≥4.5:1，大字 ≥3:1，非文字对比 ≥3:1；`validate_contrast.py tokens.json` 全绿
- [ ] A6 键盘全程可用：Tab 顺序＝视觉顺序、焦点环可见（不得 `outline:none` 无替代）、Esc 关弹层并归还焦点、Modal 焦点陷阱＋`aria-modal="true"`
- [ ] A7 所有交互元素八态齐全：default / hover / focus / active / disabled / loading / error / selected
- [ ] A8 点击区 ≥24×24 CSS px（WCAG 2.5.8）；主操作 ≥44×44
- [ ] A9 `prefers-reduced-motion: reduce` 下动效停止且内容不丢
- [ ] A10 无原生 `<select>`：筛选/下拉一律 button + ARIA listbox/combobox，键盘等价（方向键、Home/End、Esc、typeahead）
- [ ] A11 无渐变主视觉、无玻璃拟态、无三等分卡片阵列、无 emoji 图标、无单边彩色描边
- [ ] A12 破坏性操作只用 `action.destructive`，且有二次确认（确认按钮也是 destructive）
- [ ] A13 页面边缘留白一致；无横向滚动（1440/768 本阶段；390 移动端适配 2026-11-03 暂缓）
- [ ] A14 主题切换：侧栏底部一个 32px 按钮，白天 / 黑夜两态；首访跟随系统、之后记忆；切换后刷新保持，首屏无闪烁；两套主题都过 A1–A5

---

## B. 每页 DoD（14 条路由逐一签）

对 P00–P13 每一页，以下 8 条全绿才算该页完成：

- [ ] B1 有且仅有一个 `h1`；每个区块有 `h2`；标题在 1440/768/390 都不超过 2 行
- [ ] B2 五态齐全且可手动触发：loading / empty / error / no-permission / over-limit，触发方式写进该页交付说明
- [ ] B3 越权走 `/403`：显示缺失权限码＋当前账号与角色＋返回可用首页
- [ ] B4 401 清 token 并跳 `/login?returnTo=`；登录后回到原路径
- [ ] B5 两宽度截图（1440/768）无重叠、无截断、无遮挡；390 移动端本阶段暂缓（2026-11-03）
- [ ] B6 文案全中文；标题不超 2 行；数字带单位；无"赋能/一站式/无缝/极致/重构认知"等空话
- [ ] B7 该页所有请求来自真实接口，字段与响应逐字段对齐（无编造字段、无 mock 残留）
- [ ] B8 埋点事件名与字段写进交付说明；姓名/手机/邮箱/简历正文不进埋点

页面清单（勾选即代表该页 B1–B8 全部通过）：
- [ ] P00 登录 `/login`
- [ ] P01 智能工作台 `/dashboard`
- [ ] P02 简历智能筛选 `/resumes`
- [ ] P03 岗位条件 `/job-profiles`
- [ ] P04 岗位匹配 `/matching`
- [ ] P05 匹配详情 `/matching/{id}`
- [ ] P06 人才画像 `/talent-profiles`
- [ ] P07 测评中心 `/exams`
- [ ] P08 答题 `/exams/{id}/take`
- [ ] P09 成绩与错题 `/exams/result/{sid}`
- [ ] P10 系统管理 `/system`
- [ ] P11 无权访问 `/403`
- [ ] P12 页面不存在 `/404`
- [ ] P13 里程碑空态 `/soon/{module}`

---

## C. 数据契约

- [ ] C1 未出现后端不存在的字段或接口；比对方式：实际响应 + `backend/app/api/*.py` 逐个核
- [ ] C2 分页统一 `{items,total,page,page_size}`，页大小 ≤200
- [ ] C3 后端硬编码上限在 UI 标注：最近操作 8 条、答卷 100 条、错题 200 条、复习计划 200 条、解析日志 20 条
- [ ] C4 数据范围口径与后端一致：简历/匹配/工作台按 dept/self；岗位/画像/测评为全量。UI 不写"本部门"除非接口真的过滤
- [ ] C5 AI 可缺席：`ai_available=false` 时页面明说"本次为规则生成"，不得隐藏
- [ ] C6 缺字段清单为零；有则写进 `RELEASE.md` 的"已知残留"，并列出问了谁

---

## D. 权限（用 4 个演示账号实测，每条留截图或接口返回）

- [ ] D1 `admin`：14 条路由全通；`/system` 三个标签可用
- [ ] D2 `hr_zhao`：岗位可增可改**不可删**；简历可传可改可删队列；匹配可执行；画像可生成；测评可建库建卷；`/system` → 403
- [ ] D3 `pm_wang`：`/resumes` → 403；不显示工作台菜单，直达 `/dashboard` 也 403；岗位/匹配/画像/测评只读；匹配"执行"可用（依据 seed 的 `match:create`，见 PAGE-MAP G5）
- [ ] D4 `emp_chen`：只有 `/dashboard`（self，空态）；其余 403；知识库进 `/soon/kb`
- [ ] D5 按钮级显隐读 `/api/auth/me` 的 `permissions`，前端不写死角色名
- [ ] D6 退出登录：token 清除、回 `/login`、浏览器后退不能回到业务页

---

## E. 门禁三连（必须真跑，贴原始输出）

- [ ] E1 `cd C:\Users\33051\.agents\ux-ui-agent-skills && node scripts\accuracy_report.mjs`，贴原始 `RESULT: N/N`
      > 说明：按你的指令跑，但它是这个 kit 的自检，测的是 kit 自身（`tests/`、`evals/`、`examples/`），不是本项目。结果照贴并注明口径，不能当本项目得分。
- [ ] E2 `node C:\Users\33051\.dsh\skills\design-taste-frontend\scripts\lint.mjs <frontend-v2/src>`：0 FAIL
- [ ] E3 `node C:\Users\33051\.dsh\skills\design-taste-frontend\scripts\inspect.mjs http://127.0.0.1:5174 --app`：1440/768/390 三档 0 FAIL（后台页必须 `--app`，否则房规不适用）
- [ ] E4 项目门禁（指向本项目源码，不是 kit）逐条贴输出：
      `validate_tokens.py tokens.json`、`validate_contrast.py tokens.json`、`lint_hardcodes.py src`、`check_no_emoji.py src`、`verify_states.mjs <page> --dark`、`axe_audit.mjs <page>`、`verify_keyboard.mjs src`、`verify_target_size.mjs src`、`verify_mobile_first.mjs src`、`verify_reduced_motion.mjs <page>`、`verify_overflow.mjs <page>`、`verify_spacing.mjs <page>`
- [ ] E5 axe 无 serious / critical；表单控件 100% 有可访问名称
- [ ] E6 任一 FAIL 的原文贴进 `GATE.md`，修完重跑，直到 0 FAIL；不得只贴修复后的结果

---

## F. 性能（测出来的，不是估的）

- [ ] F1 LCP < 2.5s（桌面 + Moto G4 模拟 / 4G）
- [ ] F2 CLS < 0.1
- [ ] F3 INP < 200ms
- [ ] F4 首屏 JS < 200KB gzip；路由级拆分，登录/工作台 ≤120KB
- [ ] F5 字体 ≤2 族、`font-display: swap`、无 FOIT
- [ ] F6 列表首屏 ≤20 行；翻页不引起整页重排
- [ ] F7 每页读数写进 `GATE.md`，注明测法与工具（Lighthouse / 自建脚本）

---

## G. 交付物齐全（缺一件按未交付）

- [ ] G1 `PAGE-MAP.md`
- [ ] G2 `ACCEPTANCE.md`
- [ ] G3 `tokens.json` + `DESIGN.md`（色彩角色、字阶、间距基数、圆角/阴影档位、八态、动效曲线与 reduced-motion 策略）
- [ ] G4 `COPY.md`（先文案 deck，后代码）
- [ ] G5 `COMPONENTS.md`（anatomy / variants / 八态 / token 映射 / ARIA 与键盘 / 最小点击区）
- [ ] G6 每页交付说明六件：文件清单、五态触发、权限缺省、文案 key、埋点事件与字段、自检读数
- [ ] G7 `GATE.md`（真实 N/N、每条 FAIL 原文、截图目录）
- [ ] G8 `REVIEW.md`（Blocking / Non-blocking 分栏，Blocking 清零）
- [ ] G9 `RELEASE.md`（完成度、门禁读数、已知残留、下一步建议）

---

## H. 不做的（验收时反查，违一条即返工）

- [ ] H1 后端无改动：`mvp/backend` 无 diff
- [ ] H2 旧前端无改动：`mvp/frontend` 无 diff
- [ ] H3 依赖未膨胀：`frontend-v2/package.json` 运行时只有 `react` / `react-dom` / `react-router-dom` / `@tanstack/react-query` / `lucide-react`；devDeps 只有 `vite` / `@vitejs/plugin-react` / `typescript` / 类型包
- [ ] H4 无 mock 残留：联调后 mock 文件删除，或明确标注 dev-only 且默认不加载
- [ ] H5 范围外模块只有空态：培训 / 数据决策 / 知识库 / Agent，不造假数据、不假按钮
- [ ] H6 未引入 i18n 库；文案集中在 `src/content/copy.ts`，key 用 `页面.区块.元素`
- [ ] H7 未引入原生 `<select>`、Tailwind 调色板工具类、任意 UI 组件库、图表库、toast 库

---

## I. 不算完成的样子（反例，写给评审看）

- "看着没问题""应该能过""已经符合最佳实践"：没有输出，视为没做
- 只有成功态截图，没有空态/错误态/403
- 越权直接白屏或跳首页，没有解释
- 只用颜色表达对错、状态、通过与否
- 空态用假数字、假图表、假头像填充
- 为了对齐设计稿改了后端字段或加了 mock 接口
- 把 8 个接口塞进一个巨型组件，页面能跑但没有五态与键盘模型

---

## J. 放行条件（Gate 到 S2 的开关）

同时满足才进入下一阶段：

1. 本文件 A 段（全站基线）在设计契约阶段可验证的条目全部有明确规则（A1–A5、A7、A10、A11、A12）。
2. `PAGE-MAP.md` 的 14 条路由、45 个接口、4 个角色、10 条契约缺口均已确认，没有"待补"空白。
3. 两个拍板项已确认（2026-11-03）：员工答题按"HR 代考代录"执行；系统管理纳入本期。技术栈已重定为 Vite 7 + React 19 + TS 5.9 SPA（见 `PAGE-MAP.md` §0.1）。
