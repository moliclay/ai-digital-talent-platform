# AI 简历解析超时修复

> 日期：2026-11-04 ｜ 类型：bug 修复 ｜ 影响范围：所有 AI 文本调用（简历解析、JD 解析、画像、简答评分、题库导入）

## 1. 现象

真实 PDF 简历（`ai应用开发简历.pdf`，程磊，1930 字正文）解析后：

```
education = ''      ← 学历为空
years_experience=0
confidence = 0.25
ai_fallback = false ← AI 兜底从未生效
evidence = {"major":"词表命中：软件工程","skills":"词典命中 22 项"}
```

正文里明明有 `2022.09-2026.06 湖南工学院 网络工程`，但规则抽不到学历（因为没有「学历」字样），
本该由 AI 兜底补上，实际没补。

## 2. 定位过程

### 2.1 先排除「AI 不可用」

| 检查 | 结果 |
|---|---|
| `settings.ai_enabled` | True |
| API Key 长度 | 39，有效 |
| `/v1/models` | 45 个模型可列出 |
| `gateway.available` | True |
| `_ai_extract` 短文本 | ✅ 字段全对 |

短简历文本 5 次调用 5/5 成功（平均 8.8s），说明 AI 本身没问题。

### 2.2 真实正文稳定失败

同一份 1930 字正文连跑 5 次：

```
#1 FAIL 37.1s   #2 FAIL 25.0s   #3 FAIL 25.0s   #4 FAIL 25.0s   #5 FAIL 25.0s
成功 0/5
```

### 2.3 分层定位到超时预算

绕过 `gateway.chat` 的重试逻辑，直接打网关测各层真实延迟：

| 场景 | 实际耗时 | 当时预算 | 结果 |
|---|---|---|---|
| 主模型 / 短文本 | 32.7s | 12s | 超时 |
| 主模型 / 真实全文 | **15.3s** | **12s** | **超时** |
| 备用模型 / 短文本 | 6.3s | 25s | 通过 |
| 备用模型 / 真实全文 | **47.3s** | **25s** | **超时** |

## 3. 根因

`app/infrastructure/ai_gateway.py` 两处硬编码：

```python
# 主模型
timeout=min(settings.ai_timeout, 25 if use_fallback_directly else 12)
# 备用模型
timeout=min(settings.ai_timeout, 25)
```

`settings.ai_timeout=90` 被 `min()` 压成 **主模型 12s / 备用 25s**。
而主模型处理 1930 字正文需 15.3s、备用需 47.3s，**两层都超预算**，所以必然返回 `None`。

短简历能成功是因为文本短、模型 2–8s 就返回——**掩盖了这个 bug**。

## 4. 修复

### 4.1 超时改成可配置

`app/core/config.py`：

```python
# 总预算：主模型失败后还要留时间给备用模型，所以是两者之和的上限
ai_timeout: int = _env("AI_TIMEOUT", "120")           # 原 60
ai_timeout_primary: int = _env("AI_TIMEOUT_PRIMARY", "45")    # 新增
ai_timeout_fallback: int = _env("AI_TIMEOUT_FALLBACK", "60")  # 新增
```

`ai_gateway.py` 两处改为：

```python
# 主模型（含熔断后直接走备用的情况）
timeout = min(settings.ai_timeout, settings.ai_timeout_fallback if use_fallback_directly
              else settings.ai_timeout_primary)
# 备用模型
timeout=min(settings.ai_timeout, settings.ai_timeout_fallback)
```

生效值：**主模型 45s / 备用模型 60s**（`.env` 的 `AI_TIMEOUT=90` 只作总上限）。

### 4.2 顺带修中文键名静默失效

网关有时返回中文键（实测到一次）：

```json
{"姓名":"张伟","学历":"硕士","工作经验":"5年","技能":["Python"]}
```

