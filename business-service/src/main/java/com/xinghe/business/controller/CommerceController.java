package com.xinghe.business.controller;

import com.xinghe.business.dto.CreateOrderRequest;
import com.xinghe.business.dto.RefundConfirmRequest;
import com.xinghe.business.dto.RefundPreviewRequest;
import com.xinghe.business.model.Order;
import com.xinghe.business.model.Product;
import com.xinghe.business.model.Refund;
import com.xinghe.business.service.CommerceService;
import jakarta.validation.Valid;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api")
public class CommerceController {
    private final CommerceService service;

    public CommerceController(CommerceService service) {
        this.service = service;
    }

    @GetMapping("/products/search")
    public Map<String, Object> searchProducts(@RequestParam(required = false) String q) {
        List<Product> products = service.searchProducts(q);
        return Map.of("count", products.size(), "products", products);
    }

    @GetMapping("/products/{sku}")
    public Product getProduct(@PathVariable String sku) { return service.getProduct(sku); }

    @GetMapping("/orders")
    public Map<String, Object> listOrders(@RequestHeader("X-User-Id") String userId) {
        List<Order> orders = service.listOrders(userId);
        return Map.of("count", orders.size(), "orders", orders);
    }

    @GetMapping("/orders/{orderId}")
    public Order getOrder(@RequestHeader("X-User-Id") String userId, @PathVariable String orderId) {
        return service.getOrder(userId, orderId);
    }

    @PostMapping("/orders")
    public Order createOrder(@RequestHeader("X-User-Id") String userId,
                             @Valid @RequestBody CreateOrderRequest request) {
        return service.createOrder(userId, request);
    }

    @PostMapping("/refunds/preview")
    public Refund previewRefund(@RequestHeader("X-User-Id") String userId,
                                @Valid @RequestBody RefundPreviewRequest request) {
        return service.previewRefund(userId, request);
    }

    @PostMapping("/refunds/{refundId}/confirm")
    public Refund confirmRefund(@RequestHeader("X-User-Id") String userId,
                               @PathVariable String refundId,
                               @Valid @RequestBody RefundConfirmRequest request) {
        return service.confirmRefund(userId, refundId, request);
    }

    @GetMapping("/refunds/{refundId}")
    public Refund getRefund(@RequestHeader("X-User-Id") String userId, @PathVariable String refundId) {
        return service.getRefund(userId, refundId);
    }
}
