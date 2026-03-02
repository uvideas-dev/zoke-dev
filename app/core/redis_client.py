import redis.asyncio as redis
from app.core.config import settings

class MockRedis:
    """In-memory fallback for Redis during development if server is missing."""
    def __init__(self):
        self.storage = {}
    async def lrange(self, key, start, stop):
        lst = self.storage.get(key, [])
        return lst[start:stop+1]
    async def rpush(self, key, *values):
        if key not in self.storage:
            self.storage[key] = []
        self.storage[key].extend(values)
        return len(self.storage[key])
    async def delete(self, *keys):
        for k in keys:
            if k in self.storage:
                del self.storage[k]
        return len(keys)
    async def close(self):
        pass

# Global singleton
redis_instance = None

async def get_redis():
    global redis_instance
    if redis_instance is None:
        try:
            redis_instance = await redis.from_url(
                settings.REDIS_URL, 
                encoding="utf-8", 
                decode_responses=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
            await redis_instance.ping()
            print("🚀 Successfully connected to Redis!")
        except Exception as e:
            print(f"⚠️ Redis connection failed ({e}). Falling back to in-memory MockRedis.")
            redis_instance = MockRedis()
    return redis_instance

async def check_redis_connection() -> bool:
    try:
        client = await get_redis()
        # MockRedis has no ping, so check if it's the real client
        if isinstance(client, MockRedis):
            return False
        await client.ping()
        return True
    except Exception:
        return False

async def close_redis():
    global redis_instance
    if redis_instance:
        if not isinstance(redis_instance, MockRedis):
            await redis_instance.close()
        redis_instance = None
