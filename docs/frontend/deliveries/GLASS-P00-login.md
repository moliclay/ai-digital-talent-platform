# Glass Admin P00 登录页 · 改造交付

参考：
- `glass-admin-prompt.md`：三层深度、单一左上方光源、玻璃配方
- `glass-admin-demo.html`：深色光斑背景、玻璃基类、按钮/输入/标签做法

范围：**只改登录页**。其他页面保持现有 Corporate Trust 浅色，不动路由、接口、权限、校验、埋点。

---

## 1. 改了什么

### 1.1 新增玻璃令牌

`tokens.json` 增加 `semantic.glass` 组，全部由 `build-tokens.mjs` 生成 CSS 变量：

| 组 | 变量示例 |
|---|---|
| 背景 | `--glass-page-bg`、`--glass-blob-a/b/c` |
| 三层玻璃 | `--glass-layer-1/2/3-bg/blur/border` |
| 双层阴影 | `--glass-shadow-1/2` |
| 墨色 | `--glass-ink`、`--glass-ink-2`、`--glass-ink-3` |
| 强调 | `--glass-accent`、`--glass-accent-soft`、`--glass-accent-line` |
| 控件 | `--glass-field-bg/border/focus`、`--glass-button-bg/hover/shadow` |
| 圆角 | `--glass-radius-sm/md/lg/pill` |

当前 **576 个令牌**，`validate_tokens.py` OK。

### 1.2 玻璃基类

新增 `src/styles/glass.css`，仅登录页导入：

- `.glass`：L1，blur 18px / 白 5.5% / 边框白 10%
- `.glass.lv2`：L2，blur 24px / 白 9.5% / 边框白 16%
- `.glass.lv3`：L3，blur 34px / 白 14% / 边框白 24%
- 统一 `::before` 顶边高光、双层阴影、`-webkit-backdrop-filter` 双写
- `@supports not (backdrop-filter...)` 降级为 `--glass-fallback-bg`

### 1.3 动效层

新增动效令牌（`semantic.motion.*`）：

- 曲线：`--ease-out`、`--ease-expo`、`--ease-in-out`、`--ease-soft`、`--ease-exit`
- 时长：`--motion-press/hover/ui/view/reveal/item/count`
- 错峰：`--motion-stagger-item/line`

登录页进场编排：

| 元素 | 延迟 | 位移 | 时长 |
|---|---|---|---|
| Header | 0ms | 18px | 620ms |
| 登录卡外层 `panelWrap` | 165ms | 18px | 620ms |
| 标签 / 标题 / 说明 | 110 / 165 / 220ms | 18px | 620ms |
| 能力点 / 指标 / 快照外层 | 275 / 330 / 390ms | 18px | 620ms |
| 演示账号 4 张 | 420 + i×70ms | 10px | 420ms |
| 快照进度条 | 520ms | scaleX 0→1 | 620ms |

- 所有入场只动 `opacity` 与 `transform`，不用 `height/width/top/left`，不产生 CLS。
- 玻璃 `backdrop-filter` 本身不参与动画；登录卡和快照的动画挂在无滤镜的 `panelWrap` / `previewWrap` 外层。
- 统计数字 0→4/5/1，900ms ease-out quart，`tabular-nums`；reduced motion 直接显示终值。
- `prefers-reduced-motion: reduce` 时动画数量为 0，内容仍完整可见。
- 所有 hover / press 统一 180ms / 140ms；没有 `transition: all`，没有 bounce。

### 1.4 登录页

- L0：`--glass-page-bg` 冷色径向光 + 三个 46vw 光斑（blur 80px）+ 噪点 SVG。
- L1：顶部授权胶囊使用 `.glass`。
- L2：右侧登录卡和左侧「匹配快照」使用 `.glass.lv2`。
- 只有 3 个 backdrop-filter 元素，低于 12 个上限。
- 标题去掉紫色渐变，第二个短句改为单色 accent。
- 输入框白 5% 底、白 9% 边框、focus 为 accent 描边 + 3px 软环。
- 主按钮为 accent 实色渐变 + 顶部白高光 + 接触阴影，active 下压。
- 演示账号改为低透明玻璃小卡，不再是大面积实色块。
- 背景动画只动 `transform`，`prefers-reduced-motion` 关闭。
- 逻辑未改：演示填充、回车提交、错误分支、`returnTo`、登录成功跳转、埋点均保留。

---

## 2. 验收

### 截图

| 文件 | 说明 |
|---|---|
| `shots/glass-login-1440-final.png` | 1440 桌面 |
| `shots/glass-login-768-final.png` | 768 单列，登录卡在前 |
| `shots/glass-login-390-final.png` | 390 手机，单列、演示账号单列 |
| `shots/glass-login-error-final.png` | 错密码错误态 |
| `shots/glass-login-success.png` | 登录成功落到 `/dashboard` |
| `shots/glass-login-motion-1440.png` | 动效落定态 |
| `shots/glass-login-reduced.png` | reduced-motion 终态 |

### 读数

```text
1440: scrollWidth=1440  clientWidth=1440
768:  scrollWidth=768   clientWidth=768
390:  scrollWidth=390   clientWidth=390

计算样式：
panel/preview: blur(24px) saturate(1.55)
border: 1px rgba(255,255,255,0.16)
shadow: 双层 + inset
glass 数量: 3（badge / panel / preview）
进场动画: 16 个（3 个光斑 + 8 个区块 + 4 个账号 + 1 个进度条）
reduced-motion: animation count = 0，内容完整

成功路径: /login → /dashboard
失败路径: alert 显示「账号或密码不对...」
```

### 门禁

```text
tsc 0
lint_hardcodes 0 处（135 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
validate_tokens 576 tokens OK
build JS 172.38 kB gzip / CSS 23.79 kB gzip
```

`lint.mjs` 的 3 个 WARN 是既有计时器 `padStart`，与登录页无关。

---

## 3. 设计取舍

- **没有改全站主题**：其他页仍是 Corporate Trust 浅色，登录后进入 `/dashboard` 会看到旧风格；这是按「一页一审核」故意保留的过渡态。
- **没有做 3D 倾斜**：登录卡保持平面玻璃，避免左上方光源与透视同时作用导致高光方向错误。
- **没有让玻璃卡本体动**：卡片外包一层无滤镜的 `panelWrap` / `previewWrap`，动画只作用于外壳，避免 `backdrop-filter` 参与动画重绘。
- **没有用 JS 强制隐藏内容**：入场动画完全由 CSS 在首帧启动，JS 只负责数字增长；即使动画被系统关闭，内容也不会残留 opacity:0。
- **没有给输入框单独加 blur**：输入框只做半透明底和细边框，blur 只留给卡片层，避免一屏玻璃元素过多。
- **演示账号保留**：这是当前演示环境的一部分；正式环境应移除快捷填充和统一密码提示。

---

## 4. 待你拍板

1. **玻璃强度**：当前 L2 卡片是否合适，还是再收一点（更暗、更透明、更少光斑）？
2. **下一步**：确认后先改应用壳层（侧栏 + 顶栏）还是直接改工作台内容？
