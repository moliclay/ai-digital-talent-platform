# P02 简历智能筛选 · 交付说明

路由：`/resumes`
日期：2026-11-03
页面任务：把一批简历放进队列，确认解析结果能拿去匹配。

---

## 1. 文件清单

| 文件 | 作用 |
|---|---|
| `src/pages/resumes.tsx` / `.module.css` | 页面装配：列表、筛选、分页、队列入口、上传入口、详情入口 |
| `src/pages/resumes/types.ts` | 列表 / 详情 / 队列 / 岗位选项类型 |
| `src/pages/resumes/upload-dialog.tsx` / `.css` | 上传对话框：拖拽、多选、逐份上传、逐条失败原因 |
| `src/pages/resumes/queue-drawer.tsx` / `.css` | 队列抽屉：五状态计数、任务列表、移除确认、处理下一份 |
| `src/pages/resumes/detail-drawer.tsx` / `.css` | 详情抽屉：字段、技能、优势、解析记录、原文、修正表单、下载 |
| `src/components/ui/modal.tsx` / `.css` | 模态原语：焦点陷阱、Esc、遮罩关闭、归还焦点、滚动锁 |
| `src/components/ui/drawer.tsx` / `.css` | 右侧抽屉，复用同一套焦点逻辑 |
| `src/components/ui/select.tsx` / `.css` | 非原生下拉：listbox + 键盘 + 点外关闭 |
| `src/components/ui/file-drop.tsx` / `.css` | 拖拽区 + 已选文件列表 |
| `src/components/ui/pagination.tsx` / `.css` | 分页：范围文案 + 上下页 |
| `src/components/ui/confirm-dialog.tsx` | 二次确认（队列移除用内联确认，未用它） |
| `src/components/ui/textarea.tsx` / `.css` | 多行输入 |
| `src/lib/use-focus-trap.ts` | 弹层焦点陷阱 hook |
| `src/lib/download.ts` | 带 Bearer 取文件流并触发下载 |
| `src/lib/format.ts` | 新增 `formatBytes` |
| `src/components/ui/data-table.tsx` / `.css` | 新增 `selectedKey`、`hideOnTablet`、固定表格布局 |
| `src/content/copy.ts` | 新增 `resumes.*`、`pagination.*`、`common.close/cancel` |
| `scripts/shot.mjs` | 新增 `--clickText`、`--clickSelector`、`--clickTextAfter`、`--upload`、`--search`、`--wait`、`--block` |

---

## 2. 页面结构

- 标题 + 一句口径 + 右上「解析队列 N」「上传简历」。
- 列表卡：搜索（姓名/专业/技能）、学历筛选、清空、9 列表格、分页。
- 表格行：姓名是按钮，点开详情；打开时该行保持选中底色。
- 队列抽屉：五个状态计数 → 任务列表（文件名、状态、尝试次数、时间、错误、移除）→ 底部「处理下一份」。
- 详情抽屉：基本信息两列 → 技能标签 → 优势 → 解析记录 → 原文折叠；底部「关闭 / 修正档案」，编辑态「取消 / 保存修正」。
- 上传对话框：拖拽区 → 本地校验提示 → 关联岗位 / 项目名称 → 底部「取消 / 开始上传」，结果区显示接收数与逐条失败原因。

---

## 3. 五态怎么触发

| 态 | 触发方式 | 实测 |
|---|---|---|
| loading | 首次请求列表，表格 8 行骨架；队列抽屉 3 行骨架 | 本地接口约 100ms，截图需节流 |
| empty | 搜索「不存在的人」 | 表头保留，空态「没有匹配的简历」+「清空筛选」；面板计数变「筛选结果 0 份」（`shots/resumes-empty-filter.png`） |
| error | CDP 拦截 `*keyword=*`（列表请求） | 工具栏保留，列表区显示「简历列表没取到。」+「没连上服务，稍后再试。」+ 重试（`shots/resumes-error.png`） |
| no-permission | `pm_wang` 直接访问 `/resumes`（无 `resume:view`） | 页面显示「没有查看简历的权限 / 需要 resume:view」（`shots/resumes-403.png`） |
| over-limit | 选 11 MB 的 txt | 本地拦截「big-resume.txt 超过 10 MB」，文件不进列表，开始上传禁用（`shots/resumes-overlimit.png`）；一次选超过 20 份会提示并只保留前 20 份 |

权限缺省：

- `resume:create` 不存在：隐藏「上传简历」「处理下一份」，队列只读。
- `resume:edit` 不存在：详情不显示「修正档案」。
- `resume:delete` 不存在：队列任务不显示「移除」。
- `job:view` 不存在：「关联岗位」下拉禁用。
- 队列计数与列表都走各自接口，列表只含已解析档案；待解析/失败文件只在队列里，页面文案与入口按这个事实写。

---

## 4. 文案 key