而 `_extract_json` 不做键名归一化，调用方 `ai_fields.get("name")` 拿到 `None` →
**兜底静默失效，且 `ai_fallback` 仍为 True**（因为 `ai_fields` 非空）。

修复：在 `AiResult.json()` 出口加中文→英文别名映射（`_CN_KEY_ALIASES` + `_normalize_keys`）。

设计要点：

| 点 | 做法 | 原因 |
|---|---|---|
| 位置 | 只放在 `AiResult.json()` 出口 | 7 处调用方（简历/JD/画像/评分/题库）全部自动受益，无需改调用方 |
| 覆盖 | 姓名/电话/邮箱/学历/专业/年限/技能/优势 + 题目/答案/选项/分值/解析等 | 题库导入也用 `.json()` |
| 冲突 | **英文键优先**（`setdefault`） | 模型同时给两种键时不覆盖已正确的英文值 |
| 嵌套 | dict/list 递归处理 | 模型可能嵌套输出 |

## 5. 验证

### 5.1 超时修复（真实 PDF 正文）

```
#1 OK 12.4s education='本科' name='程磊'
#2 OK 10.5s education='本科' name='程磊'
#3 OK 12.6s education='本科' name='程磊'
3/3 成功（修复前 0/5）
```

### 5.2 中文键归一化（离线）

```
{'姓名':'张伟','学历':'硕士','工作经验':'5年','技能':['Python']}
→ {'name':'张伟','education':'硕士','years_experience':'5年','skills':['Python']}

{'name':'王五','姓名':'李四'} → {'name':'王五'}          ← 英文优先
[{'题干':'题1','答案':'A'}] → [{'content':'题1','answer':'A'}]  ← 列表递归
```

### 5.3 降级路径未被破坏

AI 关闭（Key 置空）时：

```
gateway.available=False
ok=True ai_fallback=False conf=0.75 耗时=0.01s
fields={'name':'张伟','education':'硕士','major':'计算机科学与技术'}
```

规则照常工作，且**不会白等超时**。

### 5.4 重解析真实数据

重置 `parse_tasks(resume_id=35)` 为 `waiting` → `POST /api/resumes/parse-next`：

```
耗时 11.6s
fields: education='本科'  ← AI 兜底补回
confidence: 0.25 → 0.75
ai_fallback: False → True
evidence: {"education": "AI 兜底：本科", "name": "AI 兜底：程磊", "skills": "词典命中 22 项；AI 补充 15 项"}
```

简历列表复核：

```
  id 姓名   学历  专业        年限  技能  置信度
  35 程磊   本科  软件工程      0   22   0.75   ← 已修复
   7 王峰   本科  信息管理      6    3   1.0
   6 陈宇   硕士  计算机科学     5    5   1.0
   5 刘洋   本科  信息管理与信息系统 6   4   1.0
   4 李娜   本科  软件工程      3    6   1.0
   3 张伟   硕士  计算机科学与技术  5   10   1.0

学历为空的简历：0 份
```

### 5.5 全量回归

12 个脚本 196 项断言全绿（见交付说明）。

## 6. 副作用与注意

| 项 | 说明 |
|---|---|
| 解析变慢 | 走 AI 兜底的简历从 ~0.1s 变成 10–15s。这是**必要代价**——之前是「假快」（直接失败） |
| 队列超时 | 前端轮询 `parse-next` 的 HTTP 超时要 > 60s，否则会客户端超时（服务端仍在跑） |
| 熔断机制 | 主模型失败后 3 分钟内直接走备用（备用更慢，47s），此时单次调用可能耗时 47s |
| `years_experience=0` | 应届生（2022.09-2026.06 在读）判 0 年合理，不是 bug |
| 中文键映射表 | 新增字段时记得同步 `_CN_KEY_ALIASES`，否则仍会静默失效 |

## 7. 改动文件

