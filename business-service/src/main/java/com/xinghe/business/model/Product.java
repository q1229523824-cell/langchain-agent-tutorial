package com.xinghe.business.model;

import java.util.List;

public record Product(
        String sku,
        String name,
        String category,
        long priceCents,
        int stock,
        List<String> features
) {
    public boolean inStock() {
        return stock > 0;
    }
}
