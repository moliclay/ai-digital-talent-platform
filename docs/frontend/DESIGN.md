# DESIGN · 设计契约

版本 v0.2 · Corporate Trust 重构 · 2026-11-03
配套文件：`tokens.json`（唯一令牌源，**494 个令牌**，`validate_tokens.py` 已通过）
适用范围：`mvp/frontend-v2` 全部 14 条路由。旧前端 `mvp/frontend` 不适用本契约。

> **当前状态（2026-11-03）**：按 `Enterprise-设计说明.md` 做 Corporate Trust 全站重构。全站强制浅色，旧深色值班仪表主题已下线；本文件 §1–§8 中关于深色默认、青色强调的段落是 v0.1 存档，实际以 `semantic.*` + `semantic.enterprise.*` 令牌为准。

---

## 0. 三条不可协商的前提

1. **全站一套主题。** 颜色、字阶、间距、圆角、阴影、动效只从 `tokens.json` 来；页面不得自带色板，也不得在组件里写 `#hex`、`px`、`ms`。
2. **强调色克制。** 唯一品牌相是 Indigo（`#4F46E5`）+ Violet（`#7C3AED`），只出现在主操作、选中态、焦点环、数据强调与品牌标记；数据页面不使用大面积渐变或发光。
3. **浅色是唯一主题。** Corporate Trust 全站浅色；`index.html` 固定 `data-theme="light"`，主题切换按钮已下线。`dark` 令牌保留在 `tokens.json` 里但不再启用。

---

## 1. 色彩角色

### 1.1 表面与文字（暗色为默认呈现，浅色同构）

| 角色 | 令牌 | 浅色 | 暗色 | 实测对比 |
|---|---|---|---|---|
| 页面底 | `surface.page` | `#f7f8f8` | `#191d20` | 与文字 16.77:1 / 15.38:1 |
| 卡片（比底更暗） | `surface.card` | `#ffffff` | `#121517` | 与文字 17.84:1 / 16.62:1 |
| 抬升面（浮层、菜单、悬停） | `surface.raised` | `#f2f4f5` | `#23282c` | 次要文字 6.34:1 / 7.53:1 |
| 凹陷面（骨架、进度轨道） | `surface.sunken` | `#eceef0` | `#08090a` | 不承载正文 |
| 正文 | `text.primary` | `#14181c` | `#f2f4f5` | 16.77:1 / 15.38:1 |
| 次要文字 | `text.secondary` | `#525a63` | `#b4b9bf` | 6.58:1 / 8.59:1 |
| 元信息、占位符 | `text.tertiary` | `#6a717a` | `#8b929a` | 4.64:1 / 5.39:1 |
| 链接 | `text.link` | `#0a6a8c` | `#5cd4f5` | 5.72:1 / 9.85:1 |
| 控件边界 | `border.strong` | `#6a717a` | `#6a717a` | 4.64:1 / 3.44:1（需 ≥3:1） |
| 装饰分隔 | `border.default` | `#dcdfe3` | `#2a3036` | 1.26:1 / 1.27:1（按定义不承担识别） |

暗色采用方向 A 的抬升模型：**卡片比页面底更暗一档**（台面 #191d20，面板 #121517），浮层与悬停面再亮一档（#23282c）。表头不使用 `surface.raised` 作底色，避免出现"表头色带"；表头只靠 12px 灰字与 1px 规则线。

亮色是同一模型的反向映射：白卡放在 `#f7f8f8` 台面上，卡片比底亮一档。两套都只用"一档底色差 + 1px 描边"分层，不同时上阴影。

> 上面两列 hex 只用于阅读。实现里只允许 `var(--text-primary)` 这类引用；`tokens.json` 是唯一写死值的地方。

### 1.2 操作色

| 角色 | 令牌 | 浅色 | 暗色 | 说明 |
|---|---|---|---|---|
| 主操作 | `action.primary` | `#14181c` | `#f2f4f5` | 近黑填充 / 反白填充，文字用 `text.on-action` |
| 主操作悬停 | `action.primary-hover` | `#24292f` | `#c2c7cd` | 只变底色，不变尺寸 |
| 主操作按下 | `action.primary-active` | `#0b0d0f` | `#c2c7cd` | 与 hover 相差一档 |
| 次操作 | `action.secondary` | `#ffffff` | `#1d2226` | 带 `border.strong` 描边 |
| 破坏操作 | `action.destructive` | `#b02f34` | `#c8404f` | 触发按钮与确认框都用它，不许借用主操作色 |

