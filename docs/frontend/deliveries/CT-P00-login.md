# CT-P00 登录页 · Corporate Trust 重构验收

页面：`/login`
日期：2026-11-03
范围：**只重构登录页**；AppShell、工作台及其余页面保持原样，等这一屏拍板后再逐页替换。

---

## 1. 设计说明落地对照

| Corporate Trust 规范 | 落地方式 |
|---|---|
| 浅色模式 + Slate 50 底 | 页面底色 `--enterprise-bg` `#F8FAFC` |
| Indigo 600 / Violet 600 双色 | `--enterprise-primary` `#4F46E5`、`--enterprise-secondary` `#7C3AED` |
| Plus Jakarta Sans | `--font-family-display`，拉丁已实测加载；中文回落到 MiSans / HarmonyOS Sans SC / PingFang / 微软雅黑 |
| 渐变标题 | 第二行「落到证据上。」indigo→violet→purple 渐变文字 |
| 主按钮 + 彩色阴影 | 收敛为纯色 Indigo 主按钮 + 轻微投影，悬停上浮；不再使用强光晕 |
| 柔和彩色阴影 | 登录卡、快照卡、安全胶囊统一用 indigo 调阴影 |
| 等距 / 层叠深度 | 匹配快照卡 `perspective + rotateX(2deg) + rotateY(-6deg)`；登录卡后一层轻微错位背板 |
| 模糊光球 | 左上 indigo/violet 柔光 + 右下沉降渐变，`blur(96px)` |
| 圆角 | 卡片 12px、输入框 8px、按钮/标签 pill |
| 留白与节奏 | 1280 容器、60/40 双栏、区块 40-48px 间距 |
| 微交互 | 卡片/按钮 hover 上浮，账号卡箭头右移，颜色 220ms 过渡 |
| 可访问性 | 原生 label、`aria-busy`、错误 `role=alert`、focus-visible indigo 环、skip link |

新增令牌组（只影响使用它的页面）：

```
semantic.enterprise.*        29 个：色板 / 渐变 / 阴影 / 圆角
semantic.type.size.hero      56px
semantic.type.size.hero-mobile 38px
semantic.type.family.display Plus Jakarta Sans + 中文回落
```

令牌总数：**494**（Corporate Trust 全站重映射后），生成 314 个 CSS 变量。

---

## 2. 页面结构

- **左栏 60%**：eyebrow、渐变标题、lede、三条能力勾选、`4 / 5 / 1` 数据条、匹配快照示例卡。
- **右栏 40%**：盾牌登录卡（账号 / 密码 / 登录），下方 2×2 演示账号。
- 顶部：品牌 + 「内部系统 · 授权访问」胶囊。
- 快照卡：张伟 85.0 / 100、合格线 70、绿色「通过」、「画像各维达标」浮标、「示例数据」标识、阈值刻度线。

---

## 3. 五态与交互实测

| 态 | 触发 | 实测 |
|---|---|---|
| 默认 | 打开 `/login` | 1440 / 768 / 390 三档截图 |
| 聚焦 | Tab 到输入框 | focus-visible 2px indigo 外环 |
| busy | 提交后 | 按钮文案「正在登录」、`aria-busy=true`、禁用 |
| error | 错密码 | 「账号或密码不对」红框，布局不跳（`ct-login-error.png`） |
| success | `hr_zhao` + 123456 | 实际跳转 `/dashboard`（`p00-login-success.js` 返回 `/dashboard`） |
| 演示填充 | 点账号卡 | 账号 + 密码一次填入，可再次提交 |

无「无权限 / 空数据」态：登录页不涉及数据查询。

---

## 4. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 0 |
| 构建 | JS 157.29 kB gzip；CSS 18.39 kB gzip |
| 字体 | `document.fonts.check('16px "Plus Jakarta Sans"')` = true；h1 computed family 命中 Plus Jakarta Sans |
| 1440 | `scrollWidth 1440 / innerWidth 1440`，无横向滚动 |
| 390 | `scrollWidth 390 / innerWidth 390`，登录卡优先、演示账号单列 |
| 768 | 登录卡居中、无溢出、演示账号 2×2 不拥挤 |
| 硬编码 | `lint_hardcodes.py src`：0 处（119 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | 0 FAIL，3 WARN；渐变/彩色阴影/kicker 按 Corporate Trust 规范显式标注 `taste-skill-ignore` |
| 令牌 | `validate_tokens.py`：479 tokens，valid JSON |

---

## 5. 文件

| 文件 | 变更 |
|---|---|
| `src/pages/login.tsx` | 重写结构；原生 label/input/button，逻辑保持（校验、埋点、returnTo、演示填充） |
| `src/pages/login.module.css` | 重写视觉，使用 enterprise 令牌 |
| `src/content/copy.ts` | `login.*` 新增 eyebrow / features / stats / preview / secureBadge / panelSub / loginHint |
| `tokens.json` + `src/styles/tokens.css` | 新增 enterprise 令牌组与 display 字体、hero 字号 |
| `scripts/build-tokens.mjs` | enterprise 渐变/阴影令牌带 lint 说明注释 |
| `index.html` | Plus Jakarta Sans 字体链接 |
| `scripts/p00-login-success.js` / `p00-login-error.js` / `p00-font.js` | 登录成功、错误态、字体与溢出实测 |

---

## 6. 已知与待拍板

1. **只改了登录页**：进站后的工作台、侧边栏、表格仍是旧的深色值班仪表风；下一屏按你拍板逐页换。
2. **登录页不再放主题切换**：Corporate Trust 是浅色模式；其他页面仍有原来的深/浅切换。是否最终全站统一浅色，等全部页面重构完再定。
3. **英文字体走 Google Fonts**：已实测可加载；若部署环境无外网，需要把 woff2 放到本地 `public/fonts`。
4. **演示账号与统一密码**：仅演示环境保留；生产环境应通过环境变量隐藏。
5. **快照卡是示例数据**：已标「示例数据」，不是实时查询；数值取自演示库张伟 85/70。

---

## 7. 截图

| 文件 | 说明 |
|---|---|
| `shots/ct-login-1440.png` | 1440×950 最终版 |
| `shots/ct-login-768.png` | 768×1200 登录卡优先 |
| `shots/ct-login-390.png` | 390×844 手机 |
| `shots/ct-login-error.png` | 错误态 |
