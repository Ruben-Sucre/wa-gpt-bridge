from redis.asyncio import Redis


class RateLimiter:
    """
    Token bucket rate limiter using Redis.
    Prevents spam and abuse by limiting messages per user per time window.
    """
    
    def __init__(self, redis_url: str, max_requests: int = 10, window_seconds: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            redis_url: Redis connection URL
            max_requests: Maximum number of requests allowed in the time window
            window_seconds: Time window in seconds
        """
        self._redis = Redis.from_url(redis_url)
        self._max_requests = max_requests
        self._window_seconds = window_seconds
    
    async def check_rate_limit(self, user_id: str) -> tuple[bool, int, int]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: Unique user identifier (e.g., phone number)
        
        Returns:
            Tuple of (is_allowed, current_count, limit)
            - is_allowed: True if request is allowed, False if rate limited
            - current_count: Current number of requests in window
            - limit: Maximum allowed requests
        """
        key = f"ratelimit:{user_id}"
        
        try:
            # Increment counter
            count = await self._redis.incr(key)
            
            # Set TTL on first request
            if count == 1:
                await self._redis.expire(key, self._window_seconds)
            
            is_allowed = count <= self._max_requests
            return (is_allowed, count, self._max_requests)
            
        except Exception:
            # On Redis errors, allow the request (fail open)
            return (True, 0, self._max_requests)
    
    async def reset(self, user_id: str):
        """Reset rate limit for a specific user."""
        key = f"ratelimit:{user_id}"
        await self._redis.delete(key)
