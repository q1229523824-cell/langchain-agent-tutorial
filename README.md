# LangChain 1.2 Agent 工程学习项目

这是一个面向 Agent 开发实习的学习型作品集项目。项目从 DeepSeek 模型调用开始，逐步实现项目学习 Agent、电商客服 Agent，以及具备动态工具规划、证据审核和网页界面的 CS2 智能复盘教练。

学习本项目时，请配合阅读 [Day 1–2 学习讲义](docs/day01-day02-study-guide.md)和
[Day 3 持久化记忆讲义](docs/day03-persistent-memory.md)、
[Day 4 上下文工程讲义](docs/day04-context-engineering.md)和
[Day 5 Agentic RAG 讲义](docs/day05-agentic-rag.md)、
[Day 6 安全退款 Agent 讲义](docs/day06-safe-refund-agent.md)以及
[Day 14 电商客服 Agent 完整讲义](docs/day14-ecommerce-agent.md)和
[Day 15 CS2 智能复盘教练讲义](docs/day15-cs2-review-coach.md)。

## 当前功能

- 使用 `ChatDeepSeek` 调用 DeepSeek 模型；
- 使用 LangChain 1.2 的 `create_agent` 构建 Agent；
- Agent 可调用安全计算、项目文本搜索、项目文件读取和项目知识检索工具；
- 使用本地 BM25 完成项目知识切块、Top-K 检索和文件行号引用；
- 使用 LangGraph `InMemorySaver` 按 `thread_id` 保存本次进程内的对话记忆；
- 使用 SQLite 保存用户与助手消息，重新启动后可恢复同一 `thread_id` 的对话；
- 使用摘要中间件压缩过长历史，并限制单轮模型和工具调用次数；
- 使用独立退款业务服务演示资格校验、二次确认、幂等执行和退款状态机；
- 高风险模拟退款只能通过确定性 CLI `/confirm` 命令触发，模型没有直接退款权限；
- 提供可交互 CLI，可切换会话、查看历史，并实时显示工具调用参数和结果；
- 文件工具限制在项目目录内，禁止读取 `.env`、隐藏文件和 IDE/Git 目录。
- 使用显式 LangGraph Router 将请求分配给商品、政策、订单、退款和安全节点；
- 使用 BM25、本地哈希向量、RRF 融合和轻量 Reranker 完成混合检索；
- 使用 FastAPI 暴露聊天、订单、退款确认、指标和 Trace 接口；
- 使用原子问答写入、用户/会话双重隔离、滑动窗口限流和结构化运行指标；
- 提供完全离线的端到端演示与评测集，默认不产生 DeepSeek API 费用。
- 提供 RoundMind CS2 复盘网页，Agent 可按问题动态选择首轮交火、补枪、道具、经济和残局工具；
- CS2 结论经过 Reviewer 校验并绑定具体回合，默认完全离线运行。

## 项目结构

```text
chapter01_summary/      # 环境与版本验证
chapter02_model/        # DeepSeek 模型调用示例
chapter03_agent/        # 最小项目学习 Agent
chapter04_rag/          # Day 5 本地知识库、切块和 BM25 检索
chapter05_refund/       # Day 6 安全退款 Agent 与本地模拟业务服务
chapter06_ecommerce/    # Day 14 电商工作流、混合检索、API、评测和可观测性
chapter07_cs2_coach/    # Day 15 CS2 复盘 Agent、分析工具、API 和网页
tests/                  # 不调用 API 的本地工具测试
```

## 环境配置

本项目使用 Conda 环境 `langchain1.2`。创建项目根目录下的 `.env`：

```env
DEEPSEEK_API_KEY=你的密钥
DEEPSEEK_BASE_URL=https://api.deepseek.com
```

`.env` 已在 `.gitignore` 中，不能提交到 GitHub。

## 运行

先运行不产生 API 消耗的本地测试：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m unittest discover -s tests -v
```

运行可交互 Agent（会向 DeepSeek 发送提示词和被 Agent 读取到的允许范围内文件内容）：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" chapter03_agent\project_learning_agent.py
```

