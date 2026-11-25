# COMPONENTS · 组件契约

S4 产物 · 2026-11-03
方向：A · 值班仪表（1px 强调线做选中，面板比台面暗一档，数字等宽）。
实现期新增的容器类组件：`Panel`、`PageHeader`、`KpiStrip`、`ScoreBar`、`DataTable`、`Badge`、`EmptyState`、`ErrorState`、`Skeleton`、`AppShell`、`Modal`、`Drawer`、`Select`、`FileDrop`、`Pagination`、`Textarea`、`ConfirmDialog`。契约以本节后续条目为准，新增组件复用同一套 token。
令牌：`tokens.json` 426 个，`validate_tokens.py` 通过；组件只允许引用 `component.*` 与 `semantic.*`，不允许写死 hex / px / ms。

---

## 0. 六条实现原则

1. **一个原子只实现一次。** Button、Input、Modal 各只有一个实现；页面要新外观就加 variant，不许在页面里复制一份。
2. **八状态先写，再写默认态。** 每个交互组件在代码里必须能用 `data-state` 触发 default / hover / focus / active / disabled / loading / error / selected；不适用的状态在本文档里写明理由。
3. **焦点是功能。** 所有交互元素可 Tab 到达、焦点环可见（2px，offset 2）；弹层有焦点陷阱，Esc 关闭并把焦点还给触发元素。
4. **点击区下限。** 桌面最小 32×32，手机最小 44×44；WCAG 2.5.8 的 24×24 是底线，不是目标。
5. **状态不靠颜色单独表达。** 每个状态至少同时有文字、图标或形状差异。
6. **组件不读业务。** 组件只接收 props；接口调用、权限判断、文案 key 都在页面层，组件里不出现 `fetch`。

---

## 1. 组件清单

| 层 | 组件 | 文件 | 谁在用 |
|---|---|---|---|
| 原子 | Button | `ui/button.tsx` | 全站 |
| 原子 | IconButton | `ui/icon-button.tsx` | 主题切换、行操作、关闭 |
| 原子 | Input | `ui/input.tsx` | 登录、筛选、表单 |
| 原子 | Textarea | `ui/textarea.tsx` | 岗位说明、解析修正 |
| 原子 | Checkbox | `ui/checkbox.tsx` | 多选（题库、条件） |
| 原子 | Switch | `ui/switch.tsx` | 画像生成的两个开关 |
| 原子 | Select | `ui/select.tsx` | 岗位、学历、题库、分页大小 |
| 原子 | Badge | `ui/badge.tsx` | 状态、范围 |
| 原子 | Tag | `ui/tag.tsx` | 技能标签 |
| 原子 | Tabs | `ui/tabs.tsx` | 测评三区、系统三标签 |
| 原子 | ScoreBar | `ui/score-bar.tsx` | 匹配分数、阈值刻度 |
| 原子 | ProgressBar | `ui/progress-bar.tsx` | 解析进度、得分条 |
| 原子 | Skeleton | `ui/skeleton.tsx` | 所有加载态 |
| 原子 | Avatar | `ui/avatar.tsx` | 账户行、考生 |
| 原子 | Tooltip | `ui/tooltip.tsx` | 图标按钮说明 |
| 复合 | FormField | `ui/form-field.tsx` | 所有表单 |
| 复合 | PageHeader | `ui/page-header.tsx` | 每页标题行 |
| 复合 | FilterBar | `ui/filter-bar.tsx` | 列表页工具栏 |
| 复合 | KpiStrip | `ui/kpi-strip.tsx` | 工作台、匹配汇总 |
| 复合 | DataTable | `ui/data-table.tsx` | 所有表格 |
| 复合 | Pagination | `ui/pagination.tsx` | 全量列表 |
| 复合 | EmptyState | `ui/empty-state.tsx` | 所有空态 |
| 复合 | ErrorState | `ui/error-state.tsx` | 区块级错误 |
| 复合 | Toast | `ui/toast.tsx` | 全局轻提示 |
| 复合 | Dialog | `ui/dialog.tsx` | 弹窗原语 |
| 复合 | ConfirmDialog | `ui/confirm-dialog.tsx` | 破坏性 / 覆盖确认 |
| 复合 | Drawer | `ui/drawer.tsx` | 简历详情、画像详情 |
| 复合 | Dropzone | `ui/dropzone.tsx` | 简历上传 |
| 复合 | SidebarNav | `ui/sidebar-nav.tsx` | 全站外壳 |
| 复合 | ThemeToggle | `ui/theme-toggle.tsx` | 外壳底部 |
| 复合 | DimensionBars | `ui/dimension-bars.tsx` | 画像五维、匹配五维 |

