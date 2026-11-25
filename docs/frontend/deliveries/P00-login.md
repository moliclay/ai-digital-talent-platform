# P00 登录 · 交付说明

路由：`/login`
日期：2026-11-03
方向：A · 值班仪表；强调色品牌青，只出现在品牌标记、焦点环与选中态。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/login.tsx` | 页面装配：文案、表单、演示账号、错误提示 |
| `src/pages/login.module.css` | 页面样式（只用令牌变量） |
| `src/components/brand-mark.tsx` | 三阶品牌标记，SVG + `currentColor` + 数据色 |
| `src/components/ui/button.tsx` / `.module.css` | 按钮原语（primary / secondary / ghost / destructive） |
| `src/components/ui/input.tsx` / `.module.css` | 输入原语（md / lg、invalid、前后缀） |
| `src/components/ui/form-field.tsx` / `.module.css` | label + hint + error 的组合，自动挂 `aria-describedby` / `aria-invalid` |
| `src/components/ui/icon-button.tsx` / `.module.css` | 图标按钮（主题切换、密码可见） |
| `src/components/ui/theme-toggle.tsx` | 白天 / 黑夜切换按钮 |
| `src/lib/api.ts` | 统一 `{code,message,data}` 解析、token 存取、落地页计算 |
| `src/lib/auth.tsx` | 会话 Provider（`/auth/me` 恢复、登录、退出） |
| `src/lib/theme.tsx` | 主题 Provider（`data-theme` + `localStorage`） |
| `src/lib/analytics.ts` | 埋点：只写 `window.dataLayer`，不联网 |
| `src/content/copy.ts` | 全部界面文案，key 用 `页面.区块.元素` |
| `src/styles/tokens.css` | 由 `tokens.json` 生成，280 个变量、58 个暗色覆盖 |
| `src/styles/base.css` | reset、焦点环、skip link、reduced-motion |
| `src/app.tsx` / `src/main.tsx` | 路由、Provider、登录保护 |
| `index.html` | 首屏前设置 `data-theme`，防闪烁 |
| `scripts/build-tokens.mjs` | 令牌生成器 |
| `scripts/shot.mjs` | CDP 截图与流程冒烟（本机浏览器工具不可用时的替代） |

---

## 2. 五态怎么触发（都可复现）

| 态 | 触发方式 | 实测结果 |
|---|---|---|
| loading | 填入演示账号后点登录；按钮进入 loading，输入框禁用，重复提交被忽略 | 本地接口约 100ms，需用 DevTools 节流才能截到 |
| empty | 不填任何内容直接点登录 | `role=alert` 显示"账号和密码都要填。"（`shots/state-empty.png`） |
| error | 填入 `hr_zhao`，密码改成 `wrong-pass`，提交 | 显示"账号或密码不对。再试一次，或找管理员重置。"并附后端原文"用户名或密码错误"（`shots/state-error-401.png`） |
| no-permission | 停用账号登录（后端返回 403） | 显示"这个账号已停用。找管理员恢复后再登录。"（代码路径，未改数据库，未截图） |
| over-limit | 账号填 70 个字符，提交 | 前端拦截："账号最多 64 个字符。"（`shots/state-overlimit.png`）；密码上限 128 同理 |

权限缺省：`/login` 公开；已登录访问 `/login` 直接跳落地页；登录失败统一 401 文案，不暴露"账号是否存在"。

---

## 3. 文案 key（`src/content/copy.ts`）

| key | 文案 |
|---|---|
| `login.titleLine1` / `titleLine2` | 把每一次用人判断，/ 落到证据上。 |
| `login.ledeLine1` / `ledeLine2` | 简历、测评、画像、匹配，/ 在同一条链路上，分数能追到条件。 |
| `login.note` | 匹配分数不接模型，可复现；测评证据最多加权 30%。 |
| `login.panelTitle` | 登录 |
| `login.username` / `password` | 账号 / 密码 |
| `login.submit` / `submitting` | 登录 / 正在登录 |
| `login.demoTitle` / `demoHint` | 演示账号 / 点账号填入，密码统一 123456 |
| `login.footer` | 数据范围按账号权限生效。 |
| `login.showPassword` / `hidePassword` | 显示密码 / 隐藏密码 |
| `theme.toLight` / `theme.toDark` | 切换到白天 / 切换到黑夜 |
| `login.errors.*` | empty / usernameTooLong / passwordTooLong / badCredentials / disabled / generic / offline |

---

## 4. 埋点事件与字段

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入登录页 | `page: "login"` |
| `login_submit` | 通过前端校验、发起请求 | `page` |
| `login_success` | 登录成功 | `page`、`role`、`redirect` |
| `login_failure` | 登录失败 | `page`、`status`、`code` |

不含姓名、手机、邮箱、账号、密码、简历正文。实现只 push 到 `window.dataLayer`，不发起网络请求；接入统计平台时只换 sink，不改事件名。

---

## 5. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | `dist/assets/index-*.js` 91.54 kB gzip；CSS 5.48 kB gzip |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处 |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，0 WARN |
| 渲染检查 | `inspect.mjs --app http://127.0.0.1:5174/login`：0 FAIL，1 WARN（tiny-text 52%） |
| 对比度 | `validate_contrast.py tokens.json`：两套主题全部 required 通过 |
| 登录流程 | 演示账号 → `/dashboard`，h1「工作台」，账号 `hr_zhao`，部门「人力资源部」，角色「HR 管理员」 |
| 主题切换 | 切换后 `data-theme=light`、`aria-label=切换到黑夜`、`localStorage=light`，三者一致 |

tiny-text WARN 的说明：52% 的字符在 13px 以下，全部是演示账号、提示、页脚的 12px 元信息；功能标签、输入框、按钮都是 14px 及以上。这是后台登录页的合理密度，保留。

---

## 6. 已知问题（不阻塞）

1. 390×844 下页脚"数据范围按账号权限生效。"在首屏外，需滚约 58px；登录卡片与演示账号完整可见。
2. 768 下是单栏、内容左对齐，右侧留白较大。这是保持"一条左边缘"的选择（品牌、标题、卡片、页脚同一条线），不做居中。
3. 演示账号区直接展示了账号与统一密码，只适用于 MVP 演示；上线前要用环境开关关闭。
4. 登录页的 403 只在账号停用时出现；未改数据库，所以无截图，只有代码路径。

---

## 7. 截图

| 文件 | 说明 |
|---|---|
| `shots/login-1440.png` | 1440×900 暗色 |
| `shots/login-768.png` | 768×1024 暗色 |
| `shots/login-390.png` | 390×844 暗色（DPR 2） |
| `shots/login-1440-light.png` | 1440×900 浅色 |
| `shots/login-toggle-light.png` | 点击主题按钮后的浅色状态 |
| `shots/state-empty.png` | 空表单错误 |
| `shots/state-error-401.png` | 密码错误 401 |
| `shots/state-overlimit.png` | 账号超长拦截 |
| `shots/after-login.png` | 登录成功后的临时落地页 |
