import json
from typing import List
import asyncio
from redis.asyncio import Redis


class ConversationMemory:
    def __init__(self, redis_url: str = "redis://redis:6379/0", ttl: int = 3600 * 24):
        self._redis = Redis.from_url(redis_url)
        self._ttl = ttl

    async def get_conversation(self, conv_id: str, max_messages: int = 20) -> List[dict]:
        """
        Retrieve conversation history for a given conversation ID.
        
        Args:
            conv_id: Unique conversation identifier (typically phone number)
            max_messages: Maximum number of messages to return (default 20).
                         Returns the most recent messages to avoid context overflow.
        
        Returns:
            List of message dictionaries with 'role' and 'content' keys
        """
        raw = await self._redis.get(f"conv:{conv_id}")
        if not raw:
            return []
        try:
            messages = json.loads(raw)
            # Return only the last N messages to prevent context overflow and reduce costs
            if len(messages) > max_messages:
                return messages[-max_messages:]
            return messages
        except Exception:
            return []

    async def append_message(self, conv_id: str, role: str, content: str):
        conv = await self.get_conversation(conv_id)
        conv.append({"role": role, "content": content})
        await self._redis.set(f"conv:{conv_id}", json.dumps(conv), ex=self._ttl)

    async def clear(self, conv_id: str):
        await self._redis.delete(f"conv:{conv_id}")

    async def ping(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if Redis responds to ping, False otherwise
        """
        try:
            return await self._redis.ping()
        except Exception:
            return False