| 文件 | 改动 |
|---|---|
| `app/core/config.py` | `ai_timeout` 60→120；新增 `ai_timeout_primary=45`、`ai_timeout_fallback=60` |
| `app/infrastructure/ai_gateway.py` | 两处超时读配置；新增 `_CN_KEY_ALIASES` + `_normalize_keys`；`AiResult.json()` 出口归一化 |
| 数据 | 重解析 `parsed_resumes.id=35`（education 补回本科） |
| `.env` | **未改**（`AI_TIMEOUT=90` 保留作总上限） |

## 8. 后续建议

1. **前端轮询超时**设到 90s 以上，或改成「提交后异步查询任务状态」；
2. 简历量大时可考虑把 AI 兜底移到后台队列（现在是同步等待）；
3. 备用模型 `Doubao-Seed-2.1-Pro` 处理长文本要 47s，若主模型稳定可考虑不启用备用；
4. `AI_TIMEOUT_PRIMARY` / `AI_TIMEOUT_FALLBACK` 已进配置，网关变慢时**只改 `.env` 即可**，不用改代码。

---

## 9. 连带修复：身份去重未迁移关联数据（2026-11-04 追加）

### 9.1 怎么发现的

重解析 `id=35` 后跑回归，`s5_onboard_test` 报：

```
AttributeError: 'NoneType' object has no attribute 'get'
POST /api/prejob-plans/generate → 404「候选人还没有画像，先去「人才画像」生成」
```

但程磊**有**画像——只是画像挂在**旧简历 `id=8`** 上。

### 9.2 根因

`identity_service.reconcile_identity()` 只做三件事：

```python
row.is_current = False
row.superseded_by = int(newest.id)
```

**不迁移任何关联数据。** 而以下 8 张表通过 `candidate_id` / `parsed_resume_id` 指向 `parsed_resumes`：

```
talent_profiles         candidate_id
prejob_plans            candidate_id
growth_ledger           candidate_id
exam_assignments        parsed_resume_id
exam_submissions        parsed_resume_id
exam_interview_results  candidate_id
match_lists             candidate_id
match_results           parsed_resume_id
```

所以同一人传了新简历后：**画像/计划/台账/测评绑定/匹配记录全部留在一份「列表里看不到」的旧简历上**，
用户视角就是「这个人突然没有画像了」。

实测数据（修复前）：

```
程磊：talent_profiles 旧(id=8)=1 新(id=35)=0
     prejob_plans    旧(id=8)=1 新(id=35)=0
     exam_assignments 旧(id=8)=1 新(id=35)=0
陈宇（1→6）、王峰（2→7）同样
```

### 9.3 修复

`identity_service.py` 新增 `migrate_links(db, old_id, new_id)`：

| 表类型 | 策略 |
|---|---|
| `talent_profiles` / `growth_ledger`（一人一条语义） | **新简历已有则不动旧的**（保留新数据，旧画像靠列表过滤隐藏） |
| `prejob_plans` / `exam_*` / `match_*`（可多条） | 直接按行迁移 |

技术细节：

- 每张表用 `db.begin_nested()`（savepoint）包住：**某张表失败只回滚这张表**，不牵连已完成的迁移；
- 表名/列名来自常量白名单 `_LINKED_TABLES`，无注入风险；
- 接入两处入口：`reconcile_identity()`（单份简历落库时）与 `reconcile_all()`（历史数据全量重算）。

### 9.4 修复后

```
reconcile_all: total=9 keyed=9 superseded=3
moved: {'prejob_plans': 18, 'growth_ledger': 1, 'match_lists': 1,
        'match_results': 1, 'talent_profiles': 1, 'exam_assignments': 1}

程磊：旧(id=8) 全部归 0，新(id=35) 画像=1 计划=1 测评=1 匹配=2
```

列表复核：

```
画像 total=6  ['程磊','王峰','陈宇','刘洋','李娜','张伟']
简历 total=6  ['程磊','王峰','陈宇','刘洋','李娜','张伟']
```

### 9.5 残留说明