---

## 2. 原子层

### 2.1 Button

**Anatomy**：`<button>` → 可选前置图标（16px）+ 文字（14/500）+ 可选后缀图标。
**Variants**：`primary` / `secondary` / `ghost` / `destructive`；`size` 只有 `md`（32px）与 `lg`（40px）；`fullWidth` 布尔。

| 状态 | 规则 | 令牌 |
|---|---|---|
| default | primary 近黑填充 / secondary 白底描边 / ghost 透明 / destructive 危险色填充 | `button.primary-bg` 等 |
| hover | 换一档底色，不位移、不加阴影 | `*-bg-hover` |
| focus | 2px 环，offset 2px | `border.focus` + `borderWidth.focus` |
| active | 再深一档 | `*-bg-active` |
| disabled | 底色 `surface.disabled`，文字 `text.disabled`，边框 `border.disabled`；保留可读 | `button.disabled-*` |
| loading | 文案不变或"处理中"，左侧 14px 旋转图标，宽度锁定，`aria-busy="true"`，重复点击被忽略 | `text.on-action` + `motion.easing.linear` |
| error | 不适用：提交失败由 FormField 或 ErrorState 承担，按钮回到可用态 | 无 |
| selected | 仅 toggle 型按钮（`aria-pressed`）：底色 `interactive.selected-bg`，文字加深 | `interactive.selected-*` |

**ARIA / 键盘**：原生 `button`；Enter 与 Space 都触发；`aria-pressed` 只在 toggle 型出现；`aria-busy` 只在 loading；不把 `div` 当按钮。
**最小点击区**：md 32×≥64；lg 40×≥72；图标型见 2.2。
**禁止**：用 primary 表达删除；用 disabled 隐藏权限（无权限应不出现在 DOM，或出现但带解释）。

### 2.2 IconButton 与 ThemeToggle

**Anatomy**：`<button>` + 单个 16px 图标；必须提供 `aria-label`，可选 `title` 与 Tooltip。
**Variants**：`ghost`（默认）/ `secondary`；`size` 32（桌面）/ 44（手机）。
**八状态**：同 Button；`selected` 用于主题按钮、视图切换。

**ThemeToggle 专规**：
- 图标显示**目标模式**：暗色显示太阳，亮色显示月亮；
- `aria-label` 与 `title` 同文："切换到白天" / "切换到黑夜"；
- 点击只切 `data-theme`，焦点留在按钮上；
- 位置：桌面侧栏底部账户行左侧，手机顶栏右侧。

**ARIA / 键盘**：原生 button；Enter/Space；Tooltip 用 `aria-describedby` 关联，不重复 label。
**最小点击区**：32×32 桌面；44×44 手机。

### 2.3 Input 与 Textarea

**Anatomy**：`<label>`（FormField 提供）+ `<input>` + 可选前置图标 + 可选后缀（清除、显示密码）+ 可选帮助/错误文字。
**Variants**：`text` / `search` / `number` / `password`；`size` md 32（工具栏）/ lg 40（表单）；`invalid`；`disabled`；`readOnly`。

| 状态 | 规则 | 令牌 |
|---|---|---|
| default | 1px 边框，白/深色面板底 | `input.border` |
| hover | 边框加深一档 | `input.border-hover` |
| focus | 边框换 `border.focus` + 2px 环 | `input.border-focus` |
| active | 不单独定义，等同 focus | 无 |
| disabled | 底色 `surface.disabled`，文字 `text.disabled`，光标 not-allowed | `input.bg-disabled` |
| loading | 异步校验中：尾部 14px 旋转图标，`aria-busy="true"`，不禁用输入 | `text.secondary` |
| error | 边框 `border.error` + 下方 12px 错误文字 + 图标 | `input.border-error` |
| selected | 不适用（输入框不是选择控件） | 无 |

