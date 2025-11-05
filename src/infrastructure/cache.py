"""Caching layer with Redis and local fallback."""

import json
import pickle
from typing import Optional, Any
from pathlib import Path
import hashlib

from .config import get_config

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class Cache:
    """Cache with Redis primary and local file fallback."""

    def __init__(self):
        self.config = get_config()
        self.redis_client = None
        self.enabled = self.config.cache_enabled

        if not self.enabled:
            return

        # Try to connect to Redis
        if REDIS_AVAILABLE and self.config.redis_url:
            try:
                self.redis_client = redis.from_url(self.config.redis_url)
                self.redis_client.ping()
            except Exception:
                self.redis_client = None

        # Setup local cache directory
        self.cache_dir = Path(self.config.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _make_key(self, key: str) -> str:
        """Create a safe cache key."""
        # Hash long keys
        if len(key) > 200:
            return hashlib.sha256(key.encode()).hexdigest()
        # Replace problematic characters for filesystem
        return key.replace("/", "_").replace(":", "_")

    def _local_path(self, key: str) -> Path:
        """Get local cache file path."""
        safe_key = self._make_key(key)
        return self.cache_dir / f"{safe_key}.cache"

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled:
            return None

        # Try Redis first
        if self.redis_client:
            try:
                value = self.redis_client.get(key)
                if value:
                    return pickle.loads(value)
            except Exception:
                pass

        # Fallback to local cache
        local_path = self._local_path(key)
        if local_path.exists():
            try:
                with open(local_path, "rb") as f:
                    return pickle.load(f)
            except Exception:
                pass

        return None

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache (must be pickleable)
            ttl: Time to live in seconds (None = no expiry)
        """
        if not self.enabled:
            return

        serialized = pickle.dumps(value)

        # Try Redis first
        if self.redis_client:
            try:
                if ttl:
                    self.redis_client.setex(key, ttl, serialized)
                else:
                    self.redis_client.set(key, serialized)
                return
            except Exception:
                pass

        # Fallback to local cache
        local_path = self._local_path(key)
        try:
            with open(local_path, "wb") as f:
                f.write(serialized)
        except Exception:
            pass

    async def delete(self, key: str):
        """Delete value from cache."""
        if not self.enabled:
            return

        # Redis
        if self.redis_client:
            try:
                self.redis_client.delete(key)
            except Exception:
                pass

        # Local
        local_path = self._local_path(key)
        if local_path.exists():
            try:
                local_path.unlink()
            except Exception:
                pass

    async def clear(self):
        """Clear all cache."""
        if not self.enabled:
            return

        # Redis
        if self.redis_client:
            try:
                self.redis_client.flushdb()
            except Exception:
                pass

        # Local
        for cache_file in self.cache_dir.glob("*.cache"):
            try:
                cache_file.unlink()
            except Exception:
                pass


# Global cache instance
_cache: Optional[Cache] = None


def get_cache() -> Cache:
    """Get global cache instance."""
    global _cache
    if _cache is None:
        _cache = Cache()
    return _cache
