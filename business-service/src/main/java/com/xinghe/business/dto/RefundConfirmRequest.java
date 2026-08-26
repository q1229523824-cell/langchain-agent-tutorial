package com.xinghe.business.dto;

import jakarta.validation.constraints.NotBlank;

public record RefundConfirmRequest(@NotBlank String idempotencyKey) {}