**ARIA / 键盘**：原生 input；`:focus-visible`；`aria-invalid="true"` + `aria-describedby` 指向错误文字；错误文字 `role="alert"` 或 `aria-live="polite"`；密码可见按钮是独立 IconButton，`aria-pressed`。
**最小点击区**：高度 32/40，宽度随容器但不小于 120；点击 label 聚焦。
**Textarea**：`rows=3` 起，只允许纵向 resize；其余同 Input。

### 2.4 Checkbox 与 Switch

**Checkbox**
- Anatomy：20×20 方框 + 勾选图标 + 文字 label（点击整行切换）。
- 状态：default / hover（边框加深）/ focus（环）/ active（内缩 1px 的勾）/ disabled（底色禁用）/ loading 不适用 / error（边框错误色 + 文案）/ selected 即 checked，`indeterminate` 用短横。
- 令牌：`checkbox.*`。
- ARIA：原生 `<input type="checkbox">` 或 `role="checkbox"` + `aria-checked="mixed"`；Space 切换；label 用 `for` 关联。
- 点击区：20 方框，行高 32，label 整行可点。

**Switch**
- Anatomy：32×20 轨道 + 16px 圆点 + 文字 label。
- 状态：default / hover / focus / active（圆点 1px 位移）/ disabled / loading（圆点换成 12px 旋转图标）/ error（罕见，用文案说明）/ selected 即 on。
- 令牌：`switch.*`；on 色用 `action.primary`，不用品牌青（青只上数据）。
- ARIA：`role="switch"` + `aria-checked`；Space 切换；label 关联；不用 checkbox 伪装。
- 点击区：32×20，行高 32，整个 label 区可点。

### 2.5 Select（ARIA listbox，禁用原生 select）

**Anatomy**：`<button role="combobox">`（当前值 + 16px chevron，右侧内缩 10px）+ `<ul role="listbox">`（选项 32px 高）。
**Variants**：单选（默认）/ 多选（`aria-multiselectable`）；`size` 32/40；`invalid`；`disabled`。

| 状态 | 规则 | 令牌 |
|---|---|---|
| default | 1px 边框，chevron 灰 | `input.border` |
| hover | 边框加深 | `input.border-hover` |
| focus | 2px 环 | `border.focus` |
| active / open | chevron 旋转 180°，面板出现 | `shadow.menu` |
| disabled | 底色禁用，文字灰 | `surface.disabled` |
| loading | 选项加载中：面板内 3 行骨架，触发器 `aria-busy` | `skeleton.bg` |
| error | 边框错误色 + 文案 | `input.border-error` |
| selected | 选项行：底色 `interactive.selected-bg` + 右侧勾；触发器显示值 | `interactive.selected-*` |

**ARIA / 键盘**：
- 触发器 `aria-haspopup="listbox"`、`aria-expanded`、`aria-controls`；
- 打开：Enter / Space / ArrowDown / ArrowUp；
- 移动：ArrowUp/Down，Home/End，字母 typeahead；
- 提交：Enter；取消：Esc（关闭并把焦点还给触发器）；Tab 关闭并移到下一个控件；
- 焦点留在触发器，列表用 `aria-activedescendant` 指向高亮项；
- 选项 `role="option"` + `aria-selected`。
**最小点击区**：触发器高 32/40，选项行高 32，手机 44。
**禁止**：原生 `<select>`、`<datalist>`、自绘无键盘支持的下拉。

### 2.6 Badge 与 Tag

**Badge（状态）**
- Anatomy：12px 图标 + 11px 文字；高 20，圆角 4，左右 8。
- Variants：neutral / success / warning / error / info；不可点击。
- 状态：不适用（非交互）；颜色永远配文字，不单靠色。
- 令牌：`badge.*`。
- ARIA：普通 `<span>`；若状态会变化，外层加 `aria-live="polite"`。

