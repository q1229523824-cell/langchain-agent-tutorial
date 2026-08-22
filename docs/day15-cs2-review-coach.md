# Day 15：RoundMind CS2 智能复盘教练

## 项目目标

RoundMind 将一场 CS2 比赛的结构化回合数据转换为中文复盘报告。它不是单纯的
数据看板，也不让大模型直接心算统计指标，而是演示一个可控的 Agent 工程：

1. 确定性程序计算 ADR、KAST、首轮交火、补枪、道具、经济和残局事实；
2. Planner 根据用户问题动态选择只读工具；
3. LangGraph 循环执行工具，但最多调用五次；
4. Reviewer 清理重复结论并校验回合编号；
5. Reporter 生成带具体回合引用的训练建议。

默认使用离线规则规划器，不调用 DeepSeek。只有显式添加
`--use-llm-planner` 时，才会把“用户问题和基础比赛统计”发送给 DeepSeek；不会发送
`.env`、项目文件或其他比赛数据。

## 执行流

```text
MatchRecord + question
          │
          ▼
prepare：计算基础统计
          │
          ▼
planner：动态选择 1～5 个只读工具
          │
          ▼
tool_executor：每次只执行一个工具
          │
          ├────还有工具且未超过上限────┐
          │                            │
          ▼                            │
reviewer：校验回合引用、去重和排序 ◀───┘
          │
          ▼
reporter：形成中文复盘和训练重点
```

这里的 Agent 位于工作流内部：外层 LangGraph 决定安全边界和退出条件，Planner
拥有“下一步使用什么工具”的局部决策权。这个混合设计比让模型自由循环更容易测试。

## 数据模型

MVP 接受结构化 JSON，而不是直接解析 `.dem`。这样可以先验证 Agent 产品闭环，后续
再把 Awpy 适配器接到 `MatchRecord`，下游工具和工作流无需修改。

核心回合字段：

```json
{
  "number": 3,
  "side": "T",
  "won": false,
  "kills": 0,
  "assists": 0,
  "died": true,
  "damage": 31,
  "opening_duel": "lost",
  "was_traded": false,
  "utility_damage": 0,
  "enemies_flashed": 0,
  "equipment_value": 4200,
  "clutch_attempted": false,
  "clutch_won": false,
  "note": "中路单摸，队友相距过远无法补枪。"
}
```

Pydantic 会校验：回合号不可重复、比分必须与回合胜负一致、未死亡不能被标记为
“已补枪”、未参与残局不能标记为残局获胜。

## 本地运行

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter07_cs2_coach.main
```

打开 `http://127.0.0.1:8000`。网页会自动加载 Mirage 示例并执行一次综合复盘。
Swagger 位于 `http://127.0.0.1:8000/docs`。

仓库同时提供 `chapter07_cs2_coach/Dockerfile`。构建上下文应选择仓库根目录，Dockerfile
路径选择该文件；容器会读取托管平台提供的 `PORT`，因此不需要硬编码线上端口。

明确允许 DeepSeek 获取当前问题与基础统计后，可以运行：

```powershell
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter07_cs2_coach.main --use-llm-planner
```

## 为什么这不是普通工作流

对问题“为什么我杀很多还是输了”，Planner 只选择 `clutches`；对“分析首杀和补枪”，
它选择 `opening_duels` 与 `tradeability`；综合复盘才调用全部工具。执行路径由当前问题
动态决定，同时工具白名单和最大调用次数由代码控制。

模型规划器启用后具有相同输出契约，即使返回无效 JSON、未知工具或空列表，也会降级到
离线规划器，避免整个请求失败。

## 面试表达

可以这样介绍项目：

> 我把 CS2 复盘拆成确定性统计层和 Agent 决策层。LangGraph 管理 Planner、工具循环、
> Reviewer 和 Reporter。Agent 只能从五个只读工具中动态选择，最多调用五次；所有结论
> 都需要绑定真实回合编号。默认模式完全离线，模型规划失败时可降级，因此结果可测试、
> 可追溯，也不会因为模型不可用而失去核心功能。

可以主动说明的工程取舍：

- 先支持 JSON 是为了验证闭环，下一阶段再接 Awpy `.dem` 解析；
- 当前比赛仓库在内存中，生产版应替换为 PostgreSQL 和对象存储；
- 当前建议来自规则模板，后续 LLM 只能润色已审核事实，不能修改指标；
- 真实上线需要登录、配额、异步解析、文件病毒扫描和删除策略；
- 评测应覆盖工具选择准确率、数值一致率、回合引用准确率和建议相关性。
