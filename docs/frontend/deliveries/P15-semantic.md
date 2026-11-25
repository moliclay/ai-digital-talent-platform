# P15 语义检索 · 交付说明

路由：`/semantic`
日期：2026-11-03
页面任务：用一句话找简历、查疑似重复、按岗位语义召回。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/semantic.tsx` / `.module.css` | 向量状态、三个标签（语义检索 / 简历查重 / 岗位召回）、重建索引确认 |
| `src/components/app-shell.tsx` | 新增「语义检索」菜单（前端合成，后端菜单表没有 `/semantic`） |
| `src/content/copy.ts` | 新增 `semantic.*` |
| `src/app.tsx` | 路由 `/semantic` |
| `scripts/p15-search.js` / `p15-dupes.js` | 截图时真实检索 / 切阈值 |
| `PAGE-MAP.md` | 新增 G31 |

---

## 2. 页面结构

- **向量能力**：嵌入模型（bge-m3 / 1024 维 / 可用）、向量库（http://127.0.0.1:19530 / 可用）、简历向量 6 条、岗位向量 2 条；`resume:create` 才有「重建索引」，弹确认后执行。
- **语义检索**：一句话 + 返回条数（5/10/20）→ 结果表（姓名 / 学历 / 年限 / 技能 / 相似度）；相似度按百分比、等宽数字。
- **简历查重**：阈值（0.93 / 0.90 / 0.80 / 0.70 / 0.50）→ 成对表格（简历 A / 简历 B / 相似度）+「只提示，不自动合并」说明。
- **岗位召回**：选岗位 → 语义召回前 10 人（姓名 / 学历 / 年限 / 技能 / 相似度）。
- 三个标签是 `tablist`，方向键 / Home / End 切换。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次打开 / 首次检索 | 状态格骨架 + 表格骨架 |
| empty | 未输入检索词；无结果；0 对重复；无召回 | 初始空态 / 「没有匹配的简历」/「没有超过阈值的疑似重复」/「没有召回候选人」 |
| error | CDP 拦截 `*vector/status*` | 「语义数据没取到。」+ 重试（`shots/semantic-error.png`） |
| no-permission | `emp_chen`、`pm_wang` | 「没有语义检索的权限」（`shots/semantic-403.png`） |
| over-limit | 检索 top-K 5/10/20；查重全量成对（无分页）；召回固定 10 人 | 6 条简历全返回；0.50 阈值 9 对全部展示 |
| 未启用 | Milvus/Ollama 任一不可用 | 状态卡显示「不可用」+「向量能力未启用」引导（代码路径，本次服务已启动未实测） |

---

## 4. 真实数据

### 4.1 状态（清理重建后）

```
嵌入模型 bge-m3 · 1024 维 · 可用
向量库 http://127.0.0.1:19530 · 可用
简历向量 6 条
岗位向量 2 条
```

`POST /vector/index` 实测：`resumes {indexed:6,total:6}`、`jobs {indexed:2,total:2}`。

### 4.2 语义检索「做过 RAG 的算法工程师」

| 姓名 | 学历 | 年限 | 相似度 |
|---|---|---|---|
| 程磊 | 本科 | 0 年 | 61.3% |
| 张伟 | 硕士 | 5 年 | 57.5% |
| 陈宇 | 硕士 | 5 年 | 55.1% |
| 王峰 | 本科 | 6 年 | 51.6% |
| 李娜 | 本科 | 3 年 | 49.0% |
| 刘洋 | 本科 | 6 年 | 46.7% |

### 4.3 简历查重

- 阈值 0.93：0 对（演示库没有高度重复）。
- 阈值 0.50：9 对，Top 3：陈宇 / 张伟 77.5%、王峰 / 刘洋 71.9%、刘洋 / 张伟 69.3%。

### 4.4 岗位召回（高级算法工程师）

| 姓名 | 学历 | 年限 | 相似度 |
|---|---|---|---|
| 陈宇 | 硕士 | 5 年 | 64.0% |
| 王峰 | 本科 | 6 年 | 64.0% |
| 张伟 | 硕士 | 5 年 | 61.0% |
| 刘洋 | 本科 | 6 年 | 59.0% |
| 程磊 | 本科 | 0 年 | 56.4% |
| 李娜 | 本科 | 3 年 | 52.7% |

召回是「文本像不像」，不是「岗位合不合适」：产品背景的王峰/刘洋会因为「需求分析、项目管理」文本接近而排进前列，页面口径写「与规则储备池互补」。

---

## 5. 权限

| 角色 | 状态 |
|---|---|
| admin / hr_zhao | 200，hr 可重建索引（`resume:create`） |
| pm_wang | **403**（实测没有 `resume:view`，与 PAGE-MAP 原假设不同） |
| emp_chen | 403 |

---

## 6. 文案 key

| key 组 | 内容 |
|---|---|
| `semantic.title/sub/tabs` | 标题、标签 |
| `semantic.status* / embed / milvus / resumeCount / jobCount` | 状态卡 |
| `semantic.rebuild*` | 重建索引与确认（含追加行提示） |
| `semantic.search* / topK / columns` | 检索 |
| `semantic.duplicate* / threshold*` | 查重 |
| `semantic.candidates* / jobPlaceholder` | 岗位召回 |
| `semantic.*Empty / loadError* / noPermission*` | 空态与错误 |

---

## 7. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入语义检索 | `page` |

不含检索词、姓名、分数。

---

## 8. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 149.07 kB gzip；CSS 15.55 kB gzip |
| 令牌 | 426 个，`validate_tokens.py` OK |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（113 文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，3 WARN（`padStart` 用于时钟） |
| 1440 | 194 字，<13px 占 56%（表头/状态标签/技能文本占比高），无横向滚动，无 <24px 点击目标 |
| 1440 岗位召回 | 521 字，<13px 占 20% |
| 768 | 无横向滚动；状态卡 2×2，搜索栏换行，表格隐藏学历/年限 |

---

## 9. 已知问题（不阻塞，但 G31 建议排期）

1. **G31 索引写入不幂等**：`/vector/index`、`/resumes/duplicates`、`/job-profiles/{id}/semantic-candidates` 都会追加行。实测连续查重后简历计数 6→18→36；查重写的是 `id/vector/name` 缺字段行，召回可能命中这些行，教育/年限/技能显示「暂无/0 年」。本次交付前已 `drop` 两个集合后重建，最终 6/2。
2. **计数会随使用漂移**：`semantic-candidates` 每次调用还会 upsert 一次岗位向量，岗位计数会从 2 变 3。
3. **pm_wang 实际 403**：原计划写「只读」，但 `pm_wang` 没有 `resume:view`；页面与菜单都按真实权限隐藏。
4. **检索结果不能进简历详情**：接口只给 `parsed_resume_id`，简历详情抽屉按 `resume_file.id` 打开，没有对应路由；不伪造跳转。
5. **未启用态未实测**：需要停 Milvus/Ollama；代码路径与文案已就位。
6. **向量库地址直接展示**：`http://127.0.0.1:19530` 对 HR 偏技术化，后续可收进悬浮说明。
7. **390 未适配**（既定暂缓）。

---

## 10. 截图

| 文件 | 说明 |
|---|---|
| `shots/semantic-1440.png` | 1440×1200 语义检索（6 条结果，状态 6/2） |
| `shots/semantic-duplicates.png` | 1440×1100 查重 0.50（9 对；多次查询后计数 36，见 G31） |
| `shots/semantic-candidates.png` | 1440×1100 岗位召回（6 人，状态 6/2） |
| `shots/semantic-confirm.png` | 重建索引确认（含追加行提示） |
| `shots/semantic-light.png` | 1440×1200 浅色检索 |
| `shots/semantic-768.png` | 768×1200 检索 |
| `shots/semantic-403.png` | 普通员工无权限 |
| `shots/semantic-error.png` | 状态请求失败 |