**Tag（技能）**
- Anatomy：文字 + 可选 12px 移除按钮；高 24，圆角 4，底色 `surface.sunken`。
- 状态：default / hover（仅可移除时）/ focus（移除按钮）/ disabled / selected（筛选选中）/ 其余不适用。
- ARIA：静态标签用 `<span>`；可移除时移除按钮 `aria-label="移除 {技能}"`。

### 2.7 Tabs

**Anatomy**：`role="tablist"` + 每个 `role="tab"`（14/500）+ 2px 指示条 + 1px 底线 + `role="tabpanel"`。
**Variants**：`line`（默认）；`count` 可选（标签后 12px 数字）。
**八状态**：default / hover（文字加深）/ focus（环）/ active（按下）/ disabled / loading（内容区骨架，标签不转圈）/ error（内容区错误条）/ selected（指示条 + 文字加深 + `aria-selected`）。
**令牌**：`tabs.*`。
**ARIA / 键盘**：左右方向键切换并自动激活，Home/End 到首尾，Tab 离开 tablist；`aria-controls` 指向面板；面板 `tabindex="0"` 便于读到内容。
**最小点击区**：高 40，宽度 ≥ label + 24。

### 2.8 ScoreBar 与 ProgressBar

**ScoreBar（本产品的签名组件）**
- Anatomy：数值（24/600，tabular）+ 单位"分"（12 灰）+ 4px 轨道 + 填充（`data.series-1`）+ **阈值刻度**（2px 竖线，`text.primary`）+ 阈值文字（"合格线 70 分"）。
- Variants：`compact`（表格行内，只有条 + 数字）/ `full`（详情页，带阈值刻度与说明）。
- 八状态：default / hover（无变化，非交互）/ focus（不适用）/ active（不适用）/ disabled（灰条）/ loading（骨架条）/ error（数据缺失打灰色短横）/ selected（不适用）。
- 令牌：`score.*`。
- ARIA：`role="progressbar"` + `aria-valuenow/min/max` + `aria-valuetext="78 分，合格线 70 分，通过"`；阈值刻度 `aria-hidden`，文字已表达。
- 最小点击区：非交互，不适用。

**ProgressBar**：同结构，无阈值；用于上传与解析进度；`aria-valuetext` 写"第 3 份，共 12 份"。

### 2.9 Link、Avatar、Skeleton、Tooltip

| 组件 | Anatomy / Variants | 状态 | 令牌 | ARIA / 键盘 | 点击区 |
|---|---|---|---|---|---|
| Link | 文字 + 可选 12px 外链图标；`inline` / `standalone` | default / hover（下划线）/ focus（环）/ visited 不变 / disabled（不适用） | `text.link` / `link-hover` | 原生 `<a>`；Enter 激活；行内链接不受 24px 限制 | 行内随文字；独立链接高 32 |
| Avatar | 32px 圆形，首字；可选图片 | default / hover 不适用 / focus 不适用 / disabled 不适用 | `avatar.*` | `role="img"` + `aria-label="{姓名}"`；纯装饰时 `aria-hidden` | 不适用 |
| Skeleton | 平涂灰块，尺寸与真实内容一致；`text` / `block` / `circle` | 只有静态；容器 `aria-busy` | `skeleton.bg` | `aria-hidden="true"`；容器用 `aria-busy="true"` | 不适用 |
| Tooltip | 文本气泡，最大 240px，8px 偏移 | show / hide；延迟 300ms | `tooltip.*` | `role="tooltip"` + `aria-describedby`；Esc 关闭；不承载必读信息 | 不适用 |

---

## 3. 复合层

### 3.1 FormField

- Anatomy：label（14/500）+ 可选说明（12 灰）+ 控件 + 可选错误（12，红 + 图标）。
- Variants：`vertical`（默认，label 在上）/ `inline`（筛选栏）。
- 状态：由内部控件承担；FormField 只负责 `error` 与 `disabled` 的文案位置。
- ARIA：`label[for]`；说明与错误都进 `aria-describedby`；错误 `role="alert"`。
- 间距：label 到控件 8；控件到错误 6；字段之间 16。

