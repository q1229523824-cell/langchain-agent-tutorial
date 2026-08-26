package com.xinghe.business.dto;

import jakarta.validation.constraints.Min;
import jakarta.validation.constraints.NotBlank;

public record CreateOrderRequest(
        @NotBlank String productSku,
        @Min(1) long amountCents
) {}