| key 组 | 内容 |
|---|---|
| `resumes.title/sub/upload/listTitle` | 简历智能筛选 / 上传后逐份解析… / 简历列表 |
| `resumes.searchPlaceholder/search/clear/clearFilters` | 搜姓名、专业或技能 / 搜索 / 清空 / 清空筛选 |
| `resumes.educationAll/educationLabel` | 全部学历 / 学历 |
| `resumes.columns.*` | 姓名 / 学历 / 专业 / 工作年限 / 技能 / 解析状态 / 置信度 / 来源文件 / 创建时间 |
| `resumes.status.*` | 待解析 / 解析中 / 已完成 / 失败 / 待 OCR |
| `resumes.total(n)/filteredTotal(n)/pageRange(a,b,n)` | 共 N 份 / 筛选结果 N 份 / 第 a-b 条，共 n 条 |
| `resumes.empty*/loadError*/noPermission*` | 空态与错误态 |
| `resumes.uploadTitle/uploadHint/drop*/job*/project*/start/uploading(i,n)` | 上传对话框 |
| `resumes.fileTooLarge/fileUnsupported/tooMany/uploadDone/uploadPartial/uploadFail` | 本地校验与服务端逐条失败 |
| `resumes.queueTitle/queueMeta(n)/queueEmpty/queueEmptyHint` | 队列面板 |
| `resumes.remove*/confirmRemove` | 移除与二次确认 |
| `resumes.parseDone/parseFailed` | 解析结果 |
| `resumes.detail*/fields.*/skillsHint/logsTitle/originalTitle/noLogs` | 详情与修正 |
| `resumes.edit/save/saved/editHint/yearsInvalid/saveError` | 修正动作 |
| `resumes.download/downloadError` | 原文下载 |
| `resumes.logStatus/logDuration` | 解析记录状态与耗时 |

---

## 5. 埋点

| 事件 | 触发 | 字段 |
|---|---|---|
| `page_view` | 进入简历页 | `page: "resumes"` |
| `resume_search` | 回车搜索 | `page`、`hasKeyword` |
| `resume_open` | 打开详情 | `page` |
| `resume_uploaded` | 上传完成且至少接收 1 份 | `page`、`accepted` |
| `queue_process_result` | 处理下一份结束 | `page`、`status`（completed / failed / idle） |

不含姓名、手机、邮箱、简历正文、文件名。

---

## 6. 自检读数

| 项 | 读数 |
|---|---|
| TypeScript | `tsc --noEmit` 退出码 0 |
| 构建 | JS 113.99 kB gzip；CSS 9.47 kB gzip |
| 硬编码 | `lint_hardcodes.py src`：OK，0 处（75 个文件） |
| Emoji / 破折号 | `check_no_emoji.py src`：OK |
| taste lint | `lint.mjs src`：0 FAIL，1 WARN（`padStart` 用于时钟，合理） |
| 工作台/简历页实测 1440 | 576 字，<13px 占 13%，无横向滚动，无 <24px 点击目标 |
| 768 | 576 字，<13px 占 13%，无横向滚动；隐藏专业/来源文件/创建时间/置信度四列 |
| 对比度 | 沿用 S2 两套主题全部 required 通过；新增弹层/下拉/警告块均用既有语义令牌 |

真实端到端（不是 mock）：

1. 用 `shots/test-resume.txt`（硕士、5 年、Python/PyTorch）在浏览器里上传；
2. 页面提示「已接收 1 份，开始解析。」，队列计数 1，列表仍 7 份；
3. 打开队列，点「处理下一份」，等待 15 秒；
4. 页面提示「已解析 1 份，列表已刷新。」，列表变 8 份，首行「张测试 / 硕士 / 5 年 / PyTorch、Python、Docker +2」，队列归 0。

这次测试在演示库里新增了 1 份简历（张测试）；后端没有删除简历的接口，所以保留。

---

## 7. 已知问题（不阻塞）

1. **列表只包含已解析档案。** 后端 `/api/resumes` 从 `parsed_resumes` 联表，待解析 / 失败的 ResumeFile 不会出现在列表里，只能在队列看到。页面文案与空态按这个事实写。
2. **两条种子数据「已完成但置信度为暂无」。** `raw_json.confidence` 缺失，UI 显示「暂无」，没有补 0。
3. **列表里有两条「程磊」。** 演示数据里同名的两份文件，来源文件名不同；后端没有合并/查重接口，UI 不做去重。
4. **上传是逐份请求。** 选 20 份会发 20 个请求，换来真实的逐条结果与「上传中 i/N」；不是一次批量。
5. **成功提示重复一次。** 对话框内和页面顶部各有一条「已接收 N 份」，关闭对话框后仍能看到页面提示；暂未做自动消失的 toast。
6. **768 隐藏 4 列**（专业、来源文件、创建时间、置信度），避免学历竖排与横向溢出；1440 九列齐全。
7. **390 未适配**（2026-11-03 决定暂缓），本轮不验收。
8. **详情里「优势」以「3.」开头** 是解析原文的残留编号，不是 UI 截断；人工修正可改。
9. **没有做简历删除**：后端只提供删除队列任务，没有删除简历档案的接口。

---

## 8. 截图

| 文件 | 说明 |
|---|---|
| `shots/resumes-1440.png` | 1440×900 暗色列表（8 份） |
| `shots/resumes-1440-light.png` | 1440×900 浅色列表 |
| `shots/resumes-768.png` | 768×1024，5 列精简 |
| `shots/resumes-upload.png` | 上传对话框空态 |
| `shots/resumes-uploaded.png` | 上传成功：已接收 1 份，队列 1 |
| `shots/resumes-overlimit.png` | 11 MB 文件被本地拦截 |
| `shots/resumes-queue.png` | 队列抽屉空态 |
| `shots/resumes-queue-task.png` | 队列抽屉含 1 条待解析任务 |
| `shots/resumes-parsed.png` | 解析完成：列表 8 份，新增张测试 |
| `shots/resumes-detail.png` | 详情抽屉（含选中行） |
| `shots/resumes-edit.png` | 修正档案表单 |
| `shots/resumes-empty-filter.png` | 搜索无结果空态 |
| `shots/resumes-error.png` | 列表请求失败 |
| `shots/resumes-403.png` | 业务负责人无 resume:view |