破坏性语义只有一套：删除岗位、清除解析队列、任何不可撤销动作。文案里要写清对象与后果，确认框主按钮用 `destructive`。

### 1.3 状态色

| 语义 | 底 | 文字 | 图标 | 用法 |
|---|---|---|---|---|
| 成功 | `feedback.success-bg` | `feedback.success-text` | `feedback.success-icon` | 解析完成、匹配通过 |
| 警告 | `feedback.warning-bg` | `feedback.warning-text` | `feedback.warning-icon` | AI 不可用、条件偏严 |
| 错误 | `feedback.error-bg` | `feedback.error-text` | `feedback.error-icon` | 请求失败、校验不通过 |
| 信息 | `feedback.info-bg` | `feedback.info-text` | `feedback.info-icon` | 口径说明、里程碑提示 |

四种状态都必须"图标 + 文字"，不允许只靠颜色；同一行最多一个状态标记。

### 1.4 数据色

| 角色 | 令牌 | 用法 |
|---|---|---|
| 主数据 | `data.series-1` | 分数条、趋势线、当前周期；浅色 `#0a6a8c`，暗色 `#35c2f2` |
| 对照数据 | `data.series-2` | 一律中性灰，不引入第二个色相 |
| 网格 / 轴 | `data.grid` / `data.axis` | 3–5 条淡网格，无 y 轴线 |
| 区间底色 | `data.span` | 浅青 12% / 14% |
| 正负 | `data.positive` / `data.negative` | 只用于"好坏"，不用于"涨跌" |

一屏最多 4 个色相；同一对象在所有图里用同一色；单序列图表不画图例。

---

## 2. 字阶

中文系统字体栈，0 个 webfont，因此没有 FOIT/FOUT，也不需要 `font-display`。等宽只用于 ID、接口路径与代码块，不用于正文。

| 角色 | 令牌 | 字号 / 行高 / 字重 | 用在哪 |
|---|---|---|---|
| 展示 | `type.size.display` | 32 / 1.2 / 600 | 只给登录页标题，应用内不超过 32 |
| 页面标题 | `type.size.page` | 24 / 1.25 / 600 | 每页唯一 `h1`，名词标题 |
| 区块标题 | `type.size.section` | 18 / 1.35 / 600 | 卡片组、页面分区 |
| 卡片标题 | `type.size.card` | 16 / 1.45 / 600 | 面板标题、抽屉标题 |
| 阅读正文 | `type.size.read` | 16 / 1.45 / 400 | 画像摘要、简历原文、空态长句 |
| 正文 | `type.size.body` | 14 / 1.45 / 400 | 表格单元、表单、导航 |
| 元信息 | `type.size.meta` | 12 / 1.4 / 400 | 表头、时间、单位 |
| 徽章下限 | `type.size.micro` | 11 / 1.4 / 500 | 只用于状态徽章，正文禁用 |

规则：

- 一屏使用 4–7 个字号；不使用 13/15/17/20/22 这类中间档。
- 字重只有 400 / 500 / 600；700 不用。
- 所有数字 `font-variant-numeric: tabular-nums`，表格数值右对齐，单位用小一号灰色后缀。
- 标题左对齐；只有登录页允许居中一次。

---

## 3. 间距与版式

基数 4px，`semantic.space` 只暴露这些档位：2 / 4 / 8 / 12 / 16 / 20 / 24 / 32 / 40 / 48 / 64。

| 位置 | 令牌 | 值 |
|---|---|---|
| 页边距（桌面 / 手机） | `layout.page-gutter` / `layout.phone-gutter` | 24 / 16 |
| 卡片内边距 | `layout.card-pad` | 20 |
| 卡片间距 | `layout.card-gap` | 16 |
| 区块间距 | `layout.section-gap` | 32 |
| 控件高度（工具栏） | `layout.control-height` | 32 |
| 表单控件高度 | `layout.form-height` | 40 |
| 表格行高 | `layout.row-height` | 48 |
| 侧栏宽度 | `layout.sidebar` | 232 |
| 顶栏高度 | `layout.topbar-height` | 48 |

