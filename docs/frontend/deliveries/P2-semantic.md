# P2 语义检索 / 向量 · 交付

日期：2026-11-04
范围：后端 v2 的 brief 字段、查重/召回可点详情、向量过期修复；**P3 未开工**。

---

## 1. 已完成

### 1.1 统一 ResumeBrief

`semantic.tsx` 的三种结果都改为 `ResumeBrief`：

- 语义检索：`ResumeBrief & { score }`
- 简历查重：`{ similarity, a: ResumeBrief, b: ResumeBrief }`
- 岗位召回：`ResumeBrief & { similarity }`

统一用 `ResumeBriefCell` 渲染：

- 姓名（可点 → 全局 `?resume=` 详情弹窗）
- 学历 / 专业 / 年限
- `skills_top` chips，末尾 `+N`（`skills_count - skills_top.length`）
- 来源文件
- `accessible=false`：姓名灰、按钮禁用、提示「无权查看该简历」

语义检索和岗位召回只保留「候选人 / 相似度」两列；查重保留 A/B 两侧 + 相似度，不再显示「暂无」学历。

### 1.2 向量状态

`Status` 增加：

- `expected_count`
- `stale`

状态卡底部显示：

```
6 / 6 条 · 索引最新
```

`stale=true` 时显示黄色提示和「修复过期索引」按钮，调：

```
POST /vector/reindex-if-stale
```

返回 `rebuilt=false` 提示「本来是最新的」；`rebuilt=true` 显示 `count / expected`。原「重建索引」改名「全量重建」，与幂等修复区分。

### 1.3 点击详情

从任意 brief 点击姓名：

- 写当前页 query `?resume=<parsed_resume_id>`
- AppShell 的 ResumeDetailHost 打开 880px 详情弹窗
- 关闭后保留当前 tab、搜索词和滚动位置

实测语义检索点程磊 → `?resume=8`，详情弹窗内容为「程磊 · 简历」。

---

## 2. 真实读数

```
vector/status: resume_count=6, expected_count=6, stale=false
semantic «做过 RAG 的算法工程师»: 6 条
duplicates threshold=0.50: 8 对
semantic-candidates job 3: 6 条
```

示例 brief（程磊）：

```
学历 本科 / 专业 网络工程 / 0 年
skills_top: Kubernetes, LangChain, PyTorch, FastAPI, Python +4
filename: 程磊_应届.txt
```

---

## 3. 状态

| 场景 | 结果 |
|---|---|
| 语义检索 | 6 条，brief 字段完整，姓名可点 |
| 查重 | 8 对，A/B 两侧独立展示并可点 |
| 岗位召回 | 6 条，按 similarity 展示 |
| brief 点详情 | `?resume=8` + 程磊详情弹窗 |
| 向量状态 | `6/6 · 索引最新` |
| 过期修复 | 代码已接 `reindex-if-stale`；当前 `stale=false` 未触发按钮 |
| 390 | `scrollWidth 390`，无横向溢出 |

---

## 4. 门禁

```
tsc 0
lint_hardcodes 0 处（130 文件）
check_no_emoji OK
lint.mjs 0 FAIL, 3 WARN
build JS 166.11 kB gzip · CSS 21.11 kB gzip
```

---

## 5. 已知

1. 当前演示数据所有 brief 的 `accessible` 都是 true，无权限置灰分支只能靠代码保证，暂无真实降权账号样本。
2. 当前向量 `stale=false`，修复按钮不会出现；接口返回结构按后端文档实现，未强行制造过期状态。
3. 语义检索的「候选人」列内包含姓名、学历、专业、年限、技能、文件，信息密度比旧表高；窄屏下技能会换行。
4. 查重阈值下拉已加宽，避免「0.50（很宽松）」被截断。

---

## 6. 截图

| 文件 | 说明 |
|---|---|
| `shots/p2-semantic-search.png` | 语义检索 6 条 brief |
| `shots/p2-semantic-duplicates.png` | 查重 A/B brief |
| `shots/p2-semantic-candidates.png` | 岗位召回 |
| `shots/p2-semantic-detail.png` | brief 点开程磊详情 |
| `shots/p2-semantic-390.png` | 390 语义检索 |
