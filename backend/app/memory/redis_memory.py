import json
from typing import Optional, Dict, Any, List
from datetime import timedelta
from dotenv import load_dotenv
import os

load_dotenv()

class LocalMemory:
    """A simple in-memory session store for when Redis is unavailable."""
    def __init__(self):
        self._storage: Dict[str, str] = {}
        print("--- Using Local In-Memory Storage (Redis not found) ---")

    async def connect(self):
        pass

    async def disconnect(self):
        pass

    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        data = self._storage.get(f"session:{session_id}")
        return json.loads(data) if data else None

    async def set_session(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None):
        self._storage[f"session:{session_id}"] = json.dumps(data)

    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        session = await self.get_session(session_id) or {}
        session.update(updates)
        await self.set_session(session_id, session)

    async def add_message(self, session_id: str, role: str, content: str):
        session = await self.get_session(session_id) or {"messages": [], "context": {}}
        session["messages"].append({"role": role, "content": content})
        if len(session["messages"]) > 20:
            session["messages"] = session["messages"][-20:]
        await self.set_session(session_id, session)

    async def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        session = await self.get_session(session_id) or {"messages": []}
        return session["messages"]

    async def set_context(self, session_id: str, key: str, value: Any):
        session = await self.get_session(session_id) or {"context": {}}
        session["context"][key] = value
        await self.set_session(session_id, session)

    async def get_context(self, session_id: str, key: str) -> Any:
        session = await self.get_session(session_id) or {"context": {}}
        return session["context"].get(key)

    async def clear_session(self, session_id: str):
        self._storage.pop(f"session:{session_id}", None)

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

class RedisMemory:
    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis_client: Optional[Any] = None
        self.session_ttl = int(os.getenv("SESSION_TTL", 3600))
    
    async def connect(self):
        if not REDIS_AVAILABLE:
            raise ConnectionError("Redis library not installed")
        if self.redis_client is None:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            # Test connection
            await self.redis_client.ping()
    
    async def disconnect(self):
        if self.redis_client:
            await self.redis_client.close()
            self.redis_client = None
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        data = await self.redis_client.get(f"session:{session_id}")
        return json.loads(data) if data else None
    
    async def set_session(self, session_id: str, data: Dict[str, Any], ttl: Optional[int] = None):
        ttl = ttl or self.session_ttl
        await self.redis_client.setex(f"session:{session_id}", timedelta(seconds=ttl), json.dumps(data))
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]):
        session = await self.get_session(session_id) or {}
        session.update(updates)
        await self.set_session(session_id, session)
    
    async def add_message(self, session_id: str, role: str, content: str):
        session = await self.get_session(session_id) or {"messages": [], "context": {}}
        session["messages"].append({"role": role, "content": content})
        if len(session["messages"]) > 20:
            session["messages"] = session["messages"][-20:]
        await self.set_session(session_id, session)
    
    async def get_messages(self, session_id: str) -> List[Dict[str, str]]:
        session = await self.get_session(session_id) or {"messages": []}
        return session["messages"]
    
    async def set_context(self, session_id: str, key: str, value: Any):
        session = await self.get_session(session_id) or {"context": {}}
        session["context"][key] = value
        await self.set_session(session_id, session)
    
    async def get_context(self, session_id: str, key: str) -> Any:
        session = await self.get_session(session_id) or {"context": {}}
        return session["context"].get(key)
    
    async def clear_session(self, session_id: str):
        await self.redis_client.delete(f"session:{session_id}")

_memory_instance: Optional[Any] = None

async def get_memory() -> Any:
    global _memory_instance
    if _memory_instance is None:
        try:
            instance = RedisMemory()
            await instance.connect()
            _memory_instance = instance
        except Exception as e:
            print(f"Redis connection failed: {e}. Falling back to LocalMemory.")
            _memory_instance = LocalMemory()
    return _memory_instance

def get_redis_memory():
    # This is for backward compatibility in imports
    # Note: This is synchronous but returns the instance which might be async-initialized
    # Better to use get_memory() in async contexts
    global _memory_instance
    if _memory_instance is None:
        # We can't easily initialize it here without blocking
        # So we'll let the first async call to get_memory do it
        pass
    return _memory_instance
