# GLASS-P10 · 系统管理

本轮把 `/system` 接到玻璃壳层：页头、用户/角色/操作日志三标签和三个只读表格统一到 L1/L2。页面只读，未新增用户/角色管理端点。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/system` |
| `src/pages/system.tsx` | 无权限分支与主分支的页头统一包 `pageHead`；三个 Panel 加 `glassTable` |
| `src/pages/system.module.css` | 页头 L2、标签条 L1、三个表格 L1、代码标签与动效 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、用户/角色/日志标签条、当前表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 无 | 页面只有只读列表，没有弹层 |

同屏玻璃元素：侧栏 1 + 页头 1 + 标签条 1 + 当前表格 1 = **4 个**。

## 3. 页面

- 页头：16px/600 标题，副标题 12px ink-2。
- 标签条：由下划线 tab 改为紧凑玻璃分段条；选中项 accent 软底 + accent 文字，键盘左右/Home/End 行为保留。
- 用户表：账号、姓名、部门、邮箱、状态；状态启用 accent / 停用 neutral。
- 角色表：角色、代码、数据范围、说明；代码使用玻璃字段胶囊。
- 操作日志：时间、账号、模块、动作、方法、路径、结果、耗时；登录请求仍显示「未记录账号 / 登录」；底部口径说明保留。
- 分页、空态、错误态、无权限态全部继承玻璃作用域 token。

## 4. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 标签条 | 165ms | 620ms | 18px |
| 当前表格 | 255ms | 620ms | 18px |

- 只动 `transform` / `opacity`。
- reduced-motion：三处全部关闭；CDP 实测 `getAnimations().length === 0`。

## 5. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 用户 5 行，无页面横向溢出 |
| 390 × 844 | 390 / 390 | 只保留账号/姓名/状态三列，无页面横向溢出 |

三标签均实测：用户 5 个账号、角色 4 个、操作日志按当前时刻读数（约 1815 条，随登录持续增长）。

## 6. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-Dolf034P.css  193.58 kB │ gzip:  28.71 kB
dist/assets/index-ZpGpvLxi.js   580.41 kB │ gzip: 173.45 kB
✓ built in 5.37s
```

## 7. 截图

- `shots/glass-system-1440.png`
- `shots/glass-system-roles-1440.png`
- `shots/glass-system-logs-1440.png`
- `shots/glass-system-390.png`

## 8. 已知边界

- 页面只读：后端没有用户/角色/日志的写接口，本轮不补管理端点。
- 只有 admin 能进；hr/biz/employee 直达由路由守卫或 403 空态处理。
- 操作日志总数随每次登录增长，交付里的读数只代表截图时刻。
- 未改权限逻辑和后端只读接口。
