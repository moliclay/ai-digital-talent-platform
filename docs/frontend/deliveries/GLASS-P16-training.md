# GLASS-P16 · 培训成长

本轮把 `/training` 接到玻璃壳层；HR 四标签和员工「我的培训」共用同一路由与壳层。样式只覆盖表现层，课程 CRUD、缺口诊断、培养计划、台账、员工任务进度逻辑未改。

## 1. 改动范围

| 文件 | 改动 |
|---|---|
| `src/components/app-shell.tsx` | `glassMode` 增加 `/training` |
| `src/pages/training.tsx` | 页头包 `pageHead`；四标签加 `glass-tabs`；四个 Panel 加 `glassTable`；计划带教人单元格加 `mentorCell` 长文本换行 |
| `src/pages/training.module.css` | 页头 L2、标签条 L1、四个内容面板 L1、表格表头/进度/chips/选中态、`trainingRise`、390 内部横向滚动 |
| `src/pages/training/my-training.tsx` | 五个返回分支和主分支的 PageHeader 统一包 `pageHead` |
| `src/pages/training/my-training.module.css` | 页头 L2、五张概览卡 tactile field、进度条、两个 block L1、计划/任务分隔线、`myRise` |

## 2. 层次

| 层 | 元素 | 做法 |
|---|---|---|
| L1 | 四标签条、当前内容面板、员工两个 block | `blur(18px)` + 白 5.5% + 单层软阴影 |
| L2 | 页头 | `blur(24px)` + 白 9.5% + 双层阴影 |
| L3 | 新建/编辑课程、生成计划、删除确认、培养计划详情抽屉 | 既有 Modal/Drawer 的 `glass-dialog` / `glass-drawer` 配方 |
| 字段面 | 员工五张概览卡、进度带、计划卡、chips、表格头/行 | 不逐卡 backdrop blur；使用 `--glass-field-bg` + 1px 半透明边 |

同屏玻璃元素：

- HR 课程页：侧栏 + 页头 + 标签条 + 当前面板 = **4 个**。
- 员工有数据：侧栏 + 页头 + 两个 block = **4 个**（五张概览卡不单独 blur）。
- 员工无计划：侧栏 + 页头 = **2 个**。

## 3. 页面

### HR

- 页头：16px/600「培训成长」；四标签：课程 / 缺口诊断 / 培养计划 / 成长台账。
- 课程：5 门真实课程；搜索条、新建课程、7 列表格、编辑操作。
- 缺口诊断：候选人 + 目标岗位；五维缺口表；程度徽标；推荐课程 chips；生成培养计划入口。
- 培养计划：4 条真实计划；进度条 + 任务计数；查看打开右侧详情抽屉。
- 成长台账：候选人筛选；空态/台账表。
- 新建课程/删除确认：L3 弹窗；课程详情抽屉：L3 右侧抽屉。

### 员工

- 同一个 `/training` 路由，`TrainingPage` 按角色切到 `MyTrainingView`。
- 页头「我的培训」；概览 5 卡；总进度；培养计划卡；成长台账；员工「记录进度 / 完成」走原 Modal。
- 无计划时保留「还没有培养计划」空态；有权限缺失时保留 403 空态。

## 4. 实测

HR `hr_zhao`：

| 场景 | 读数 |
|---|---|
| 课程 | 5 门；表头 7 列；搜索、编辑、新建课程入口正常 |
| 缺口诊断 | 张伟 / ai应用开发；5 个维度；高/低/已达标徽标与推荐课程 chips 可读 |
| 培养计划 | 4 条；陈宇 1/3 33%、王峰 2/3 67%、程磊 0/3 0%、陈宇岗前暂无任务 |
| 成长台账 | 张伟无记录，空态完整 |
| 培养计划抽屉 | 右侧抽屉打开；目标、阶段、3 个任务、记录进度/完成按钮可读 |
| 新建课程 | L3 弹窗；字段、下拉、富文本区与按钮可读 |

员工 `emp_chen`：

| 场景 | 读数 |
|---|---|
| 登录落地 | `/training`，h1「我的培训」 |
| 当前账号 | 陈宇 / 普通员工；`onboarded=false` |
| 页面 | 页头 L2 + 「还没有培养计划」空态；无浅色残留 |
| 完整任务态 | 本轮未重新构造；演示库中王峰账号已不在 `/system/users` 返回列表，程磊一次性密码未落盘 |

视口：

| 视口 | scrollWidth / clientWidth | 结论 |
|---|---|---|
| 1440 × 1100 | 1440 / 1440 | 无页面横向溢出 |
| 390 × 844 | 390 / 390 | 页面不溢出；课程表在自身容器内横向滚动（表宽 704，容器裁切） |

## 5. 动效

| 元素 | 延迟 | 时长 | 位移 |
|---|---|---|---|
| 页头 | 110ms | 620ms | 18px |
| 标签条 | 165ms | 620ms | 18px |
| 内容面板 | 255ms | 620ms | 18px |

- reduced-motion：页头、标签条、面板、员工 block 全部关闭；HR 实测 `getAnimations().length === 0`。
- 玻璃元素本身不挂 animation，均由无滤镜外层承载。

## 6. 门禁原始输出

```text
tsc=0
Scanned 136 of 136 candidate file(s).
OK: no hardcoded values found.
OK: no emoji in UI output or taste files, and no em or en dash.
RESULT: 0 FAIL, 3 WARN
Parsed 1/1 token files, 583 tokens defined.
dist/assets/index-BJ8z_8g1.css  206.68 kB │ gzip:  29.87 kB
dist/assets/index-CxKof33_.js   581.72 kB │ gzip: 173.66 kB
✓ built in 5.31s
```

> 首次 lint 报 1 FAIL：`.tabActive` 的 1px 内描边被当成浮层阴影；已加 `taste-skill-ignore` 说明「选中标签玻璃高光」并复跑为 0 FAIL。

## 7. 截图

- `shots/glass-training-1440.png`（课程，真实 5 门）
- `shots/glass-training-390.png`（390，课程表内部滚动）
- `shots/glass-training-diagnose-1440.png`（缺口诊断初始）
- `shots/glass-training-diagnose-result-1440.png`（缺口诊断结果）
- `shots/glass-training-plans-1440.png`（培养计划，长带教人文本已回列内换行）
- `shots/glass-training-ledger-1440.png`（成长台账空态）
- `shots/glass-training-drawer-1440.png`（培养计划详情抽屉）
- `shots/glass-training-course-dialog-1440.png`（新建课程 L3）
- `shots/glass-my-training-1440.png`（员工我的培训空态）
- `shots/glass-my-training-390.png`（员工 390）

## 8. 已知边界

- 演示库培养计划的 `mentor` 字段有两行被写成「建议优先安排…」长文本（后端生成数据问题）；本轮只在表格内换行，不篡改数据。
- 缺口诊断「技术深度」目标值显示为 6、当前 70、缺口 0，属于后端画像/岗位基线数据不一致；前端按接口值显示。
- 课程删除仍只有 `admin` 具备；`hr_zhao` 页面不显示删除按钮（G32）。
- 员工完整任务态本轮未重新登录验证：王峰账号不在当前用户列表，程磊一次性密码不落盘；本轮只验证了员工空态与样式壳层。
- 未改后端培训接口、任务进度语义或课程权限。
