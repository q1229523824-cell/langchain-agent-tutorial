# LangChain 1.2 Agent 学习项目

这是一个面向 Agent 开发实习的学习型作品集项目。它从模型调用开始，逐步实现具备工具调用、项目检索和多轮记忆能力的智能体。

学习本项目时，请配合阅读 [Day 1–2 学习讲义](docs/day01-day02-study-guide.md)和
[Day 3 持久化记忆讲义](docs/day03-persistent-memory.md)、
[Day 4 上下文工程讲义](docs/day04-context-engineering.md)和
[Day 5 Agentic RAG 讲义](docs/day05-agentic-rag.md)。

## 当前功能

- 使用 `ChatDeepSeek` 调用 DeepSeek 模型；
- 使用 LangChain 1.2 的 `create_agent` 构建 Agent；
- Agent 可调用安全计算、项目文本搜索、项目文件读取和项目知识检索工具；
- 使用本地 BM25 完成项目知识切块、Top-K 检索和文件行号引用；
- 使用 LangGraph `InMemorySaver` 按 `thread_id` 保存本次进程内的对话记忆；
- 使用 SQLite 保存用户与助手消息，重新启动后可恢复同一 `thread_id` 的对话；
- 使用摘要中间件压缩过长历史，并限制单轮模型和工具调用次数；
- 提供可交互 CLI，可切换会话、查看历史，并实时显示工具调用参数和结果；
- 文件工具限制在项目目录内，禁止读取 `.env`、隐藏文件和 IDE/Git 目录。

## 项目结构

```text
chapter01_summary/      # 环境与版本验证
chapter02_model/        # DeepSeek 模型调用示例
chapter03_agent/        # 最小项目学习 Agent
chapter04_rag/          # Day 5 本地知识库、切块和 BM25 检索
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
6. `interview_note`、`.env`、本地数据库及隐藏目录不会进入 RAG 或 Git。

## 后续计划

- 接入 Tavily 搜索，添加带来源的联网研究；
- 为 Agent 增加 token 级流式输出和异常重试；
- 接入 PostgreSQL checkpoint，实现跨进程会话记忆；
- 将 BM25 升级为 Embedding + 向量数据库，并加入重排；
- 添加 FastAPI 服务接口。