### 3.2 PageHeader

- Anatomy：左侧 `h1`（24/600，名词）+ 可选一行说明（14 灰，≤2 行）；右侧动作区（最多一个 primary + 若干 secondary/ghost）。
- 状态：不适用。
- 令牌：`type.size.page`、`text.secondary`、`space.*`。
- ARIA：`<header>` + `h1`；动作区 `role="group"` + `aria-label="页面操作"`。
- 规则：每页一个 h1；右侧不放导出、分享这类没有接口的按钮。

### 3.3 FilterBar

- Anatomy：左侧搜索（280×32）+ 1-2 个 Select（160×32）+ 可选筛选 chip；右侧计数（"共 128 条"）+ 刷新 IconButton。
- 状态：default / loading（右侧刷新转圈）/ disabled（无数据时刷新禁用）。
- ARIA：`<form role="search">`；搜索有 label（可视觉隐藏）；刷新按钮 `aria-label="刷新列表"`。
- 手机：搜索整行，筛选收进一枚"筛选"按钮 + 底部抽屉；页面不横滚。

### 3.4 KpiStrip

- Anatomy：一个容器，1px 分隔线切成 4 格；每格 label（12 灰）+ value（24/600 tabular）+ 单位（12 灰）。
- Variants：4 格 / 3 格 / 2 格（手机 2 列）；`muted` 用于零值。
- 状态：default / loading（4 条等宽骨架）/ empty（零值正常打印 0）/ error（整条 ErrorState 替代）。
- 令牌：`kpi.*`。
- ARIA：`<dl>` + `dt/dd`；数值与单位在同一个 `dd` 里。
- 禁止：KPI 上放图标、迷你折线、彩色底、增长胶囊。

### 3.5 DataTable 与 Pagination

**DataTable**
- Anatomy：容器（`surface.card`，1px 边，圆角 8）→ `<table>` → `caption`（视觉隐藏，说明这张表是什么）→ `thead`（40px，12px 灰，句首大写）→ `tbody`（行 48px，1px 规则线）→ 末行 Pagination。
- Variants：`dense`（44px 行，系统日志）/ `comfortable`（48px）；`selectable`（仅批量操作存在时）；`sortable`。
- 八状态（行）：default / hover（`table.row-hover`）/ focus-within（行内控件聚焦时整行描边）/ active（不适用）/ disabled（不适用）/ loading（10 行骨架）/ error（表体替换为 ErrorState，表头保留）/ selected（`table.row-selected`）。
- 令牌：`table.*`。
- ARIA：原生 table；`th scope="col"`；排序列 `aria-sort` + 表头内 button；`caption` 视觉隐藏；数字列 `class="num"` 右对齐 + tabular。
- 手机：640px 以下转两行式列表（第一行姓名 + 关键数字，第二行其余字段 13px 灰），字段不丢；确实要横滚时只滚表体。
- 禁止：斑马纹、表头色带、大写字母间距、每行都放头像与 kebab。

**Pagination**
- Anatomy：左"第 1–20 条，共 128 条"；右上一页 / 下一页 IconButton（32）。
- 状态：default / hover / focus / disabled（首末页）/ loading（翻页中按钮转圈）。
- ARIA：`<nav aria-label="分页">`；当前范围用 `aria-live="polite"` 更新。
- 规则：概览列表不翻页，用"查看全部"；全量列表必须显示总数与当前范围。

### 3.6 EmptyState 与 ErrorState

**EmptyState**
- Anatomy：1px 虚线框（`border.default`，圆角 8，内边距 32）+ 一句现状 + 一句下一步 + 可选一个次按钮；跨整行（`grid-column: 1 / -1`）。
- 状态：只有静态；不可用图标大插画。
- ARIA：`role="status"`；按钮是真的按钮。

**ErrorState**
- Anatomy：16px 错误图标 + 一句"什么失败" + 后端 message（12 灰）+ 重试按钮；区块内替换内容，不做全屏横幅。
- 状态：default / retrying（按钮 loading）。
- ARIA：`role="alert"`；重试按钮可键盘触发。

