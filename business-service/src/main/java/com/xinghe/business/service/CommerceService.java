package com.xinghe.business.service;

import com.xinghe.business.dto.CreateOrderRequest;
import com.xinghe.business.dto.RefundConfirmRequest;
import com.xinghe.business.dto.RefundPreviewRequest;
import com.xinghe.business.exception.BusinessException;
import com.xinghe.business.model.Order;
import com.xinghe.business.model.Product;
import com.xinghe.business.model.Refund;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicLong;

/**
 * 确定性业务层：Agent 可以调用它，但不能绕过这里直接修改订单。
 * 当前默认使用内存仓库，便于没有 MySQL 的学习环境启动；生产 profile 应替换为 MyBatis/JDBC Repository。
 */
@Service
public class CommerceService {
    private final Map<String, Product> products = new ConcurrentHashMap<>();
    private final Map<String, Order> orders = new ConcurrentHashMap<>();
    private final Map<String, Refund> refundsByKey = new ConcurrentHashMap<>();
    private final AtomicLong orderSequence = new AtomicLong(1003);

    public CommerceService() {
        products.put("sku-headphone-001", new Product("sku-headphone-001", "星河降噪耳机",
                "耳机", 39900, 20, List.of("主动降噪", "通勤", "蓝牙")));
        products.put("sku-drone-001", new Product("sku-drone-001", "星河航拍无人机",
                "无人机", 49900, 5, List.of("4K", "折叠", "电子防抖")));
        orders.put("order-1001", new Order("order-1001", "demo-user", "sku-drone-001", 49900, "PENDING_SHIPMENT"));
        orders.put("order-1002", new Order("order-1002", "demo-user", "sku-headphone-001", 39900, "SHIPPED"));
        orders.put("order-2001", new Order("order-2001", "other-user", "sku-headphone-001", 39900, "PENDING_SHIPMENT"));
    }

    public List<Product> searchProducts(String keyword) {
        if (keyword == null || keyword.isBlank()) return new ArrayList<>(products.values());
        String normalized = keyword.toLowerCase();
        return products.values().stream()
                .filter(p -> (p.name() + p.category() + String.join("", p.features())).toLowerCase().contains(normalized))
                .toList();
    }

    public Product getProduct(String sku) {
        Product product = products.get(sku);
        if (product == null) throw new BusinessException("PRODUCT_NOT_FOUND", "商品不存在", 404);
        return product;
    }

    public List<Order> listOrders(String userId) {
        return orders.values().stream().filter(o -> o.getUserId().equals(userId)).toList();
    }

    public Order getOrder(String userId, String orderId) {
        Order order = orders.get(orderId);
        if (order == null || !order.getUserId().equals(userId)) {
            throw new BusinessException("ORDER_NOT_FOUND", "订单不存在或无权访问", 404);
        }
        return order;
    }

    public Order createOrder(String userId, CreateOrderRequest request) {
        getProduct(request.productSku());
        String orderId = "order-" + orderSequence.getAndIncrement();
        Order order = new Order(orderId, userId, request.productSku(), request.amountCents(), "PENDING_SHIPMENT");
        orders.put(orderId, order);
        return order;
    }

    /** 预览只创建待确认记录，不触发资金动作。 */
    public Refund previewRefund(String userId, RefundPreviewRequest request) {
        Order order = getOrder(userId, request.orderId());
        if (!"PENDING_SHIPMENT".equals(order.getStatus())) {
            throw new BusinessException("REFUND_NOT_ALLOWED", "订单当前状态不支持自动退款", 409);
        }
        String key = userId + ":" + request.idempotencyKey();
        Refund existing = refundsByKey.get(key);
        if (existing != null) return existing;
        Refund refund = new Refund("refund-" + UUID.randomUUID(), request.idempotencyKey(),
                order.getOrderId(), userId, order.getAmountCents(), "PREPARED", order.getVersion(), java.time.Instant.now());
        refundsByKey.put(key, refund);
        return refund;
    }

    /**
     * 确认操作在真实数据库中应由 @Transactional + 唯一索引 + 乐观锁共同保障。
     * synchronized 只用于本地演示，不能替代分布式锁或数据库事务。
     */
    @Transactional
    public synchronized Refund confirmRefund(String userId, String refundId, RefundConfirmRequest request) {
        String key = userId + ":" + request.idempotencyKey();
        Refund refund = refundsByKey.get(key);
        if (refund == null || !refund.refundId().equals(refundId) || !refund.userId().equals(userId)) {
            throw new BusinessException("REFUND_NOT_FOUND", "退款记录不存在或无权访问", 404);
        }
        if ("SUCCEEDED".equals(refund.status())) return refund;
        Order order = getOrder(userId, refund.orderId());
        if (order.getVersion() != refund.orderVersion() || !"PENDING_SHIPMENT".equals(order.getStatus())) {
            throw new BusinessException("ORDER_VERSION_CONFLICT", "订单状态已变化，请重新预览退款", 409);
        }
        order.markRefunded();
        Refund succeeded = new Refund(refund.refundId(), refund.idempotencyKey(), refund.orderId(), refund.userId(),
                refund.amountCents(), "SUCCEEDED", order.getVersion(), refund.createdAt());
        refundsByKey.put(key, succeeded);
        return succeeded;
    }

    public Refund getRefund(String userId, String refundId) {
        return refundsByKey.values().stream()
                .filter(r -> r.refundId().equals(refundId) && r.userId().equals(userId))
                .findFirst()
                .orElseThrow(() -> new BusinessException("REFUND_NOT_FOUND", "退款记录不存在或无权访问", 404));
    }
}