版式规则：

- 一屏一个左边缘、一个右边缘；卡片不短于网格右边界。
- 手机是基础层：默认样式即手机，`min-width` 向上叠加；侧栏在 640px 以下折叠为顶栏 + 全屏抽屉。
- 表格在 640px 以下转两行式列表，字段不丢；确实要横滚时只滚表格自身，页面不横滚。
- 概览类列表最多 4–6 行 + "查看全部"；全量列表才分页，并显示"第 1–20 条，共 N 条"。

---

## 4. 圆角与阴影

| 档位 | 令牌 | 值 | 用在哪 |
|---|---|---|---|
| 徽章 | `radius.chip` | 4 | 状态徽章、标签 |
| 控件 | `radius.control` | 6 | 按钮、输入框、下拉触发器 |
| 面板 | `radius.card` | 8 | 卡片、表格容器、抽屉、对话框 |
| 胶囊 | `radius.pill` | 999 | 头像、分段控件 |

只有三档可见圆角（4/6/8），不用 12px 统一圆角；嵌套圆角不再递减出第四档。

| 阴影 | 令牌 | 用在哪 |
|---|---|---|
| 无 | `shadow.none` | 所有静置卡片：用 1px 描边或一档底色分层，禁止"描边 + 阴影"同时出现 |
| 菜单 | `shadow.menu` | 下拉、弹出菜单 |
| 对话框 | `shadow.dialog` | 对话框、抽屉 |
| 提示条 | `shadow.toast` | 右下角通知 |

---

## 5. 八状态规范

每个交互元素都要有这八种状态；不适用的状态在组件契约里写明"不适用"，不能默默缺省。

| 状态 | 视觉规则 | 令牌映射 | 可访问性要求 |
|---|---|---|---|
| default | 静置 | 组件 token | 控件边界 ≥3:1 |
| hover | 底色变一档或叠加 5% 遮罩；不位移、不放大 | `action.*-hover` / `interactive.hover-overlay` | 悬停不是唯一反馈 |
| focus | 2px 焦点环，offset 2px；环色 `border.focus` | `borderWidth.focus` | 键盘可见；不得 `outline:none` 无替代 |
| active | 再深一档，或 9% 遮罩 | `action.*-active` / `interactive.active-overlay` | 按下有即时反馈 |
| disabled | 底色 `surface.disabled`，文字 `text.disabled`，边框 `border.disabled` | 同名组件 token | 仍可读（≥4.5:1），并说明为什么禁用 |
| loading | 内容不塌：按钮保留原宽，文字换"处理中"或加 16px 旋转图标；区块用骨架 | `skeleton.bg` | `aria-busy="true"`，禁用重复提交 |
| error | 只标出错的那一项：边框 `border.error` + 一条错误文案 | `input.border-error` | 文案用 `aria-live`，不弹全局红色横幅 |
| selected | 中性底 `interactive.selected-bg` + 文字加深；不叠加彩色描边 | `interactive.*` | 同时有 `aria-selected` / `aria-current` |

补充约定：

- 按钮没有 error 态；提交失败用错误提示条 + 按钮回到可点。
- 输入框的 loading 是异步校验（如用户名查重），用尾部 14px 图标 + `aria-busy`。
- 表格行的 selected 用整行底色，不用左侧色条；行内操作在 hover 与 focus-within 时出现，不能只在 hover 出现。
- 禁用态不能只靠 30% 透明度；透明度会让文字低于 4.5:1。

---

## 6. 动效

| 令牌 | 值 | 用途 |
|---|---|---|
| `motion.duration.fast` | 90ms | hover、focus、按下 |
| `motion.duration.base` | 140ms | 下拉展开、选中切换 |
| `motion.duration.slow` | 220ms | 抽屉、对话框、Toast 进出 |
| `motion.easing.enter` | `cubic-bezier(0, 0, 0.2, 1)` | 进场 |
| `motion.easing.exit` | `cubic-bezier(0.4, 0, 1, 1)` | 退场 |
| `motion.easing.standard` | `cubic-bezier(0.2, 0, 0, 1)` | 原地状态变化 |