### 3.7 Toast

- Anatomy：右下角容器（`role="region"`，`aria-live="polite"`）；每条：状态图标 16 + 文字 14 + 关闭 IconButton；宽 420，圆角 8，边框 + 阴影。
- Variants：success / error / info；error 用 `role="alert"`，其余 polite。
- 状态：enter（220ms，opacity + 8px 位移；reduced 时无位移）/ exit（140ms）/ hover 暂停计时 / focus 暂停 / 最多 3 条，超出排队。
- 令牌：`toast.*`。
- ARIA：不抢焦点；关闭按钮可 Tab 到；6 秒自动消失，悬停与聚焦时暂停。
- 禁止：用 toast 承担表单字段错误；用 toast 说"系统繁忙"。

### 3.8 Dialog（Modal 原语，全站唯一）

- Anatomy：overlay（`surface.overlay`）→ 面板（`dialog.bg`，1px 边，圆角 8，阴影，`max-width` 480 / 640，内边距 24）→ 标题（18/600）+ 描述（14 灰）+ 内容 + 底部动作（右对齐，最多一个 primary）。
- Variants：`sm`（480，确认类）/ `md`（640，表单类）；`dismissible`（点遮罩关闭，默认 true；确认类 false）。
- 状态：closed / opening / open / closing / loading（确认按钮转圈，面板不转）/ error（面板内 ErrorState）。
- 令牌：`dialog.*`、`z.dialog`。
- **ARIA 与焦点（硬要求）**：
  - `role="dialog"`、`aria-modal="true"`、`aria-labelledby` 指向标题、`aria-describedby` 指向描述；
  - 打开时焦点落到首个可聚焦控件（或面板本身 `tabindex="-1"`，用于纯文本确认）；
  - Tab / Shift+Tab 在面板内循环，焦点不跑到背景；
  - Esc 关闭（除非 `dismissible=false` 且有未保存内容，此时先确认）；
  - 关闭后焦点**归还触发元素**；
  - 背景滚动锁定，补偿滚动条宽度，页面不跳。
- 最小点击区：底部按钮 40 高；关闭按钮 32。
- 禁止：每页手搓弹窗；嵌套 Dialog（需要两层时改成 Drawer + Dialog）。

### 3.9 ConfirmDialog

- 基于 Dialog 的组合；标题是动词短语（"删除岗位条件"），正文写对象与后果，按钮是"取消 + 动词"。
- 破坏性确认：焦点默认落在**取消**；确认按钮 `destructive`；遮罩点击不关闭。
- 覆盖类确认（重新匹配）：焦点默认落在取消；确认按钮用 primary，文案是"重新匹配"。
- `aria-describedby` 必须指向后果说明，不能只靠视觉。

### 3.10 Drawer

- Anatomy：右侧滑出，宽 480（手机 100%）；头部 56（标题 + 关闭）+ 可滚动内容 + 可选底部动作区。
- 状态：同 Dialog；`loading` 用内容区骨架；`error` 用区块 ErrorState。
- 令牌：`drawer.*`、`z.dialog`。
- ARIA / 焦点：同 Dialog；Esc 关闭；焦点归还触发元素；抽屉内第一个可聚焦元素获得焦点。
- 规则：详情优先用 Drawer，不新开页面；一个抽屉内不再叠对话框，除非是确认。

### 3.11 Dropzone

- Anatomy：1px 虚线框（`dropzone.border`，圆角 8，内边距 32）+ 一句主文案 + 一句限制说明 + "选择文件"次按钮 + 已选文件列表（文件名 14 + 大小 12 灰 + 移除 IconButton）。
- 状态：default / drag-over（边框换 `dropzone.active-border`，底色不变）/ focus（环）/ disabled / uploading（每行进度条）/ error（逐条原因，红字 + 图标）/ selected 不适用。
- ARIA：隐藏的 `<input type="file" multiple>` 由按钮触发；按钮 `aria-label="选择简历文件"`；文件列表 `role="list"`；上传结果 `aria-live="polite"`。
- 限制：单个 ≤10 MB，一次 ≤20 份（前端策略，界面写明）。

