# GLASS-P07 · 智能测评

本轮把 `/exams` 接到玻璃壳层：页头、测评任务、受众筛选、题库、题目、试卷和答卷列表统一到 L1/L2；题库/题目/试卷/绑定/导入/取消确认统一到 L3。测评业务逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加精确路由 `/exams` |
| `src/pages/exams.tsx` | 页头包 `pageHead`；5 个 Panel 加 `glassTable` |
| `src/pages/exams.module.css` | 页头 L2、5 个面板 L1、受众胶囊、题库卡片、动效与移动端 |
| `src/components/audience-filter.tsx` | 增加稳定字面类 `glass-segmented*`，让共享受众控件在玻璃页切到 accent 选中态 |
| `src/styles/glass-app.css` | 新增受众分段控件的玻璃样式 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、测评任务、题库、题目、试卷、答卷、受众胶囊 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 新建题库、新建题目、新建试卷、绑定测评、导入题库、取消绑定 | `blur(34px)` + 白 14% + 暗色遮罩 |

同屏玻璃元素：侧栏 1 + 页头 1 + 5 个面板 + 受众胶囊 1 = **8 个**，低于 12 上限。

## 3. 页面

- 页头：16px/600 标题，副标题 12px ink-2。
- 受众切换：共享控件新增 `glass-segmented`，外层玻璃字段底，选中项 accent 软底 + accent 文字 + accent 描边；改为紧凑胶囊，不占满整行。
- 测评任务：L1 表格容器，状态/受众徽标走暗色 token。
- 题库：L1 列表容器，当前题库用 accent 软底 + accent 描边，不再用白色选中块。
- 题目/试卷/答卷：全部 L1 表格容器，表头 ink-2、行高 48px。
- 按钮：页面内多个创建入口保留原权限和原主次；`绑定测评`、`新建题库` 等主操作继续用青色 accent。
- 空态、错误态、分页和 skeleton 全部继承玻璃作用域 token。

## 4. 浮层

| 浮层 | 结果 |
|---|---|
| 新建题库 | L3；名称、受众、说明字段深色；创建按钮禁用态可辨 |
| 绑定测评 | L3；试卷下拉、截止/备注、候选人列表、全选和确认绑定均可读 |
| 导入题库 | L3；拖拽区深色玻璃，格式/大小提示和「上传并解析」按钮完整 |
| 新建题目 / 新建试卷 | 共用 Modal，自动 L3；原表单逻辑未改 |
| 取消绑定 | ConfirmDialog，自动 L3 |

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 5 个内容 section | 165ms | 620ms | 18px |

- 动画挂在无 `backdrop-filter` 的 `.section` 外层，玻璃面板本身不参与 transform。
- reduced-motion：页头和 section 全部关闭；CDP 实测 `getAnimations().length === 0`。

## 6. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 19% |
| 390 × 844 | 390 / 390 | 无页面横向溢出；测评任务表在容器内横向滚动 |

390 下测评任务保留候选人/结果/操作三列，受众胶囊完整显示，题库面板在下方顺序堆叠。

## 7. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-Bj9Pm89P.css  186.69 kB │ gzip:  28.28 kB
dist/assets/index-DJQYvHyn.js   579.31 kB │ gzip: 173.27 kB
✓ built in 6.26s
```

## 8. 截图

- `shots/glass-exams-1440.png`
- `shots/glass-exams-390.png`
- `shots/glass-exams-bank-1440.png`
- `shots/glass-exams-bind-1440.png`
- `shots/glass-exams-import-1440.png`

## 9. 已知边界

- 只把 `/exams` 精确路由接入玻璃壳层；`/exams/:id/take` 和 `/exams/result/:sid` 仍是旧页面，P08/P09 处理。
- `/exams` 纵向约 2970px，5 个面板顺序排列；首屏只露出任务、受众、题库和题目开头。
- 受众筛选仍只筛题库/试卷/任务三块已返回的数据，沿用原逻辑。
- 本轮未改后端、题库导入和测评提交逻辑。
