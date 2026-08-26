# 星河商城业务服务（Java）

这是 Python Agent 的确定性业务侧，负责商品、订单和退款，不让大模型直接修改数据库。

## 本地启动（无需 MySQL）

安装 JDK 17 和 Maven 后：

```powershell
mvn spring-boot:run
```

默认端口是 `8081`，默认使用内存仓库，方便学习 Controller → Service → Repository 边界。

## 接口示例

```powershell
$headers = @{"X-User-Id" = "demo-user"}
Invoke-RestMethod http://127.0.0.1:8081/api/products/search?q=耳机
Invoke-RestMethod http://127.0.0.1:8081/api/orders -Headers $headers
Invoke-RestMethod http://127.0.0.1:8081/api/orders/order-1001 -Headers $headers
```

退款是两阶段流程：

1. `POST /api/refunds/preview`：校验用户、订单状态和幂等键，只生成 `PREPARED` 记录；
2. `POST /api/refunds/{refundId}/confirm`：再次校验订单版本后，在事务边界内执行一次确认。

当前 `CommerceService` 用内存 Map 演示业务流程；`persistence/` 已提供 MyBatis-Plus Entity/Mapper 和 Redis 幂等存储适配器。启用 `mysql` profile 后可把这些适配器接入真正的 Service 事务；不要把默认 demo 描述成已经连接 MySQL/Redis。

## Python Agent 如何接入

Python 侧只需要把 `query_product`、`query_order`、`preview_refund`、`confirm_refund` 封装为 REST 工具，并透传 `X-User-Id` 和 `X-Request-ID`。Agent 负责意图识别和工具编排，Java 服务负责鉴权、状态机、事务和最终写入。
