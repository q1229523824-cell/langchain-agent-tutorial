-- 星河商城业务库：生产环境由 Flyway/Liquibase 管理迁移。
CREATE TABLE IF NOT EXISTS users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id VARCHAR(80) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(40) NOT NULL DEFAULT 'CUSTOMER',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS products (
    sku VARCHAR(80) PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(80) NOT NULL,
    price_cents BIGINT NOT NULL,
    stock INT NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(80) PRIMARY KEY,
    user_id VARCHAR(80) NOT NULL,
    product_sku VARCHAR(80) NOT NULL,
    amount_cents BIGINT NOT NULL,
    status VARCHAR(40) NOT NULL,
    version BIGINT NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_orders_product FOREIGN KEY (product_sku) REFERENCES products(sku),
    INDEX idx_orders_user (user_id)
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id VARCHAR(80) PRIMARY KEY,
    order_id VARCHAR(80) NOT NULL,
    user_id VARCHAR(80) NOT NULL,
    idempotency_key VARCHAR(120) NOT NULL,
    amount_cents BIGINT NOT NULL,
    status VARCHAR(40) NOT NULL,
    order_version BIGINT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_refund_user_key (user_id, idempotency_key),
    INDEX idx_refunds_user (user_id)
);

CREATE TABLE IF NOT EXISTS refund_events (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    refund_id VARCHAR(80) NOT NULL,
    from_status VARCHAR(40),
    to_status VARCHAR(40) NOT NULL,
    trace_id VARCHAR(100),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_refund_events_refund (refund_id)
);