### 3.12 SidebarNav 与外壳

- Anatomy：品牌区（标记 + "人才平台" + 副标）→ 工作域行（部门 · 范围）→ 导航列表（7 项，高 32）→ 底部（ThemeToggle + 账户行 + 退出）。
- 状态（导航项）：default / hover（文字加深）/ focus（环）/ active（按下）/ disabled（不适用）/ loading（不适用）/ error（不适用）/ selected（文字 `item-text-active` + 1px 强调线贴在行的左内边，线高与文字同高）。
- 令牌：`nav.*`、`shell.*`、`layout.sidebar`。
- ARIA：`<nav aria-label="主导航">`；当前项 `aria-current="page"`；图标 `aria-hidden`；每个链接有可见文字。
- 手机：≤640px 折叠为 48px 顶栏 + 全屏抽屉；导航项 44 高。
- 规则：分组标签用句首大写 12px 灰；计数只出现在需要处理的队列上，并带名词。

### 3.13 DimensionBars

- Anatomy：5 行，每行：维度名（14）+ 数值（14 tabular，右对齐）+ 4px 条。
- 状态：default / loading（5 行骨架）/ error（整块 ErrorState）；非交互。
- 令牌：`score.bar-height`、`data.series-1`、`surface.sunken`。
- ARIA：用 `<dl>` 或表格；数值必须可读，条是 `aria-hidden`；不画雷达图（五维用横条更易读）。

---

## 4. 八状态矩阵

| 组件 | default | hover | focus | active | disabled | loading | error | selected |
|---|---|---|---|---|---|---|---|---|
| Button | 有 | 有 | 有 | 有 | 有 | 有 | 不适用（由 FormField/ErrorState 承担） | toggle 型有 |
| IconButton | 有 | 有 | 有 | 有 | 有 | 有 | 不适用 | 有 |
| Input | 有 | 有 | 有 | 等同 focus | 有 | 有 | 有 | 不适用 |
| Textarea | 有 | 有 | 有 | 等同 focus | 有 | 不适用 | 有 | 不适用 |
| Checkbox | 有 | 有 | 有 | 有 | 有 | 不适用 | 有 | checked / mixed |
| Switch | 有 | 有 | 有 | 有 | 有 | 有 | 有 | on |
| Select | 有 | 有 | 有 | open | 有 | 有 | 有 | 选项有 |
| Badge / Tag | 有 | 可移除时有 | 移除按钮有 | 不适用 | 有 | 不适用 | 不适用 | 筛选选中 |
| Tabs | 有 | 有 | 有 | 有 | 有 | 内容区骨架 | 内容区错误条 | 有 |
| ScoreBar | 有 | 不适用 | 不适用 | 不适用 | 灰条 | 骨架 | 灰短横 | 不适用 |
| Table 行 | 有 | 有 | focus-within | 不适用 | 不适用 | 骨架 | 区块错误 | 有 |
| Dialog | closed/open | 内部控件 | 陷阱内 | 内部控件 | 内部控件 | 确认按钮 | 面板内错误 | 不适用 |
| Drawer | closed/open | 内部控件 | 陷阱内 | 内部控件 | 内部控件 | 内容骨架 | 区块错误 | 不适用 |
| Toast | 有 | 暂停 | 暂停 | 不适用 | 不适用 | 不适用 | error 变体 | 不适用 |
| Dropzone | 有 | 有 | 有 | drag-over | 有 | uploading | 有 | 不适用 |

---

## 5. 键盘模型总表