`talent_profiles.id=1`（陈宇旧简历的画像）仍留在库里，内容与新画像 `id=5` **完全相同**（五维数据一字不差）。
不删的理由：留追溯。靠 `list_profiles` 的 `is_current` 过滤使其不显示。

### 9.6 备份

改动前已备份：`backup/ai_talent_20261104_before_linkmigrate.sql`（279,149 字节）

---

## 10. 修复过程中暴露的测试脚本问题（一并修了）

### 10.1 `s3_identity_test.py` 清理失败 → 残留简历

**现象**：跑完 s3 后库里多了 `张伟` 两条现行简历（id=39/40/41/42），s7 报「列表默认无重复姓名」失败。

**原因**：cleanup 只删了 `parse_tasks` / `parse_logs` / `parsed_resumes`，
但迁移后 `match_results` 等子表也有数据指向该简历，外键约束报 1451：

```
Cannot delete or update a parent row: a foreign key constraint fails
(`ai_talent`.`match_results`, FOREIGN KEY (`parsed_resume_id`) REFERENCES `parsed_resumes`)
```

事务整体回滚 → 简历没删掉。

**修复**：删除前先按「全部引用列」删子表数据。特别注意
`match_lists` 同时有 `candidate_id` 和 `parsed_resume_id` 两列，**两列都要删**。

### 10.2 `s5_onboard_test.py` 直接转正真实候选人

**现象**：s5 跑完留下 `13973951702`（程磊）、`13900000002`（王峰）两个员工账号，
smoke 的 `管理员可读系统用户 total == 4` 失败。

**原因**：s5 原来从简历列表里挑一个真实候选人转正，中途崩溃就留下账号；
即使成功，cleanup 也只是「解除绑定」而不是删账号+删简历。

**修复**：

1. 改为**上传临时简历**（随机手机号 + `转正测试xxxx` 姓名）再转正，不碰真实数据；
2. cleanup 改为删除账号 + 删除临时简历及其全部关联数据；
3. 补上 `POST /api/talent-profiles/generate`（培养计划依赖画像，缺画像 404）。

### 10.3 `training_test.py` 硬编码 `candidate_id=1`

**现象**：`IndexError: list index out of range`（台账为空）。

**原因**：陈宇的旧简历是 `id=1`，已被 `id=6` 替代，`growth_ledger` 随迁移挂到了 `id=6`，
测试还查 `candidate_id=1` → 空。

**修复**：动态解析「陈宇 + is_current」的简历 id，不再硬编码。

### 10.4 `smoke_test.py` 硬编码 `total == 4`

**现象**：转正建号后用户数变多，断言失败。

**原因**：`total == 4` 假设用户数恒定，但转正是正常业务行为。

**修复**：改为「能读到且包含基线 4 个账号」，`len(users) >= 4 and {4 个用户名} <= names`。

## 11. 本次修复的完整清单

| 文件 | 改动 |
|---|---|
| `app/core/config.py` | 新增 `ai_timeout_primary` / `ai_timeout_fallback`，`ai_timeout` 60→120 |
| `app/infrastructure/ai_gateway.py` | 超时读配置；`_CN_KEY_ALIASES` + `_normalize_keys`；`AiResult.json()` 归一化 |
| `app/services/identity_service.py` | 新增 `migrate_links()`（8 张关联表 + 转正关系），接入 `reconcile_identity` / `reconcile_all` |
| `scripts/s3_identity_test.py` | 清理时先删全部引用列的子表数据 |
| `scripts/s5_onboard_test.py` | 改上传临时简历；cleanup 删账号+删简历；补画像生成 |
| `scripts/training_test.py` | `candidate_id` 动态解析 |
| `scripts/smoke_test.py` | 用户数断言放宽为「含基线 4 个」 |

数据修复：`reconcile_all()` 迁移 22 条关联数据；重解析 `id=35` 补回学历；清理测试残留。
