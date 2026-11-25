# GLASS-P14 · 空缺预警

本轮把 `/vacancy` 接到玻璃壳层：页头、KPI 条、岗位预警卡、储备池和预警口径统一到玻璃语言。预警计算、储备池查询和跳转逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/vacancy` |
| `src/components/ui/kpi-strip.tsx` | 增加稳定字面类 `glass-kpi`，让共享 KPI 条可被作用域样式命中 |
| `src/pages/vacancy.tsx` | 无权限/加载错误/主分支页头统一包 `pageHead`；储备池 Panel 加 `glassTable` |
| `src/pages/vacancy.module.css` | 页头 L2、KPI/布局动效、预警卡玻璃字段面、选中态、储备池/图例 |
| `src/styles/glass-app.css` | 新增 `--kpi-label/value/divider` 直连覆盖与 `.glass-kpi` L2 配方 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、储备池表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头、KPI 条 | `blur(24px)` + 白 9.5% + 双层阴影 |
| 内容面 | 岗位预警卡、预警口径图例 | 玻璃字段底 + 1px 白 9% 边框，不加 blur |
| L3 | 无 | 页面只有列表和储备池，没有弹层 |

同屏玻璃元素：侧栏 1 + 页头 1 + KPI 1 + 储备池 1 = **4 个**；岗位预警卡不逐个模糊，避免岗位多时同屏玻璃数失控。

## 3. 页面

- 页头：16px/600 标题，副标题 12px ink-2。
- KPI 条：共享 `KpiStrip` 加 `glass-kpi` 类，L2 玻璃；标签/数值/分隔线改由玻璃 token 直连，避免旧浅色残留。
- 岗位预警卡：深色玻璃字段面；选中项 accent 软底 + accent 描边；等级使用高 danger / 中 warn / 低 ink-2 / 正常 accent。
- 统计格：名额、已通过、空缺；空缺 >0 用 warn；卡脚保留合格线与通过率。
- 储备池：L1 面板，接近线内候选人表 + 画像达标未投递表；空态保留。
- 预警口径：玻璃字段卡，四档等级色阶和通过率分母说明完整保留。
- 390 下 KPI 2 列、预警卡和储备池单列堆叠，无页面横向溢出。

## 4. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| KPI 条 | 165ms | 620ms | 18px |
| 预警列表 + 储备池布局 | 255ms | 620ms | 18px |

- 预警卡自身不做错峰动画，避免多卡同时 transform 造成视觉噪音。
- reduced-motion：页头、KPI、布局全部关闭；CDP 实测 `getAnimations().length === 0`。

## 5. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 44% |
| 390 × 844 | 390 / 390 | 无页面横向溢出；KPI 2×2，卡片单列 |

数据读数：在招岗位 3、有空缺岗位 1、空缺合计 1 人、高预警 0；当前选中「高级算法工程师(AI平台部)」，名额 3 / 已通过 2 / 空缺 1。

## 6. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-K0BF34SE.css  197.06 kB │ gzip:  29.02 kB
dist/assets/index-vKdnz9Gg.js   580.68 kB │ gzip: 173.49 kB
✓ built in 6.51s
```

## 7. 截图

- `shots/glass-vacancy-1440.png`
- `shots/glass-vacancy-390.png`

## 8. 已知边界

- 预警卡使用玻璃字段面而非独立 L2 模糊卡；页面可能有多张岗位卡，逐卡模糊会突破同屏玻璃预算。
- `/job-profiles/{id}/reserve` 无分页/limit（G30），大数据量时仍可能返回过长列表，本轮未改后端。
- 通过率分母是已匹配人数，不等于名额；图例底部说明保留，未改口径。
- 未改预警计算、储备池筛选和跳转逻辑。
