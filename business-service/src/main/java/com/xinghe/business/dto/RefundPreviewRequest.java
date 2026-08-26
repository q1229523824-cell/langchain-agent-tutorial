package com.xinghe.business.dto;

import jakarta.validation.constraints.NotBlank;

public record RefundPreviewRequest(
        @NotBlank String orderId,
        @NotBlank String idempotencyKey
) {}
