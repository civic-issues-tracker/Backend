import redis
from django.conf import settings

class RedisClient:
    """Redis client for direct operations"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = redis.Redis(
                host=settings.REDIS_HOST,
                port=settings.REDIS_PORT,
                db=settings.REDIS_DB,
                decode_responses=True
            )
        return cls._instance
    
    def get(self, key):
        return self.client.get(key)
    
    def set(self, key, value, expiry=None):
        return self.client.set(key, value, ex=expiry)
    
    def delete(self, key):
        return self.client.delete(key)
    
    def exists(self, key):
        return self.client.exists(key)
    
    def expire(self, key, seconds):
        return self.client.expire(key, seconds)
    
    def incr(self, key):
        return self.client.incr(key)
    
    def hset(self, name, key, value):
        return self.client.hset(name, key, value)
    
    def hget(self, name, key):
        return self.client.hget(name, key)
    
    def hgetall(self, name):
        return self.client.hgetall(name)
    
    def hdel(self, name, key):
        return self.client.hdel(name, key)