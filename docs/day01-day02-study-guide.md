# Day 1–2 学习讲义：从模型调用到可交互 Agent

## 学习目标

完成这两天后，你应该能不看答案讲清楚并重新实现：

1. 普通大模型调用和 Agent 的区别；
2. `create_agent`、模型、工具、系统提示词之间的关系；
3. `@tool` 如何把 Python 函数变成模型可调用的工具；
4. `thread_id` 和 checkpointer 如何实现多轮短期记忆；
5. 为什么工具需要路径校验、输入限制和错误处理；
6. 如何用测试验证工具，而不是只看一次运行结果。

## Day 1：最小 Agent

### 1. 普通模型与 Agent

普通模型调用：

```text
用户问题 → 模型 → 文本回答
```

Agent：

```text
用户问题 → 模型判断 → 调用工具 → 获得工具结果 → 模型组织最终回答
```

模型并不能直接读取电脑文件。`search_project_files` 和 `read_project_file` 是我们明确授予它的能力。

### 2. 需要掌握的代码

- `build_agent()`：组装模型、工具、记忆和系统提示词；
- `@tool`：声明工具名称、参数和描述；
- `search_project_files()`：搜索允许类型的项目文本；
- `read_project_file()`：读取文件并阻止目录越界；
- `calculate()`：通过 AST 计算表达式，不执行任意 Python 代码。

### 3. 面试表达

> 我使用 LangChain 1.2 的 `create_agent` 构建了一个项目学习助手。模型可以自主选择项目搜索、文件读取和计算工具。我给文件工具添加了目录边界和敏感文件限制，并使用 AST 替代 `eval`，降低任意代码执行风险。

## Day 2：多轮记忆与可观察性

### 1. `thread_id` 的作用

`thread_id` 是会话编号。同一个编号会读取同一份历史；不同编号相互隔离：

```text
thread_id=study       → 学习会话的消息历史
thread_id=interview   → 面试会话的消息历史
```

`InMemorySaver` 只保存在当前 Python 进程内，退出后数据消失。生产环境通常替换为数据库 checkpointer。

### 2. 工具调用日志

`stream_mode="updates"` 会在 Agent 每个步骤完成后产生更新：

```text
model → AIMessage(tool_calls=[...])
tools → ToolMessage(工具执行结果)
model → AIMessage(最终回答)
```

CLI 将这些更新格式化为 `[工具调用]` 和 `[工具结果]`，便于调试模型是否选对工具、参数是否正确、工具返回了什么。

### 3. 面试表达

> 我使用 LangGraph 的 `InMemorySaver` 和 `thread_id` 实现会话级短期记忆，并通过 Agent 的 updates 流输出工具调用参数和结果。这样既能支持多轮对话，也能观察 Agent 的执行路径并定位工具选择错误。

## 正确的学习方法

每个功能使用四步学习法：

1. **运行**：先运行测试和演示，观察输入、日志、输出；
2. **追踪**：从 `main()` 开始，逐函数追踪调用链；
3. **改写**：关闭原文件，自己写一个只含计算器的最小 Agent；
4. **解释**：用两分钟口述设计、风险和取舍。

不要背完整代码。重点记住组件关系和解决问题的思路。

## 今日动手练习

### 练习一：验证同一会话有记忆

```text
[default] 你> 我叫小王，请记住。
[default] 你> 我叫什么？
```

### 练习二：验证不同会话隔离

```text
/thread interview
你> 我叫什么？
```

新会话不应该自动知道 `default` 会话中的名字。

### 练习三：触发工具日志

```text
你> 请使用计算工具计算 (15 + 5) * 3
```

观察 `[工具调用] calculate` 的参数和 `[工具结果]`。

### 练习四：自己添加工具

添加一个 `count_text(text: str)` 工具，返回字符数和单词数，并为它编写至少两个测试。

## 自测题

在不看源码的情况下回答：

1. 为什么模型不能直接读取 Notebook？
2. `@tool` 的 docstring 为什么重要？
3. 为什么计算器不直接使用 `eval`？
4. 两个用户使用相同 `thread_id` 会有什么风险？
5. 为什么 `InMemorySaver` 不适合多实例生产服务？
6. Agent 调错工具时，你会从哪些日志开始排查？

如果六题中至少五题能独立回答，并能完成 `count_text` 工具，你才算真正掌握 Day 1–2。

## Git 的核心模型

```text
工作区 --git add--> 暂存区 --git commit--> 本地仓库 --git push--> GitHub
```

- 工作区：正在编辑的文件；
- 暂存区：明确选择这次要提交的文件；
- 本地提交：一份带说明、可回退的版本快照；
- GitHub：远端仓库，用于备份、展示和协作。

推荐的第一次提交命令：

```powershell
git init
git status
git add .gitignore README.md requirements.txt chapter01_summary chapter02_model chapter03_agent tests docs
git diff --cached
git commit -m "feat: build a DeepSeek project learning agent"
```

推送前必须检查：

```powershell
git status
git ls-files .env
```

第二条命令必须没有输出，确保 API Key 没被纳入 Git。
