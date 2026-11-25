# GLASS-P06 · 人才画像

本轮把 `/talent-profiles` 接到玻璃壳层：页头、画像卡片、雷达图和画像详情弹窗统一到 L1/L2/L3。搜索、生成画像、分页、权限分支均未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/talent-profiles`；该路由挂 `glass-talent`，单独压低光斑强度 |
| `src/pages/talent-profiles.tsx` | 页头包 `pageHead`；画像卡传入 `--card-index` 做错峰；无其他逻辑改动 |
| `src/pages/talent-profiles.module.css` | 页头/画像卡 L2、玻璃卡底色、动效和移动端样式 |
| `src/pages/talent-profiles/radar-chart.tsx` | 最强维度增加外圈 halo，点半径 3 → 5 |
| `src/pages/talent-profiles/radar-chart.module.css` | 最强点改为亮色填充 + accent 描边 + halo |
| `src/content/copy.ts` | 雷达说明由「深色点」改为「亮色点」，与深色玻璃上的实际表现一致 |
| `src/styles/glass-app.css` | `--data-series-2` 映射到 accent；新增 `--glass-card-tint` 与 talent 作用域光斑强度 |
| `tokens.json` / `src/styles/tokens.css` | 新增 `semantic.glass.card-tint`；令牌总数 581 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏 | `blur(18px)` + 白 5.5% |
| L2 | 页头、6 张画像卡 | `blur(24px)` + 白 9.5% + 双层阴影；卡片额外叠 22% 深色 tint，压住背后光斑造成的绿/蓝色差 |
| L3 | 画像详情、生成画像 | `blur(34px)` + 白 14% + 暗色遮罩；由 `body.glass-route` 让 portal 继承玻璃令牌 |

同屏 `backdrop-filter`：侧栏 1 + 页头 1 + 首屏 6 张卡 = **8 个**；打开画像详情后 9 个。

画像页的活动光斑透明度单独从 0.4 降到 **0.26**，否则右侧卡片会被青色光斑染成绿色，看起来像选中态。

## 3. 画像卡

- 卡片：`22px` 圆角、白 16% 边框、双层阴影，hover `translateY(-3px)`，只改 transform。
- 头像：玻璃字段底、1px 白 12% 边框。
- 姓名：16px/600 ink；画像类型 12px ink-2；摘要 14px ink-2，两行截断。
- 最强维度条：玻璃字段底；维度名 ink、数值 accent。
- 标签：玻璃字段底、12px ink-2。
- 空态/错误态/加载骨架都走同一作用域令牌，不再出现浅色卡。

## 4. 雷达图

- 五边形网格、轴线、区域全部引用现有语义 token；玻璃作用域下自动变成白色低透明网格 + accent 区域。
- 最强维度：5px 亮色圆点 + accent 描边 + 7px halo；弱化了「深色点」在深底上看不出来的问题。
- `aria-label` 仍由 `radarLabel` 生成，包含姓名和五维分值。
- 文案同步改为「亮色点是当前最强维度」。

## 5. 浮层

| 浮层 | 结果 |
|---|---|
| 画像详情 | 640px L3；雷达图、维度表、优势、待验证、用人建议、测评证据表全部深色可读 |
| 生成画像 | L3；单选、两个开关、`开始生成` 主按钮均为玻璃字段/青色 accent |
| 空态里的 `去简历页` | 仍是次级按钮，不抢主操作 |

## 6. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 列表说明条 | 165ms | 620ms | 18px |
| 画像卡 1–N | 165 + i×55ms | 620ms | 18px |

- 只动 `transform` / `opacity`，`animation-fill-mode: backwards`。
- reduced-motion：页头、列表条、卡片全部 `animation:none`；CDP 实测 `getAnimations().length === 0`。

## 7. 实测

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出；smallPct 36% |
| 768 × 900 | 768 / 768 | 两列卡片，无页面横向溢出 |
| 390 × 844 | 390 / 390 | 单列卡片，雷达标签不越界 |

搜索回归：输入「程磊」后列表切为「筛选结果 1 张」，卡片只保留程磊，雷达仍显示五维。

打开画像详情后 390 宽仍为 390 / 390；雷达图、维度表和底部关闭按钮都在弹窗内。

## 8. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 581 tokens defined.
dist/assets/index-zwPuz1x9.css  175.34 kB │ gzip:  27.28 kB
dist/assets/index-CLfQdnx6.js   577.86 kB │ gzip: 173.00 kB
✓ built in 7.80s
```

## 9. 截图

- `shots/glass-talent-1440.png`
- `shots/glass-talent-768.png`
- `shots/glass-talent-390.png`
- `shots/glass-talent-modal-1440.png`
- `shots/glass-talent-modal-390.png`
- `shots/glass-talent-generate-1440.png`
- `shots/glass-talent-search.png`

## 10. 已知边界

- 目前只有 `/dashboard`、`/resumes`、`/talent-profiles` 挂玻璃壳层；其余页面仍是旧浅色，逐页迁移中。
- `PAGE_SIZE = 12`，但首屏只展示 6 张卡；屏幕外卡片不计入同屏玻璃预算。
- 390 下页面纵向较长，雷达轴标签字号仍沿用原有 12px，移动端系统性适配暂缓。
- 本轮只改表现层，搜索、生成、分页和权限分支未改。
