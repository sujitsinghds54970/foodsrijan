"""
Redis Cache Service for VaidyaVihar Diagnostic ERP

Provides caching functionality for:
- API response caching
- Session management
- Rate limiting
- Real-time data
"""

import json
import asyncio
from datetime import datetime
from typing import Optional, Any, Dict, List
from functools import wraps
import redis.asyncio as redis
from redis.asyncio.connection import ConnectionPool

# Cache configuration
CACHE_CONFIG = {
    "host": "localhost",
    "port": 6379,
    "db": 0,
    "decode_responses": True,
    "max_connections": 50,
    "socket_timeout": 5,
    "socket_connect_timeout": 5,
}

# Default TTL values (in seconds)
DEFAULT_TTL = {
    "patient": 300,      # 5 minutes
    "analytics": 60,      # 1 minute
    "inventory": 120,     # 2 minutes
    "appointment": 60,    # 1 minute
    "report": 300,        # 5 minutes
    "doctor": 600,        # 10 minutes
    "session": 86400,     # 24 hours
    "token": 3600,        # 1 hour
    "otp": 300,           # 5 minutes
    "default": 300,       # 5 minutes
}


class RedisCache:
    """
    Redis cache service with async support
    """

    def __init__(self, config: Optional[Dict] = None):
        self.config = config or CACHE_CONFIG
        self._pool: Optional[ConnectionPool] = None
        self._client: Optional[redis.Redis] = None

    async def connect(self):
        """Initialize Redis connection"""
        try:
            self._pool = ConnectionPool(**self.config)
            self._client = redis.Redis(connection_pool=self._pool)
            # MenuItem connection
            await self._client.ping()
            print("Redis cache connected successfully")
            return True
        except Exception as e:
            print(f"Redis connection failed: {e}")
            return False

    async def disconnect(self):
        """Close Redis connection"""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache"""
        if not self._client:
            return None
        try:
            value = await self._client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            print(f"Cache get error: {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        category: str = "default"
    ) -> bool:
        """Set value in cache with TTL"""
        if not self._client:
            return False
        try:
            # Get TTL from config if not provided
            if ttl is None:
                ttl = DEFAULT_TTL.get(category, DEFAULT_TTL["default"])

            # Serialize value
            serialized = json.dumps(value, default=str)

            # Set in Redis
            await self._client.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"Cache set error: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self._client:
            return False
        try:
            await self._client.delete(key)
            return True
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern"""
        if not self._client:
            return 0
        try:
            keys = await self._client.keys(pattern)
            if keys:
                return await self._client.delete(*keys)
            return 0
        except Exception as e:
            print(f"Cache delete pattern error: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        if not self._client:
            return False
        try:
            return await self._client.exists(key) > 0
        except Exception as e:
            print(f"Cache exists error: {e}")
            return False

    async def incr(self, key: str) -> int:
        """Increment value"""
        if not self._client:
            return 0
        try:
            return await self._client.incr(key)
        except Exception as e:
            print(f"Cache incr error: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        if not self._client:
            return False
        try:
            return await self._client.expire(key, ttl)
        except Exception as e:
            print(f"Cache expire error: {e}")
            return False

    # === Convenience Methods ===

    async def get_patient(self, patient_id: int) -> Optional[Dict]:
        """Get cached patient data"""
        key = f"patient:{patient_id}"
        return await self.get(key)

    async def set_patient(self, patient_id: int, data: Dict, ttl: int = None) -> bool:
        """Cache patient data"""
        key = f"patient:{patient_id}"
        return await self.set(key, data, ttl, "patient")

    async def delete_patient(self, patient_id: int) -> bool:
        """Delete cached patient"""
        key = f"patient:{patient_id}"
        return await self.delete(key)

    async def get_analytics(self, key: str) -> Optional[Dict]:
        """Get cached analytics"""
        cache_key = f"analytics:{key}"
        return await self.get(cache_key)

    async def set_analytics(self, key: str, data: Dict, ttl: int = 60) -> bool:
        """Cache analytics data"""
        cache_key = f"analytics:{key}"
        return await self.set(cache_key, data, ttl, "analytics")

    async def invalidate_analytics(self, pattern: str = "analytics:*") -> int:
        """Invalidate analytics cache"""
        return await self.delete_pattern(pattern)

    async def get_inventory_item(self, item_id: int) -> Optional[Dict]:
        """Get cached inventory item"""
        key = f"inventory:{item_id}"
        return await self.get(key)

    async def set_inventory_item(self, item_id: int, data: Dict) -> bool:
        """Cache inventory item"""
        key = f"inventory:{item_id}"
        return await self.set(key, data, ttl=120, category="inventory")

    async def delete_inventory_item(self, item_id: int) -> bool:
        """Delete cached inventory item"""
        key = f"inventory:{item_id}"
        return await self.delete(key)

    async def get_doctor(self, doctor_id: int) -> Optional[Dict]:
        """Get cached doctor data"""
        key = f"doctor:{doctor_id}"
        return await self.get(key)

    async def set_doctor(self, doctor_id: int, data: Dict) -> bool:
        """Cache doctor data"""
        key = f"doctor:{doctor_id}"
        return await self.set(key, data, ttl=600, category="doctor")

    async def invalidate_doctor(self, doctor_id: int) -> bool:
        """Delete cached doctor"""
        key = f"doctor:{doctor_id}"
        return await self.delete(key)

    # === Session Management ===

    async def set_session(self, session_id: str, data: Dict, ttl: int = 86400) -> bool:
        """Set session data"""
        key = f"session:{session_id}"
        return await self.set(key, data, ttl, "session")

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session data"""
        key = f"session:{session_id}"
        return await self.get(key)

    async def delete_session(self, session_id: str) -> bool:
        """Delete session"""
        key = f"session:{session_id}"
        return await self.delete(key)

    async def session_exists(self, session_id: str) -> bool:
        """Check if session exists"""
        key = f"session:{session_id}"
        return await self.exists(key)

    # === Token Management (for rate limiting) ===

    async def set_token(self, token: str, data: Dict, ttl: int = 3600) -> bool:
        """Cache token data"""
        key = f"token:{token}"
        return await self.set(key, data, ttl, "token")

    async def get_token(self, token: str) -> Optional[Dict]:
        """Get token data"""
        key = f"token:{token}"
        return await self.get(key)

    async def delete_token(self, token: str) -> bool:
        """Delete token"""
        key = f"token:{token}"
        return await self.delete(key)

    # === OTP Management ===

    async def set_otp(self, phone: str, otp: str, ttl: int = 300) -> bool:
        """Cache OTP"""
        key = f"otp:{phone}"
        return await self.set(key, {"otp": otp}, ttl, "otp")

    async def get_otp(self, phone: str) -> Optional[str]:
        """Get cached OTP"""
        data = await self.get(f"otp:{phone}")
        return data.get("otp") if data else None

    async def verify_otp(self, phone: str, otp: str) -> bool:
        """Verify OTP"""
        cached_otp = await self.get_otp(phone)
        if cached_otp == otp:
            await self.delete(f"otp:{phone}")
            return True
        return False

    # === Rate Limiting ===

    async def check_rate_limit(
        self,
        identifier: str,
        limit: int = 100,
        window: int = 3600
    ) -> Dict[str, Any]:
        """
        Check rate limit for identifier
        
        Returns:
            {
                "allowed": True/False,
                "remaining": int,
                "reset_at": int,
                "limit": int,
                "window": int
            }
        """
        key = f"ratelimit:{identifier}"

        # Use Redis pipeline for atomic operations
        async with self._client.pipeline(transaction=True) as pipe:
            # Increment counter
            pipe.incr(key)
            # Set expiry if this is a new key
            pipe.expire(key, window)
            # Get current count
            results = await pipe.execute()
            current_count = results[0]

        remaining = max(0, limit - current_count)
        allowed = current_count <= limit

        # Get TTL for reset time
        ttl = await self._client.ttl(key)
        reset_at = int((datetime.now().timestamp() + ttl) if ttl > 0 else 0)

        return {
            "allowed": allowed,
            "remaining": remaining,
            "reset_at": reset_at,
            "limit": limit,
            "window": window,
            "current": current_count
        }

    # === Locking ===

    async def acquire_lock(
        self,
        lock_name: str,
        timeout: int = 10,
        blocking: bool = False
    ) -> Optional[str]:
        """
        Acquire a distributed lock
        
        Args:
            lock_name: Name of the lock
            timeout: Lock expiry in seconds
            blocking: Whether to wait for lock
            
        Returns:
            Lock token if acquired, None otherwise
        """
        import uuid
        lock_token = str(uuid.uuid4())

        key = f"lock:{lock_name}"

        if blocking:
            # Wait up to timeout seconds
            start_time = datetime.now().timestamp()
            while datetime.now().timestamp() - start_time < timeout:
                # Try to set the lock
                acquired = await self._client.set(
                    key,
                    lock_token,
                    nx=True,
                    ex=timeout
                )
                if acquired:
                    return lock_token
                await asyncio.sleep(0.1)
            return None
        else:
            acquired = await self._client.set(
                key,
                lock_token,
                nx=True,
                ex=timeout
            )
            return lock_token if acquired else None

    async def release_lock(self, lock_name: str, lock_token: str) -> bool:
        """Release a distributed lock"""
        key = f"lock:{lock_name}"
        
        # Use Lua script for atomic check-and-delete
        script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """
        
        result = await self._client.eval(script, 1, key, lock_token)
        return result == 1

    # === Statistics ===

    async def get_cache_stats(self) -> Dict:
        """Get cache statistics"""
        if not self._client:
            return {}

        info = await self._client.info("memory")
        stats = {
            "used_memory": info.get("used_memory_human", "N/A"),
            "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients", 0),
            "total_connections": info.get("total_connections_received", 0),
            "keyspace_hits": info.get("keyspace_hits", 0),
            "keyspace_misses": info.get("keyspace_misses", 0),
            "hit_rate": 0
        }

        # Calculate hit rate
        total = stats["keyspace_hits"] + stats["keyspace_misses"]
        if total > 0:
            stats["hit_rate"] = round(
                stats["keyspace_hits"] / total * 100, 2
            )

        return stats


# Global cache instance
cache = RedisCache()


def get_cache() -> RedisCache:
    """Get the global cache instance"""
    return cache


# Cache decorator for API endpoints
def cached(ttl: int = 300, category: str = "default", key_builder=None):
    """
    Decorator for caching function results
    
    Usage:
        @cached(ttl=60, category="analytics", key_builder=lambda *args, **kwargs: f"user:{args[0]}")
        async def get_user_data(user_id: int):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                # Default key from function name and arguments
                key_parts = [func.__name__]
                for arg in args:
                    key_parts.append(str(arg))
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}:{v}")
                cache_key = ":".join(key_parts)

            # Try to get from cache
            cached_result = await cache.get(cache_key)
            if cached_result is not None:
                return cached_result

            # Call function and cache result
            result = await func(*args, **kwargs)
            await cache.set(cache_key, result, ttl, category)
            return result

        return wrapper
    return decorator


# Invalidation decorator
def invalidate_cache(pattern: str):
    """
    Decorator for invalidating cache after function execution
    
    Usage:
        @invalidate_cache(pattern="patient:*")
        async def update_patient(patient_id: int, data):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            result = await func(*args, **kwargs)
            await cache.delete_pattern(pattern.format(*args, **kwargs))
            return result
        return wrapper
    return decorator

