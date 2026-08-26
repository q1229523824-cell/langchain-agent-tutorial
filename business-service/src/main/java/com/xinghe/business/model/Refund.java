package com.xinghe.business.model;

import java.time.Instant;

public record Refund(
        String refundId,
        String idempotencyKey,
        String orderId,
        String userId,
        long amountCents,
        String status,
        long orderVersion,
        Instant createdAt
) {}
