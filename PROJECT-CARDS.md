<!-- deep-ptc:project-cards v1 next=R1,F2,Q1,T6 -->
# Project cards

> Maintained by Deep PTC in DeepSeek Harness: edit in a Deep PTC conversation, view 特点卡片 / Project cards.
> User-approved settings guide this project. Features and requirements are records that can be checked and corrected.

## Completed tasks / 已完成任务
<!-- card id=tasks kind=tasks rev=5 updated=2026-11-25T14:56:03.628Z -->

- **T1** [done] 讨论人才项目是否有必要接入 ChatAI，并确定功能边界。 — ChatAI 首期开发与隔离验收完成，10 项后端测试、前端构建与 Chrome 合成数据验收通过；真实服务部署联调单独记录。 (11/25)
- **T2** [done] 梳理 ChatAI 距离上线还未完成的事项。 — 已核实当前 AI 网关 JSON、SSE 可用，用户提供的备用网关可用；MySQL 缺聊天表、Milvus 不可用，已更新上线验收清单。 (11/25)
- **T3** [done] 对整个人才平台进行测试和完善，确保达到真实落地运行条件。 — 完成全平台核心业务隔离回归与修复，285 项检查通过，真实 ChatAI、向量和浏览器验证通过，目标服务健康，正式上线条件已记录。 (11/25)
- **T4** [done] 把当前工作区 E:\AI数字化人才平台-相关文档 的项目提交到用户的 GitHub 账号，由 AI 新建一个公开仓库并推 — 已创建公开仓库 moliclay/ai-digital-talent-platform 并推送 447 个文件（2.71MB），远端与本地 commit cdd2c92 一致。 (11/25)
- **T5** [done] 将前端验收流程写入用户级全局 Skill，供今后的前端设计任务跨项目使用。 — 已安装并验证用户级前端视觉验收 Skill，要求真实浏览器截图、子代理首评、修改后重截图与复评，无新增问题方可交付。 (11/25)


## Implemented features / 已实现功能
<!-- card id=features kind=features rev=2 updated=2026-11-26T01:13:51.628Z -->

- **F1** Windows 一键启动.bat、一键停止.bat 调用 scripts/windows/_services.ps1。启动复用本工作区进程并检查前端 HTTP 和后端 MySQL 健康；MySQL 未监听时，失效的 MYSQL_HOME 会给出警告并回退到项目默认安装路径。停止只结束本工作区启动包装脚本的进程树。已实测失效路径下的冷启动、重复启停、外部端口冲突、数据库连接失败和共享依赖进程保留。