规则：

- 后台页面**没有入场动画**：标题、卡片、表格不随滚动淡入。动效只做反馈：hover、focus、按下、弹层开合、Toast 进出、行插入。
- 只动 `transform` 与 `opacity`；不动 `width/height/top/left`，避免重排。
- `prefers-reduced-motion: reduce` 时：所有 duration 归 0，位移与缩放全部取消，只保留 opacity 的 0→1；弹层直接出现，内容不丢。
- 不使用 shimmer 骨架屏；骨架是平涂灰块，尺寸与真实内容一致，数据到达不跳版。

---

## 7. 令牌到 CSS 变量的映射

命名规则固定，不允许自己发明：

| 令牌路径 | CSS 变量 |
|---|---|
| `semantic.text.primary` | `--text-primary` |
| `semantic.surface.card` | `--surface-card` |
| `semantic.action.destructive` | `--action-destructive` |
| `semantic.border.strong` | `--border-strong` |
| `semantic.space.md` | `--space-md` |
| `semantic.radius.control` | `--radius-control` |
| `semantic.motion.duration.base` | `--motion-base` |
| `semantic.type.size.page` | `--font-page` |
| `component.button.primary-bg` | `--button-primary-bg` |

生成与覆盖规则：

1. 由 `tokens.json` 生成一份 `src/styles/tokens.css`，全局只导入一次。
2. 浅色写在 `:root`，暗色写在 `:root[data-theme="dark"]`，只覆盖 `semantic.*` 的颜色变量。
3. **组件令牌必须写成 `var(--text-on-action)` 这样的引用**，不能在构建时解析成固定 hex，否则切主题不生效。
4. 页面样式只允许 `var(--...)`；`px` 只允许出现在 1px 描边与媒体查询断点里，`ms` 只允许出现在 tokens.css。
5. 新增令牌的流程：primitive → semantic → component 三层补齐，跑 `validate_tokens.py` 与 `validate_contrast.py`，不允许只加 component 层。

---

## 8. 与旧前端的关系

| 项 | 旧前端 | 新契约 | 原因 |
|---|---|---|---|
| 页面底 | `#070c13`（偏蓝黑） | `#191d20`（中性深灰台面），卡片再暗一档 `#121517` | 后台设计规则禁止 navy/slate 深色主题；方向 A 的 move 是"面板比底更暗" |
| 强调色 | `#35c2f2`，出现在按钮与图标 | `#35c2f2` 只保留为暗色数据色 `data.series-1` | 强调色上数据，不上 chrome |
| 主按钮 | 青色填充 | 近黑填充 / 暗色反白 | 12/23 个真实后台没有任何填充主按钮；有也是近黑 |
| 圆角 | 混用 | 4 / 6 / 8 三档 | 三档以内，避免"全站 12px"的模板感 |
| 阴影 | 卡片带阴影 | 静置无阴影，靠描边/底色 | 卡片阴影是生成式后台的第一大特征 |

旧前端的 CSS 不复用；只复用它的业务流程与交互结论（见 `PAGE-MAP.md`）。

---

## 8.5 主题切换（白天 / 黑夜）

产品默认暗色，但两套主题都是可用的正式状态，不是演示开关。

| 项 | 规则 |
|---|---|
| 位置 | 桌面：侧栏底部账户行左侧；手机：顶栏右侧、菜单按钮左边 |
| 控件 | 32×32 图标按钮，ghost 样式，1.5px 线性图标；不用开关滑块，不用下拉 |
| 图标 | 显示**目标模式**：当前暗色显示太阳，当前亮色显示月亮 |
| 文案 | `aria-label` 与 `title` 一致：当前暗色时为"切换到白天"，当前亮色时为"切换到黑夜" |
| 首访 | 读 `localStorage["tl.theme"]`；没有记录时跟随 `prefers-color-scheme`；系统也没有偏好时用暗色 |
| 持久化 | 每次切换写入 `localStorage["tl.theme"]`（`light` / `dark`），只记本机，不写后端 |
| 应用方式 | `data-theme` 挂在 `<html>` 上，`tokens.css` 里 `:root[data-theme="dark"]` 覆盖语义颜色；组件令牌用 `var()` 跟随 |
| 防闪烁 | `index.html` 里一段内联脚本在首屏 CSS 之前设置 `data-theme`；不允许先亮后暗 |
| 切换行为 | 只改属性，不重挂载路由、不丢表单输入、不重置滚动位置 |
| 键盘与焦点 | Tab 可达，焦点环可见；切换后焦点留在按钮上 |
| 验收 | 两套主题都过 A1–A5；切换后刷新保持；三种初始状态（有记录 / 无记录跟随系统 / 无记录无系统偏好）各截一张图 |

