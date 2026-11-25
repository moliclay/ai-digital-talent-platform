# GLASS-P15 · 语义检索

本轮把 `/semantic` 接到玻璃壳层：页头、向量能力、三标签和三个结果面板统一到 L1/L2；全量重建确认走 L3。向量检索、查重、岗位召回和索引校验逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/semantic` |
| `src/pages/semantic.tsx` | 无权限/状态错误/主分支页头统一包 `pageHead`；状态面板加 `glassPanel`，三个结果 Panel 加 `glassTable` |
| `src/pages/semantic.module.css` | 页头 L2、状态卡、玻璃标签条、检索区、表头/相似度、空态和动效 |
| `tokens.json` | 令牌总数仍为 583 |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 侧栏、三标签条、结果表格容器 | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头、向量能力卡 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 全量重建确认 | `blur(34px)` + 白 14% + 暗色遮罩 |

同屏玻璃元素：侧栏 1 + 页头 1 + 向量能力 1 + 标签条 1 + 当前结果面板 1 = **5 个**。

## 3. 页面

- 页头：16px/600 标题，副标题 12px ink-2。
- 向量能力：4 个状态格；嵌入模型/向量库可用徽标，简历/岗位向量计数；索引状态行保留「6 / 6 条 · 索引最新」。
- 标签条：玻璃分段条，选中项 accent 软底 + accent 文字；键盘左右/Home/End 行为保留。
- 语义检索：输入、返回条数、检索主按钮；结果表用 ResumeBrief + accent 相似度。
- 简历查重：阈值选择保留；A/B brief 与相似度三列；底部人工核对提示保留。
- 岗位召回：岗位下拉 + 候选人 brief + 相似度；空态和错误态沿用原组件。
- 全量重建确认：L3；正文明确「会追加行，重复重建会让向量计数变大；检索结果不受影响」。

## 4. 实测

Milvus 19530 与 Ollama 11434 启动后实测：

| 场景 | 读数 |
|---|---|
| 向量状态 | 嵌入 bge-m3 / 1024 维可用；Milvus 可用；简历 6 条、岗位 4 条；`6 / 6 条 · 索引最新` |
| 语义检索「做过 RAG 的算法工程师」 | 5 条；张伟 57.5%、陈宇 49.6%、李娜 49.0%、刘洋 46.7%、王峰 46.2% |
| 简历查重 0.93 严格 | 程磊 A/B 100.0% 1 对 |
| 岗位召回「ai应用开发」 | 5 条；刘洋 65.3%、王峰 61.6%、李娜 60.6%、张伟 55.3%、陈宇 54.9% |

视口：

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出 |
| 390 × 844 | 390 / 390 | 状态卡单列、标签条完整，无横向溢出 |

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 向量能力卡 | 165ms | 620ms | 18px |
| 标签条 / 结果面板 | 255ms | 620ms | 18px |

- reduced-motion：页头、状态卡、标签条、结果面板全部关闭；CDP 实测 `getAnimations().length === 0`。
- Milvus 不可用时页面按真实状态隐藏三标签并显示「向量能力未启用」，不伪造检索结果。

## 6. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-B7kjK5Cq.css  200.23 kB │ gzip:  29.29 kB
dist/assets/index-DsNpiINt.js   581.05 kB │ gzip: 173.57 kB
✓ built in 4.66s
```

## 7. 截图

- `shots/glass-semantic-1440.png`
- `shots/glass-semantic-390.png`
- `shots/glass-semantic-search-1440.png`
- `shots/glass-semantic-duplicates-1440.png`
- `shots/glass-semantic-candidates-1440.png`
- `shots/glass-semantic-rebuild-1440.png`
- `shots/glass-semantic-unavailable-1440.png`（Milvus 未启动时的真实空态）

## 8. 已知边界

- 向量检索依赖本机 Milvus 19530 + Ollama 11434；关闭任一服务时页面显示不可用态，三标签隐藏。
- 全量重建的追加行副作用仍存在（G31），确认弹窗已明示；本轮没有真正提交重建。
- `/semantic` 的相似度是向量距离换算值，不代表规则匹配分；页面文案保留原口径。
- 未改后端向量写入、查重和召回接口。
