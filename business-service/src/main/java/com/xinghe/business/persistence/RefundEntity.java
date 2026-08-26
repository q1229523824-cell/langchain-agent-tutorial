package com.xinghe.business.persistence;

import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;

@TableName("refunds")
public class RefundEntity {
    @TableId
    private String refundId;
    private String orderId;
    private String userId;
    private String idempotencyKey;
    private long amountCents;
    private String status;
    private long orderVersion;

    public String getRefundId() { return refundId; }
    public void setRefundId(String refundId) { this.refundId = refundId; }
    public String getOrderId() { return orderId; }
    public void setOrderId(String orderId) { this.orderId = orderId; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getIdempotencyKey() { return idempotencyKey; }
    public void setIdempotencyKey(String idempotencyKey) { this.idempotencyKey = idempotencyKey; }
    public long getAmountCents() { return amountCents; }
    public void setAmountCents(long amountCents) { this.amountCents = amountCents; }
    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
    public long getOrderVersion() { return orderVersion; }
    public void setOrderVersion(long orderVersion) { this.orderVersion = orderVersion; }
}