不做三态（跟随系统 / 白天 / 黑夜）：用户只要求一个按钮，三态会让按钮语义变复杂；"跟随系统"只作为首访默认值存在。

---

## 9. 已知约束与风险

1. **浅色主题是映射，不是产品承诺。** 演示与验收以暗色为主；浅色要能过对比度与布局检查，但不单独做视觉打磨。
2. **没有 webfont。** 中文系统字体在 Windows 是微软雅黑，macOS 是苹方，字形宽度略有差异；所有宽度相关的断言按最宽的一档留余量。
3. **S3 可能换色相。** 若视觉方向选中别的强调色，只允许替换 `primitive.color.cyan.*` 这一组值，语义路径与组件映射不动，并重跑两个校验脚本。
4. **等宽字体只用于 ID 与代码。** 表格数字用 `tabular-nums`，不切等宽，避免"代码感"泄漏到正文。

---

## 10. S2 门禁原始输出

`python3 C:\Users\33051\.agents\ux-ui-agent-skills\scripts\validate_tokens.py tokens.json`

```
Parsed 1/1 token files, 426 tokens defined.

OK: all token files valid JSON.
exit=0
```

`python3 C:\Users\33051\.agents\ux-ui-agent-skills\scripts\validate_contrast.py tokens.json`

```
=== LIGHT (required) ===
  PASS body text on page: 16.77:1 (need 4.5)  [#14181c on #f7f8f8]
  PASS body text on card: 17.84:1 (need 4.5)  [#14181c on #ffffff]
  PASS secondary text on page: 6.58:1 (need 4.5)  [#525a63 on #f7f8f8]
  PASS link on page: 5.72:1 (need 4.5)  [#0a6a8c on #f7f8f8]
  PASS text on primary action: 17.84:1 (need 4.5)  [#ffffff on #14181c]
  PASS essential control border (WCAG 1.4.11): 4.64:1 (need 3.0)  [#6a717a on #f7f8f8]

=== DARK (required) ===
  PASS body text on page: 15.38:1 (need 4.5)  [#f2f4f5 on #191d20]
  PASS body text on card: 16.62:1 (need 4.5)  [#f2f4f5 on #121517]
  PASS secondary text on page: 8.59:1 (need 4.5)  [#b4b9bf on #191d20]
  PASS link on page: 9.85:1 (need 4.5)  [#5cd4f5 on #191d20]
  PASS text on primary action: 17.65:1 (need 4.5)  [#0b0d0f on #f2f4f5]
  PASS essential control border (WCAG 1.4.11): 3.44:1 (need 3.0)  [#6a717a on #191d20]

=== LIGHT (advisory) ===
  ok tertiary/incidental text on page: 4.64:1 (need 4.5)  [#6a717a on #f7f8f8]
  ok secondary text on raised surface: 6.34:1 (need 4.5)  [#525a63 on #f2f4f5]
  warn default border on page (decorative): 1.26:1 (need 3.0)  [#dcdfe3 on #f7f8f8]

=== DARK (advisory) ===
  ok tertiary/incidental text on page: 5.39:1 (need 4.5)  [#8b929a on #191d20]
  ok secondary text on raised surface: 7.53:1 (need 4.5)  [#b4b9bf on #23282c]
  warn default border on page (decorative): 1.27:1 (need 3.0)  [#2a3036 on #191d20]

OK: all required contrast pairs pass WCAG 2.2 minimums.
exit=0
```

两条 warning 是装饰性分隔线低于 3:1，按定义不承担控件识别，保留；所有承担识别功能的边界走 `border.strong`（4.64:1 / 3.95:1）。
