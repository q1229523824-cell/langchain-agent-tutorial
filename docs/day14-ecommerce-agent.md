# Day 14：星河商城电商客服 Agent

## 项目定位

这是一个面向求职作品集的电商客服 Agent 原型，支持商品推荐、政策问答、订单查询和安全退款。核心目标不是让模型拥有更多权限，而是让大模型在可验证的知识、可信业务数据和确定性工作流内工作。

它解决五类电商痛点：

1. 商城政策多且频繁更新，纯模型回答容易过时或编造；
2. 商品价格、库存和订单状态属于实时业务事实，不能让模型猜测；
3. 多轮客服在程序重启或切换会话后容易丢失上下文；
4. 退款具有真实副作用，需要身份隔离、二次确认、幂等和审计；
5. Agent 只看最终回答难以排错，需要 Trace、指标和离线评测。

## 可演示任务

```text
“预算500元，推荐适合通勤的降噪耳机”
“第一个多少钱，还有库存吗？”
“满多少金额可以包邮？”
“查询订单 order-1001”
“order-1001 能不能退款？”
“我要退款 order-1001”
```

自然语言最多只能生成待确认记录。真正的本地模拟退款必须调用独立确认接口。

## 总体架构

```mermaid
flowchart LR
    U["用户 / Swagger / CLI"] --> API["FastAPI + Pydantic"]
    API --> AUTH["Demo Token → 服务端 user_id"]
    AUTH --> RATE["滑动窗口限流"]
    RATE --> RT["EcommerceAgentRuntime"]
    RT --> G["LangGraph Router"]

    G --> SAFE["Safety Agent"]
    G --> POLICY["Policy Agent"]
    G --> CATALOG["Catalog Agent"]
    G --> ORDER["Order Agent"]
    G --> REFUND["Refund Agent"]

    POLICY --> HYBRID["BM25 + Hash Vector + RRF + Reranker"]
    HYBRID --> KB[("电商知识库")]
    CATALOG --> PRODUCT[("商品目录")]
    ORDER --> BIZ[("SQLite 业务库")]
    REFUND --> BIZ

    RT --> CHAT[("SQLite 会话库")]
    RT --> TRACE["Trace + Metrics"]
    RT --> LLM["可选 DeepSeek 语言润色"]

    API -->|"独立确认接口"| CONFIRM["RefundService.confirm_and_execute"]
    CONFIRM --> BIZ
```

## 一次政策问答的 Data Lineage

```mermaid
sequenceDiagram
    participant User as 用户
    participant API as FastAPI
    participant Runtime as Runtime
    participant Graph as LangGraph
    participant RAG as Hybrid Retriever
    participant DB as SQLite Chat
    participant Trace as Trace Store

    User->>API: 满多少金额可以包邮？
    API->>API: Demo Token 映射 user_id
    API->>Runtime: user_id + thread_id + message
    Runtime->>DB: 读取最近12条同用户会话
    Runtime->>Graph: invoke state
    Graph->>Graph: router → policy_agent
    Graph->>RAG: 查询政策
    RAG-->>Graph: Top-K 段落 + 行号 + 各阶段分数
    Graph-->>Runtime: answer + citations + route
    Runtime->>DB: 原子写入问题和回答
    Runtime->>Trace: 路由、耗时、引用、成功状态
    Runtime-->>API: 结构化 ChatResponse
    API-->>User: 回答与来源
```

## 安全退款 Data Lineage

```mermaid
sequenceDiagram
    participant User as 用户
    participant Agent as LangGraph Refund Agent
    participant Service as RefundService
    participant DB as SQLite Business
    participant Provider as Simulated Provider

    User->>Agent: 我要退款 order-1001
    Agent->>Service: prepare_refund(trusted_user_id, order_id)
    Service->>DB: 校验所有权、状态和已有退款
    Service->>DB: 保存 confirmation_id、金额和过期时间
    Service-->>User: 待确认；尚未退款
    User->>Service: POST /refunds/{confirmation_id}/confirm
    Service->>DB: BEGIN IMMEDIATE + 重新校验
    Service->>DB: 先保存 processing 和 idempotency_key
    Service->>Provider: 本地模拟退款
    Provider-->>Service: succeeded / processing / failed
    Service->>DB: 更新状态与 refund_events
    Service-->>User: 权威结构化结果
```

## 技术栈与用途

| 技术 | 在项目中的实际用途 |
|---|---|
| Python 3.13 | 业务服务、工作流、API、测试 |
| LangChain 1.2 | DeepSeek消息模型、工具和文档抽象 |
| LangGraph 1.1 | Router、条件边、专业节点、进程内 checkpoint |
| DeepSeek | 可选的自然语言回答润色，不负责业务状态转换 |
| FastAPI + Pydantic 2 | REST API、参数校验、Swagger、拒绝额外 user_id 字段 |
| SQLite | 跨进程聊天、订单、确认、退款和审计事件 |
| BM25 | 关键词召回，适合政策术语和精确词 |
| 本地哈希向量 | 零下载的向量召回与同义词扩展，不冒充神经网络 Embedding |
| RRF | 融合 BM25 和向量召回排名 |
| 轻量 Reranker | 综合词覆盖、向量相似度和融合分数重新排序 |
| InMemorySaver | 保存当前进程的 LangGraph 状态 |
| unittest + TestClient | 单元、并发、API、端到端和回归测试 |

## 核心模块输入输出

