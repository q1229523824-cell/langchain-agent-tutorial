package com.xinghe.business.persistence;

import org.springframework.context.annotation.Profile;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Component;

import java.time.Duration;

/** mysql profile 才启用：将退款幂等键设为 Redis 原子占位，避免重复进入业务事务。 */
@Component
@Profile("mysql")
public class RedisIdempotencyStore {
    private final StringRedisTemplate redis;

    public RedisIdempotencyStore(StringRedisTemplate redis) {
        this.redis = redis;
    }

    public boolean reserve(String userId, String idempotencyKey, Duration ttl) {
        String key = "xinghe:refund:idempotency:" + userId + ":" + idempotencyKey;
        return Boolean.TRUE.equals(redis.opsForValue().setIfAbsent(key, "reserved", ttl));
    }
}
