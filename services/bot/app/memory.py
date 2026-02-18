import json
from typing import List
import asyncio
from redis.asyncio import Redis


class ConversationMemory:
    def __init__(self, redis_url: str = "redis://redis:6379/0", ttl: int = 3600 * 24):
        self._redis = Redis.from_url(redis_url)
        self._ttl = ttl

    async def get_conversation(self, conv_id: str) -> List[dict]:
        raw = await self._redis.get(f"conv:{conv_id}")
        if not raw:
            return []
        try:
            return json.loads(raw)
        except Exception:
            return []

    async def append_message(self, conv_id: str, role: str, content: str):
        conv = await self.get_conversation(conv_id)
        conv.append({"role": role, "content": content})
        await self._redis.set(f"conv:{conv_id}", json.dumps(conv), ex=self._ttl)

    async def clear(self, conv_id: str):
        await self._redis.delete(f"conv:{conv_id}")