| 模块 | 输入 | 输出 |
|---|---|---|
| `route_intent` | 用户文本 | policy/catalog/order/refund/status/unsafe/general |
| `HybridCommerceRetriever` | 查询、Top-K | 文档块、行号、BM25/向量/融合/重排分数 |
| `CatalogService` | 需求、预算 | 真实 SKU、价格、库存、特征 |
| `RefundService` | 可信 user_id、订单或确认编号 | 资格、确认或退款权威状态 |
| `EcommerceWorkflow` | 用户、会话、消息、历史 | 路由、答案、引用、业务结果 |
| `EcommerceAgentRuntime` | 一次应用请求 | 原子记忆、Trace和结构化响应 |
| FastAPI | HTTP 请求、demo token | JSON、状态码和 OpenAPI 文档 |

## Day 1—14 知识体系

```mermaid
mindmap
  root((电商 Agent 工程))
    模型层
      DeepSeek
      System Human AI ToolMessage
      可选回答润色
    Agent层
      LangChain create_agent
      Tool Calling
      LangGraph Router
      条件边与专业节点
    记忆层
      thread_id
      user_id + thread_id 隔离
      SQLite跨进程问答
      InMemorySaver图状态
      原子问答写入
    知识层
      文档加载
      chunk 900/150与700/100
      BM25
      本地哈希向量
      RRF融合
      Reranker
      Metadata和引用
    业务层
      商品价格库存
      订单所有权
      退款资格
      confirmation_id
      idempotency_key
      状态机和审计
    服务层
      FastAPI
      Pydantic
      Demo Token
      限流
    质量层
      unittest
      路由准确率
      Retrieval Hit Rate
      安全阻断率
      Trace和延迟指标
```

## 离线评测结果

当前固定评测集包含6个路由/回答用例和3个检索用例：

```text
Route/Answer Accuracy       1.0000
Retrieval Hit Rate@3       1.0000
Unsafe Request Block Rate  1.0000
```

这些结果只代表仓库内的小型固定评测集，不代表真实线上泛化效果。简历中应写“构建离线评测集并在当前9个固定用例上全部通过”，不能写成“准确率达到100%”而不说明测试集范围。

## 运行方式

```powershell
# 80项全量测试
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m unittest discover -s tests -v

# 完全离线演示
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --demo

# 离线评测
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m chapter06_ecommerce.ecommerce_agent --eval

# API + Swagger
& "C:\Users\19194\.conda\envs\langchain1.2\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## 简历项目描述

### 项目名称

**基于 LangChain / LangGraph 的电商客服 Agent**

### 一句话介绍

面向商品咨询、商城政策问答、订单查询和退款售后的电商客服 Agent，通过混合检索增强私有知识回答，并以确定性工作流约束高风险业务操作。

### 简历技术栈

```text
Python、LangChain 1.2、LangGraph、DeepSeek、FastAPI、Pydantic、SQLite、
BM25、Local Hash Vector、RRF、Reranker、RAG、RESTful API、unittest
```

### 简历要点

- 基于 LangGraph 构建电商意图 Router 和商品、政策、订单、退款、安全等专业节点，将开放式语言理解与确定性业务规则解耦；
- 实现 BM25＋本地哈希向量双路召回、RRF 排名融合和轻量重排，返回精确到文件行号的政策证据，并建立 Retrieval Hit Rate@3 离线评测；
- 使用 SQLite 持久化聊天和业务状态，以 `user_id + thread_id` 隔离会话，并通过事务、唯一约束、确认编号和幂等键防止越权及重复退款；
- 使用 FastAPI/Pydantic 提供聊天、订单、退款确认、状态和指标接口，增加请求校验、演示身份映射、滑动窗口限流和不记录原始消息的 Trace；
- 编写80项自动化测试覆盖 RAG、记忆、正式API、提示词注入阻断、并发退款和端到端流程；固定9例离线评测集当前全部通过。

## 面试介绍

### 30秒版本

> 我实现了一个基于 LangChain、LangGraph 和 DeepSeek 的电商客服 Agent，支持商品推荐、政策问答、订单查询和安全退款。政策问答采用 BM25 与本地哈希向量双路召回，再做 RRF 融合和重排；订单价格、库存和退款状态全部来自确定性业务服务。高风险退款不能由模型直接执行，而是通过服务端身份、二次确认、事务和幂等键保证安全。项目提供分层FastAPI后端、SQLite记忆、SSE传输、Trace、离线评测和80项测试。

### 技术取舍

- 为什么不是所有任务都交给大模型：价格、库存、身份和状态必须确定；
- 为什么显式 LangGraph：复杂业务路径比自由 ReAct 更容易审计、测试和限制权限；
- 为什么混合检索：BM25擅长精确术语，本地向量补充同义表达，融合后再重排；
- 为什么先保存 processing：外部调用超时或崩溃后仍可对账，避免把未知结果误判为失败；
- 为什么默认离线：保证面试现场无网络也能演示，DeepSeek只作为可选语言增强。

## 不应在简历中夸大的内容

- Demo Token 不是生产级登录认证；
- 本地哈希向量不是 BGE、OpenAI Embedding 等神经网络语义模型；
- SQLite 和进程内限流不适合多实例高并发；
- 模拟退款不连接真实支付渠道；
- 固定9例全部通过不等于线上准确率100%。

生产升级方向是 JWT/OAuth、PostgreSQL checkpointer、Redis分布式限流、真实Embedding与向量数据库、Cross-Encoder Reranker、支付回调验签、对账和完整监控告警。