CLI 支持以下命令：

```text
/thread <名称>  切换或创建指定 thread_id 会话
/new            创建一个新会话
/threads        查看已有会话
/history        查看当前会话历史
/clear          清空当前会话并切换到空会话
/help           查看帮助
/quit           退出
```

运行两轮自动演示，观察计算工具调用日志和 `thread_id` 记忆。该演示不会读取项目文件：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" chapter03_agent\project_learning_agent.py --demo
```

运行 Day 6 本地退款黑盒演示。它不调用 DeepSeek、不连接真实支付渠道，也不产生真实资金变化：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" chapter05_refund\refund_agent.py --demo
```

运行 Day 6 可交互 Agent（普通问答会调用 DeepSeek，`/confirm` 只执行本地模拟退款）：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" chapter05_refund\refund_agent.py
```

运行 Day 14 完全离线的电商端到端演示：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --demo
```

运行离线路由与检索评测：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --eval
```

启动 FastAPI（默认使用确定性回答模板，不调用外部模型）：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --api
```

访问 `http://127.0.0.1:8000/docs` 查看 Swagger。演示接口使用请求头
`X-Demo-Token: demo-user-token`，生产环境必须替换为真正的 JWT/OAuth/session。

只有明确允许把当前问题、最近六条消息和必要证据发送给 DeepSeek 时才启用：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --api --use-llm
```

启动 RoundMind CS2 智能复盘教练（默认完全离线）：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter07_cs2_coach.main
```

访问 `http://127.0.0.1:8000`。网页内置一场 Mirage 示例比赛，也支持上传符合
`MatchRecord` 格式的 JSON。原始 `.dem` 接入属于下一阶段，当前版本不会伪装成已经支持。

`InMemorySaver` 保存当前 Python 进程的完整图状态；SQLite 保存可跨进程恢复的用户与助手文本。
本地数据库默认位于 `.agent_data/chat_history.db`，不会提交到 GitHub。生产环境可进一步换成
PostgreSQL checkpointer 持久化完整图状态。

Day 4 默认在状态消息达到 30 条时摘要旧历史并保留最近 12 条，同时限制单轮最多 8 次模型调用和
6 次工具调用。可通过以下参数调整：

```text
--summary-trigger-messages
--summary-keep-messages
--model-call-limit
--tool-call-limit
```

## 技术亮点

这个项目没有直接让模型访问整个磁盘或执行命令。每个工具都有明确输入、范围限制和错误处理：

1. Agent 只能通过工具获得项目内容；
2. 文件读取会校验路径，避免 `../` 越界；
3. 计算器通过 Python AST 解析表达式，不使用 `eval`；
4. 短期记忆通过 `thread_id` 隔离，便于后续替换为 PostgreSQL 持久化；
5. RAG 只索引允许的项目文本，返回 Top-K 证据和精确到行的来源；
6. `interview_note`、`.env`、本地数据库及隐藏目录不会进入 RAG 或 Git；
7. 模型可查询订单和准备退款，但不能直接执行高风险副作用；
8. `confirmation_id` 绑定用户、订单、金额和过期时间，幂等键防止重复退款；
9. SQLite 事务、唯一约束和状态事件保证并发安全与可追踪性。
10. 商品价格和库存只来自业务服务，政策结论必须带可追溯引用；
11. 高风险退款确认独立于自然语言路由，模型没有直接写权限；
12. Trace 只保存路由、耗时和引用等元数据，不保存原始问题；
13. 离线评测覆盖路由准确率、Retrieval Hit Rate@3 和危险请求阻断率。

## 生产化边界

- 当前身份系统是本地 demo token，不是真实登录认证；
- 默认向量编码器是可离线测试的本地哈希向量，不是神经网络 Embedding；
- SQLite 和 `InMemorySaver` 适合单机作品演示，生产环境应换成 PostgreSQL；
- 退款渠道是本地模拟器，不连接真实支付和资金系统；
- 生产环境还需要分布式限流、密钥管理、回调验签、对账、告警和数据脱敏。