| 场景 | 按键 | 行为 |
|---|---|---|
| 全局 | Tab / Shift+Tab | 按视觉顺序移动焦点；首项前有"跳到主内容"链接 |
| 全局 | Esc | 关闭最上层弹层（Dialog / Drawer / Select / Tooltip），焦点归还触发元素 |
| Button | Enter / Space | 触发 |
| Checkbox | Space | 切换 |
| Switch | Space | 切换 |
| Select | Enter / Space / ArrowDown | 打开 |
| Select | ArrowUp / ArrowDown / Home / End / 字母 | 移动高亮 |
| Select | Enter | 选中并关闭 |
| Select | Esc | 关闭并归还焦点 |
| Tabs | Left / Right / Home / End | 切换标签（自动激活） |
| Tabs | Tab | 离开 tablist 进入面板 |
| Dialog / Drawer | Tab / Shift+Tab | 在面板内循环 |
| Table | Enter / Space | 触发表头排序或行内动作 |
| Pagination | Enter / Space | 翻页 |
| Dropzone | Enter / Space | 打开文件选择器 |

---

## 6. 焦点与层级

| 层 | z-index 令牌 | 说明 |
|---|---|---|
| 页面 | `z.base` | 普通内容 |
| 侧栏 | `z.nav` | 不遮挡内容 |
| 下拉 | `z.dropdown` | Select、菜单 |
| 遮罩 | `z.overlay` | Dialog / Drawer 背景 |
| 弹层 | `z.dialog` | Dialog / Drawer 面板 |
| 提示 | `z.toast` | 永远在最上 |

焦点规则：
- 焦点环 2px，offset 2，颜色 `border.focus`；在深色与浅色下都要 ≥3:1。
- 弹层打开时背景内容 `aria-hidden="true"` + `inert`，键盘与读屏都进不去。
- 关闭后焦点回到触发元素；触发元素不存在时回到页面 `h1`（`tabindex="-1"`）。
- 不用 `outline: none` 除非同时给出等价的可见替代。

---

## 7. 禁止清单

1. 页面里手搓第二套 Button / Input / Modal。
2. 原生 `<select>`、`<datalist>`、无键盘支持的自绘下拉。
3. 用 `div` + `onClick` 当按钮。
4. 卡片同时有边框和阴影；静置卡片有阴影。
5. 表头色带、斑马纹、大写字母间距。
6. KPI 上的图标、迷你折线、彩色底块。
7. 只用颜色表达状态（通过 / 未通过、错误、选中）。
8. 禁用态用 30% 透明度导致文字低于 4.5:1。
9. 用 toast 承担字段级错误。
10. 在组件里写死 `#hex`、`px`、`ms`；在组件里 `fetch` 接口。

---

## 8. 实现约定

| 项 | 约定 |
|---|---|
| 目录 | `src/components/ui/<component>.tsx` + `<component>.module.css` |
| 导出 | 具名导出；每个文件一个主组件；类型与组件同文件 |
| 样式 | CSS Modules + `var(--token)`；不引 Tailwind，不写行内颜色 |
| 状态 | 用 `data-state="hover|focus|..."` 与 CSS 属性选择器，便于测试与截图 |
| 变体 | `variant` / `size` / `tone` 三个 props 封顶，不堆布尔 |
| 图标 | lucide-react，16px，`currentColor`，`aria-hidden`（有文字时） |
| 受控 | 表单组件一律受控；Dialog / Drawer 用 `open` + `onOpenChange` |
| 测试钩子 | `data-testid` 只加在页面级容器，不给每个原子加 |
| 文档 | 每个组件文件顶部注释：anatomy、状态、键盘、令牌 |

---

## 9. S5 实现顺序

1. `tokens.css` 生成 + 全局基础样式（reset、字体、焦点环、skip link）
2. Button / IconButton / Input / Textarea / FormField
3. Select（listbox）
4. Badge / Tag / Tabs / Avatar
5. Skeleton / EmptyState / ErrorState
6. DataTable / Pagination / FilterBar
7. KpiStrip / PageHeader / ScoreBar / DimensionBars
8. Toast / Dialog / ConfirmDialog / Drawer
9. Dropzone / SidebarNav / ThemeToggle
10. 页面装配：登录 → 工作台 → 简历 → 岗位 → 匹配 → 详情 → 画像 → 测评 → 答题 → 成绩 → 系统 → 异常页

每完成一个组件，先在单独的 harness 页过一遍八状态与键盘，再进页面；页面里不允许出现"临时样式"。
