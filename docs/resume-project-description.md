# 简历项目描述：星河商城智能客服 Agent

以下内容可以直接复制到简历，再根据岗位篇幅删减。

## 项目名称

**星河商城智能客服 Agent｜Python + Java 电商客服系统**

## 技术栈

```text
Python、LangChain 1.2、LangGraph、DeepSeek、FastAPI、RAG、BM25、RRF、
Reranker、SQLite、PyJWT、SSE、HTTPX、Java 17、Spring Boot、Maven、
MyBatis-Plus、MySQL、Redis、React、Vite、TypeScript、Docker Compose
```

## 项目描述

面向商品咨询、商城政策问答、订单查询和退款售后的电商客服 Agent。采用 Python Agent 编排层与 Java 业务服务分层架构：Python 负责意图识别、RAG 检索和工具编排，Java 负责订单、商品和退款等确定性业务，避免大模型直接修改核心业务数据。

## 项目要点

- 基于 LangGraph 构建商品推荐、政策问答、订单查询、退款处理和安全拦截工作流，并使用 `thread_id`、SQLite 和摘要机制实现会话隔离与持久化记忆；
- 实现 BM25、哈希向量、RRF 和轻量 Reranker 混合检索，返回文件名、段落及行号引用，支持检索结果追溯；
- 设计 Python Agent + Java Spring Boot 跨服务架构，通过 REST 工具调用商品、订单和退款接口；
- 采用退款 `preview/confirm` 两阶段流程，结合权限校验、订单状态机、订单版本控制和幂等键，降低越权及重复退款风险；
- 使用 FastAPI 提供聊天、SSE、商品、订单、退款、会话和 Trace API，使用 PyJWT 实现 Bearer Token 认证，并通过 `X-Request-ID` 关联跨服务日志；
- 使用 MyBatis-Plus Entity/Mapper、MySQL 建表脚本、Redis 幂等适配器和 Docker Compose 提供生产化迁移基础；
- 使用 React、Vite 和 TypeScript 实现登录、聊天、商品查看、订单查询及退款二次确认页面；
- 编写自动化测试覆盖 Agent 路由、RAG 检索、权限隔离、退款幂等、JWT 认证和 API 行为，全项目 85 项测试通过。

## 30 秒面试介绍

> 我开发了一个星河商城智能客服 Agent。Python 侧使用 LangGraph 负责意图路由、RAG 检索和工具编排，Java Spring Boot 负责商品、订单和退款等确定性业务。退款采用 preview/confirm 两阶段流程，用户确认后才允许执行，Java 服务再通过权限校验、订单状态、版本号和幂等键防止重复退款。系统还支持 JWT 登录、SQLite 会话记忆、SSE 聊天和 Trace ID 链路追踪。

## 面试时必须诚实说明

- Java 默认使用内存仓库，MyBatis-Plus、MySQL 和 Redis 已提供适配层、脚本和 Docker 配置；
- 当前退款是本地模拟流程，不连接真实支付渠道；
- 前端和 Java 服务需要安装 Node/JDK/Maven 后单独构建验证；
- 不要把固定测试集通过率描述成线上准确率。
