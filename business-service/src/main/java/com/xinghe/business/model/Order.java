package com.xinghe.business.model;

import java.time.Instant;

public class Order {
    private final String orderId;
    private final String userId;
    private final String productSku;
    private final long amountCents;
    private String status;
    private long version;
    private final Instant createdAt;

    public Order(String orderId, String userId, String productSku, long amountCents, String status) {
        this.orderId = orderId;
        this.userId = userId;
        this.productSku = productSku;
        this.amountCents = amountCents;
        this.status = status;
        this.version = 0;
        this.createdAt = Instant.now();
    }

    public String getOrderId() { return orderId; }
    public String getUserId() { return userId; }
    public String getProductSku() { return productSku; }
    public long getAmountCents() { return amountCents; }
    public String getStatus() { return status; }
    public long getVersion() { return version; }
    public Instant getCreatedAt() { return createdAt; }
    public void markRefunded() { this.status = "REFUNDED"; this.version++; }
}
