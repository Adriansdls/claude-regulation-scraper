"""
Cache Manager
High-performance caching system for LLM responses, extracted content, and workflow results
"""
import asyncio
import logging
import json
import hashlib
import pickle
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field
import redis.asyncio as redis
from pathlib import Path
import aiofiles
import gzip
import base64

from ...config.config_manager import get_config


class CacheType(str, Enum):
    """Types of cached content"""
    LLM_RESPONSE = "llm_response"
    EXTRACTED_CONTENT = "extracted_content"
    WEBSITE_ANALYSIS = "website_analysis"
    PDF_CONTENT = "pdf_content"
    IMAGE_ANALYSIS = "image_analysis"
    VALIDATION_RESULT = "validation_result"
    WORKFLOW_STATE = "workflow_state"


class CacheStrategy(str, Enum):
    """Cache invalidation strategies"""
    TTL = "ttl"  # Time-to-live
    LRU = "lru"  # Least recently used
    MANUAL = "manual"  # Manual invalidation
    DEPENDENCY = "dependency"  # Dependency-based


@dataclass
class CacheEntry:
    """A cached entry with metadata"""
    key: str
    cache_type: CacheType
    data: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    dependencies: List[str] = field(default_factory=list)
    compression: Optional[str] = None


class CacheManager:
    """High-performance distributed cache manager"""
    
    def __init__(self):
        self.config = get_config()
        self.cache_config = self.config.cache
        self.logger = logging.getLogger(__name__)
        
        # Redis connection
        self.redis_client: Optional[redis.Redis] = None
        
        # Local cache for frequently accessed items
        self.local_cache: Dict[str, CacheEntry] = {}
        self.local_cache_size = 0
        self.max_local_cache_size = self.cache_config.local_cache_size_mb * 1024 * 1024
        
        # Cache statistics
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "storage_saves": 0,
            "storage_loads": 0
        }
        
        # TTL configurations by cache type
        self.default_ttls = {
            CacheType.LLM_RESPONSE: timedelta(hours=24),
            CacheType.EXTRACTED_CONTENT: timedelta(days=7),
            CacheType.WEBSITE_ANALYSIS: timedelta(days=1),
            CacheType.PDF_CONTENT: timedelta(days=30),
            CacheType.IMAGE_ANALYSIS: timedelta(days=7),
            CacheType.VALIDATION_RESULT: timedelta(hours=12),
            CacheType.WORKFLOW_STATE: timedelta(hours=1)
        }
        
        # File storage paths
        self.cache_dir = Path(self.cache_config.file_cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Background tasks
        self._cleanup_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self):
        """Initialize and start the cache manager"""
        if self._is_running:
            return
        
        self.logger.info("Starting cache manager")
        
        # Initialize Redis connection
        if self.cache_config.redis_enabled:
            try:
                self.redis_client = redis.Redis(
                    host=self.cache_config.redis_host,
                    port=self.cache_config.redis_port,
                    password=self.cache_config.redis_password,
                    db=self.cache_config.redis_db,
                    encoding='utf-8',
                    decode_responses=False  # We handle encoding ourselves
                )
                
                # Test connection
                await self.redis_client.ping()
                self.logger.info("Connected to Redis cache")
                
            except Exception as e:
                self.logger.warning(f"Failed to connect to Redis: {e}")
                self.redis_client = None
        
        # Start cleanup task
        self._is_running = True
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        
        self.logger.info("Cache manager started successfully")
    
    async def stop(self):
        """Stop the cache manager"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        if self.redis_client:
            await self.redis_client.close()
        
        self.logger.info("Cache manager stopped")
    
    async def get(
        self, 
        key: str, 
        cache_type: CacheType,
        default: Any = None
    ) -> Optional[Any]:
        """Retrieve item from cache"""
        cache_key = self._build_key(key, cache_type)
        
        # Check local cache first
        if cache_key in self.local_cache:
            entry = self.local_cache[cache_key]
            
            # Check if expired
            if entry.expires_at and datetime.utcnow() > entry.expires_at:
                await self._evict_local(cache_key)
                self.stats["misses"] += 1
                return default
            
            # Update access info
            entry.access_count += 1
            entry.last_accessed = datetime.utcnow()
            
            self.stats["hits"] += 1
            return entry.data
        
        # Check Redis cache
        if self.redis_client:
            try:
                cached_data = await self.redis_client.get(cache_key)
                if cached_data:
                    entry = await self._deserialize_entry(cached_data)
                    if entry:
                        # Add to local cache if small enough
                        if entry.size_bytes < self.max_local_cache_size // 10:
                            await self._add_to_local_cache(cache_key, entry)
                        
                        self.stats["hits"] += 1
                        return entry.data
            except Exception as e:
                self.logger.warning(f"Redis cache get error: {e}")
        
        # Check file cache for large items
        try:
            file_path = self._get_file_cache_path(cache_key)
            if file_path.exists():
                async with aiofiles.open(file_path, 'rb') as f:
                    cached_data = await f.read()
                
                entry = await self._deserialize_entry(cached_data)
                if entry and (not entry.expires_at or datetime.utcnow() <= entry.expires_at):
                    self.stats["hits"] += 1
                    self.stats["storage_loads"] += 1
                    return entry.data
                else:
                    # Remove expired file
                    file_path.unlink(missing_ok=True)
        except Exception as e:
            self.logger.debug(f"File cache get error: {e}")
        
        self.stats["misses"] += 1
        return default
    
    async def set(
        self,
        key: str,
        data: Any,
        cache_type: CacheType,
        ttl: Optional[timedelta] = None,
        dependencies: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Store item in cache"""
        cache_key = self._build_key(key, cache_type)
        
        # Calculate TTL
        if ttl is None:
            ttl = self.default_ttls.get(cache_type, timedelta(hours=1))
        
        expires_at = datetime.utcnow() + ttl if ttl else None
        
        # Create cache entry
        entry = CacheEntry(
            key=cache_key,
            cache_type=cache_type,
            data=data,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
            metadata=metadata or {},
            dependencies=dependencies or []
        )
        
        # Serialize data
        serialized_data = await self._serialize_entry(entry)
        entry.size_bytes = len(serialized_data)
        
        # Determine storage strategy based on size
        use_file_cache = entry.size_bytes > self.cache_config.file_cache_threshold
        
        try:
            if use_file_cache:
                # Store large items in file cache
                await self._store_in_file_cache(cache_key, serialized_data, ttl)
                self.stats["storage_saves"] += 1
            else:
                # Store in Redis/local cache
                if self.redis_client:
                    await self.redis_client.setex(
                        cache_key, 
                        int(ttl.total_seconds()) if ttl else 3600,
                        serialized_data
                    )
                
                # Add to local cache
                if entry.size_bytes < self.max_local_cache_size // 10:
                    await self._add_to_local_cache(cache_key, entry)
            
            return True
            
        except Exception as e:
            self.logger.error(f"Cache set error for key {cache_key}: {e}")
            return False
    
    async def delete(self, key: str, cache_type: CacheType) -> bool:
        """Delete item from cache"""
        cache_key = self._build_key(key, cache_type)
        
        deleted = False
        
        # Remove from local cache
        if cache_key in self.local_cache:
            await self._evict_local(cache_key)
            deleted = True
        
        # Remove from Redis
        if self.redis_client:
            try:
                result = await self.redis_client.delete(cache_key)
                deleted = deleted or bool(result)
            except Exception as e:
                self.logger.warning(f"Redis delete error: {e}")
        
        # Remove from file cache
        file_path = self._get_file_cache_path(cache_key)
        if file_path.exists():
            try:
                file_path.unlink()
                deleted = True
            except Exception as e:
                self.logger.warning(f"File cache delete error: {e}")
        
        return deleted
    
    async def invalidate_by_pattern(self, pattern: str, cache_type: Optional[CacheType] = None) -> int:
        """Invalidate cache entries matching pattern"""
        count = 0
        
        # Build pattern with cache type prefix if specified
        if cache_type:
            search_pattern = f"{cache_type.value}:{pattern}"
        else:
            search_pattern = f"*:{pattern}"
        
        # Redis pattern matching
        if self.redis_client:
            try:
                keys = await self.redis_client.keys(search_pattern)
                if keys:
                    deleted = await self.redis_client.delete(*keys)
                    count += deleted
            except Exception as e:
                self.logger.warning(f"Redis pattern invalidation error: {e}")
        
        # Local cache pattern matching
        local_keys_to_delete = []
        for key in self.local_cache.keys():
            if self._matches_pattern(key, search_pattern):
                local_keys_to_delete.append(key)
        
        for key in local_keys_to_delete:
            await self._evict_local(key)
            count += 1
        
        # File cache pattern matching
        try:
            for file_path in self.cache_dir.glob("*"):
                if self._matches_pattern(file_path.stem, search_pattern):
                    file_path.unlink()
                    count += 1
        except Exception as e:
            self.logger.warning(f"File cache pattern invalidation error: {e}")
        
        self.logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
        return count
    
    async def invalidate_dependencies(self, dependency: str) -> int:
        """Invalidate all entries that depend on the given dependency"""
        count = 0
        
        # Check local cache for dependent entries
        local_keys_to_delete = []
        for key, entry in self.local_cache.items():
            if dependency in entry.dependencies:
                local_keys_to_delete.append(key)
        
        for key in local_keys_to_delete:
            await self._evict_local(key)
            count += 1
        
        # For Redis and file cache, we'd need to iterate through all entries
        # This is expensive, so we use a dependency index in production
        
        return count
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self.stats["hits"] + self.stats["misses"]
        hit_rate = (self.stats["hits"] / total_requests) if total_requests > 0 else 0.0
        
        # Local cache stats
        local_cache_size_mb = self.local_cache_size / (1024 * 1024)
        local_cache_count = len(self.local_cache)
        
        # Redis stats
        redis_info = {}
        if self.redis_client:
            try:
                redis_info = await self.redis_client.info("memory")
            except Exception as e:
                self.logger.debug(f"Could not get Redis info: {e}")
        
        # File cache stats
        file_cache_size = 0
        file_cache_count = 0
        try:
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file():
                    file_cache_size += file_path.stat().st_size
                    file_cache_count += 1
        except Exception:
            pass
        
        return {
            "performance": {
                "hit_rate": hit_rate,
                "total_hits": self.stats["hits"],
                "total_misses": self.stats["misses"],
                "total_requests": total_requests
            },
            "local_cache": {
                "entry_count": local_cache_count,
                "size_mb": local_cache_size_mb,
                "max_size_mb": self.max_local_cache_size / (1024 * 1024),
                "utilization": local_cache_size_mb / (self.max_local_cache_size / (1024 * 1024))
            },
            "redis_cache": {
                "enabled": self.redis_client is not None,
                "memory_used_mb": redis_info.get("used_memory", 0) / (1024 * 1024) if redis_info else 0
            },
            "file_cache": {
                "entry_count": file_cache_count,
                "size_mb": file_cache_size / (1024 * 1024),
                "directory": str(self.cache_dir)
            },
            "operations": {
                "evictions": self.stats["evictions"],
                "storage_saves": self.stats["storage_saves"],
                "storage_loads": self.stats["storage_loads"]
            }
        }
    
    async def create_llm_cache_key(
        self,
        model: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.1
    ) -> str:
        """Create a cache key for LLM requests"""
        # Create deterministic hash of request parameters
        cache_data = {
            "model": model,
            "messages": messages,
            "tools": tools or [],
            "temperature": temperature
        }
        
        cache_json = json.dumps(cache_data, sort_keys=True, ensure_ascii=True)
        cache_hash = hashlib.sha256(cache_json.encode()).hexdigest()
        
        return f"llm_{model}_{cache_hash[:16]}"
    
    async def create_content_cache_key(self, url: str, extraction_method: str) -> str:
        """Create cache key for extracted content"""
        content_data = f"{url}:{extraction_method}"
        content_hash = hashlib.md5(content_data.encode()).hexdigest()
        return f"content_{content_hash}"
    
    # Private methods
    def _build_key(self, key: str, cache_type: CacheType) -> str:
        """Build full cache key with type prefix"""
        return f"{cache_type.value}:{key}"
    
    async def _add_to_local_cache(self, key: str, entry: CacheEntry):
        """Add entry to local cache with size management"""
        # Check if we need to evict items
        while (self.local_cache_size + entry.size_bytes > self.max_local_cache_size and 
               self.local_cache):
            await self._evict_lru_local()
        
        self.local_cache[key] = entry
        self.local_cache_size += entry.size_bytes
    
    async def _evict_local(self, key: str):
        """Evict item from local cache"""
        if key in self.local_cache:
            entry = self.local_cache[key]
            self.local_cache_size -= entry.size_bytes
            del self.local_cache[key]
            self.stats["evictions"] += 1
    
    async def _evict_lru_local(self):
        """Evict least recently used item from local cache"""
        if not self.local_cache:
            return
        
        # Find LRU entry
        lru_key = min(
            self.local_cache.keys(),
            key=lambda k: self.local_cache[k].last_accessed or self.local_cache[k].created_at
        )
        
        await self._evict_local(lru_key)
    
    async def _serialize_entry(self, entry: CacheEntry) -> bytes:
        """Serialize cache entry for storage"""
        # Create serializable dict
        entry_dict = {
            "key": entry.key,
            "cache_type": entry.cache_type.value,
            "data": entry.data,
            "created_at": entry.created_at.isoformat(),
            "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
            "access_count": entry.access_count,
            "last_accessed": entry.last_accessed.isoformat() if entry.last_accessed else None,
            "metadata": entry.metadata,
            "dependencies": entry.dependencies
        }
        
        # Serialize to bytes
        serialized = pickle.dumps(entry_dict)
        
        # Compress if enabled and beneficial
        if self.cache_config.compression_enabled and len(serialized) > 1024:
            compressed = gzip.compress(serialized)
            if len(compressed) < len(serialized) * 0.9:  # At least 10% savings
                entry.compression = "gzip"
                return b"COMPRESSED:" + compressed
        
        return serialized
    
    async def _deserialize_entry(self, data: bytes) -> Optional[CacheEntry]:
        """Deserialize cache entry from storage"""
        try:
            # Check for compression
            if data.startswith(b"COMPRESSED:"):
                data = gzip.decompress(data[11:])  # Remove "COMPRESSED:" prefix
            
            # Deserialize
            entry_dict = pickle.loads(data)
            
            # Reconstruct entry
            entry = CacheEntry(
                key=entry_dict["key"],
                cache_type=CacheType(entry_dict["cache_type"]),
                data=entry_dict["data"],
                created_at=datetime.fromisoformat(entry_dict["created_at"]),
                expires_at=datetime.fromisoformat(entry_dict["expires_at"]) if entry_dict["expires_at"] else None,
                access_count=entry_dict["access_count"],
                last_accessed=datetime.fromisoformat(entry_dict["last_accessed"]) if entry_dict["last_accessed"] else None,
                metadata=entry_dict["metadata"],
                dependencies=entry_dict["dependencies"]
            )
            
            return entry
            
        except Exception as e:
            self.logger.warning(f"Failed to deserialize cache entry: {e}")
            return None
    
    async def _store_in_file_cache(self, key: str, data: bytes, ttl: Optional[timedelta]):
        """Store large items in file cache"""
        file_path = self._get_file_cache_path(key)
        
        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write data
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(data)
        
        # Set file modification time for TTL tracking
        if ttl:
            expire_time = datetime.utcnow() + ttl
            file_path.touch(times=(expire_time.timestamp(), expire_time.timestamp()))
    
    def _get_file_cache_path(self, key: str) -> Path:
        """Get file path for cache key"""
        # Create safe filename from key
        safe_key = base64.urlsafe_b64encode(key.encode()).decode().rstrip('=')
        return self.cache_dir / f"{safe_key}.cache"
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Simple pattern matching for cache keys"""
        import fnmatch
        return fnmatch.fnmatch(key, pattern)
    
    async def _cleanup_loop(self):
        """Background cleanup task"""
        while self._is_running:
            try:
                await self._cleanup_expired_entries()
                await asyncio.sleep(300)  # Run every 5 minutes
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in cache cleanup: {e}")
                await asyncio.sleep(60)
    
    async def _cleanup_expired_entries(self):
        """Clean up expired cache entries"""
        current_time = datetime.utcnow()
        
        # Clean local cache
        expired_local_keys = []
        for key, entry in self.local_cache.items():
            if entry.expires_at and current_time > entry.expires_at:
                expired_local_keys.append(key)
        
        for key in expired_local_keys:
            await self._evict_local(key)
        
        # Clean file cache
        try:
            for file_path in self.cache_dir.iterdir():
                if file_path.is_file() and file_path.suffix == '.cache':
                    # Check file modification time
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if current_time > mod_time:
                        file_path.unlink()
        except Exception as e:
            self.logger.debug(f"File cache cleanup error: {e}")
        
        if expired_local_keys:
            self.logger.debug(f"Cleaned up {len(expired_local_keys)} expired cache entries")


# Global cache manager instance
_cache_manager: Optional[CacheManager] = None

async def get_cache_manager() -> CacheManager:
    """Get global cache manager instance"""
    global _cache_manager
    
    if _cache_manager is None:
        _cache_manager = CacheManager()
        await _cache_manager.start()
    
    return _cache_manager

async def shutdown_cache_manager():
    """Shutdown global cache manager"""
    global _cache_manager
    
    if _cache_manager:
        await _cache_manager.stop()
        _cache_manager = None