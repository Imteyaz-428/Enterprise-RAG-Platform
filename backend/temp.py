from services.cache.redis_service import RedisService

redis = RedisService()

redis.set(
    "test",
    {
        "name": "Imteyaz"
    }
)

print(redis.get("test"))