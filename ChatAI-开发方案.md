# ChatAI 首期开发方案

## 产品边界
HR 人才业务助手。支持只读人才查询、语义检索、岗位匹配解释、画像分析、岗位缺口统计、多轮追问、历史会话恢复。继承现有 React/FastAPI/MySQL/Milvus 与 AI 网关。Base 仅作参考。

## 技术设计
- 会话与登录独立，MySQL 保存会话和对话。用户身份从 JWT 取得，按会话归属限制访问。员工不开放入口。
- 每条问题进行长度、格式、权限及规则审核，高风险问题模型审核，审核失败或不可用时拒绝高风险请求。
- 最近 5 轮合法完成的问答、有限长度结构化条件和对象 ID 作为上下文。按需改写，无法消歧时追问。模型输出只能作为受控查询参数，重新验证字段及对象权限。
- 业务查询采用固定意图及参数，使用已有服务与 ORM，禁止自由 SQL 和写业务操作。查询与来源引用均按当前数据权限过滤，避免发送联系方式、完整简历等非必要敏感数据。恢复历史时重新检查引用权限，权限变化的内容应隐藏。
- 模型使用已有 AI 网关配置，支持真实 SSE 输出，失败或取消时记录状态，已有输出后禁止模型自动重试。数据源不可用明确反馈。无模型时可对已确定的业务结果提供确定性文字反馈。
- 首期持久化会话内记忆，不建聊天向量索引，不接入云端审核或多 Agent，不展示模型内部推理过程。

## API 契约
均使用现有 Bearer Token。普通接口沿用统一响应 {code,message,data}（具体键沿用现有 response.py）。

| 方法 | 路径 | 请求与结果 |
|---|---|---|
| GET | /api/chat/sessions | data 为会话数组，每项 id,title,created_at,updated_at |
| POST | /api/chat/sessions | 可选 title，data 为会话对象 |
| GET | /api/chat/sessions/{id} | data 为 {session,conversations}，对话字段 id,question,rewritten_question,answer,status,source_refs,created_at,error_code |
| DELETE | /api/chat/sessions/{id} | 删除本人会话及其对话 |
| POST | /api/chat/sessions/{id}/messages | {question}，SSE 流 |

SSE 使用 data: JSON + 空行，事件通过 type 字段区分。meta 包含 conversation_id 和 session_id，delta 包含 text，sources 包含 source_refs 数组（每条 type,id,label，可附 path），done 包含 status，error 包含 code,message。若 HTTP 层返回普通错误，客户端显示错误内容。客户端支持停止生成、失败提示、历史恢复与防重复发送。

## 验收与阶段
1. 数据模型、迁移、认证、会话 CRUD 与归属验证。
2. 审核、会话记忆、结构化意图及受控查询。测试歧义、跨部门、越权和业务只读性。
3. AI 网关 SSE、异常处理、取消、持久化来源和状态。
4. 沿用现有页面的主题、组件、路由、角色入口，提供聊天历史、空状态、快捷问题、发送、停止、引用和异常提示。
5. 隔离数据库测试、前端构建、接口与浏览器联调，记录真实运行证据，逐项更新 TODO。

迁移采用增量、幂等方式，不重置现行数据库。模型配置与真实数据访问按当前授权环境验证，测试优先使用合成记录。

## 启动与验证

从项目根目录运行以下命令。

```powershell
# 隔离测试与前端构建
backend/.venv/Scripts/python.exe tests/backend/test_chat.py
npm --prefix frontend run build
node tests/frontend/chat-smoke.mjs

# 确认 backend/.env 指向目标开发数据库后执行增量迁移
backend/.venv/Scripts/python.exe backend/scripts/migrate_chat.py
```

重启现有前后端后，HR 或具备业务查看权限的管理员可从侧栏进入 ChatAI 人才助手（/chat）。沿用既有 AI 网关与向量配置。模型不可用时，意图理解会提示暂不可用，高风险审核失败时拒绝请求。

验收状态见 [ChatAI-TODO.md](ChatAI-TODO.md)。隔离后端共 10 项通过，前端构建成功，Chrome 合成数据交互通过。目标数据库迁移及真实服务联调仍待部署环境验收。
