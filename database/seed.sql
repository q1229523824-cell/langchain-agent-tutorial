INSERT INTO users (user_id, password_hash, role) VALUES
('demo-user', '$2a$10$demo-only-placeholder', 'CUSTOMER'),
('other-user', '$2a$10$demo-only-placeholder', 'CUSTOMER')
ON DUPLICATE KEY UPDATE user_id = VALUES(user_id);

INSERT INTO products (sku, name, category, price_cents, stock) VALUES
('sku-headphone-001', '星河降噪耳机', '耳机', 39900, 20),
('sku-drone-001', '星河航拍无人机', '无人机', 49900, 5)
ON DUPLICATE KEY UPDATE sku = VALUES(sku);

INSERT INTO orders (order_id, user_id, product_sku, amount_cents, status) VALUES
('order-1001', 'demo-user', 'sku-drone-001', 49900, 'PENDING_SHIPMENT'),
('order-1002', 'demo-user', 'sku-headphone-001', 39900, 'SHIPPED'),
('order-2001', 'other-user', 'sku-headphone-001', 39900, 'PENDING_SHIPMENT')
ON DUPLICATE KEY UPDATE order_id = VALUES(order_id);
