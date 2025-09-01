"""
Performance Optimizer
Optimizes LLM agent performance through intelligent batching, caching, and resource management
"""
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from enum import Enum
import json
import statistics
from collections import defaultdict, deque

from ..caching.cache_manager import CacheManager, CacheType, get_cache_manager
from ...config.config_manager import get_config


class OptimizationStrategy(str, Enum):
    """Performance optimization strategies"""
    BATCH_REQUESTS = "batch_requests"
    CACHE_AGGRESSIVE = "cache_aggressive"
    PARALLEL_PROCESSING = "parallel_processing"
    REQUEST_DEDUPLICATION = "request_deduplication"
    SMART_RETRY = "smart_retry"
    RESOURCE_POOLING = "resource_pooling"


@dataclass
class PerformanceMetrics:
    """Performance tracking metrics"""
    total_requests: int = 0
    cached_responses: int = 0
    batch_requests: int = 0
    parallel_executions: int = 0
    deduplicated_requests: int = 0
    failed_requests: int = 0
    retry_attempts: int = 0
    
    # Timing metrics
    average_response_time: float = 0.0
    min_response_time: float = float('inf')
    max_response_time: float = 0.0
    recent_response_times: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Resource usage
    peak_memory_usage: float = 0.0
    average_cpu_usage: float = 0.0
    concurrent_requests: int = 0
    max_concurrent_requests: int = 0


@dataclass
class BatchRequest:
    """A batch of similar requests for optimization"""
    batch_id: str
    requests: List[Dict[str, Any]]
    created_at: datetime
    priority: int = 0
    max_batch_size: int = 10
    max_wait_time: timedelta = field(default_factory=lambda: timedelta(seconds=5))


class RequestDeduplicator:
    """Deduplicates similar requests to reduce LLM calls"""
    
    def __init__(self):
        self.pending_requests: Dict[str, List[asyncio.Future]] = defaultdict(list)
        self.request_signatures: Dict[str, str] = {}
    
    def get_request_signature(self, model: str, messages: List[Dict], **kwargs) -> str:
        """Generate signature for request deduplication"""
        sig_data = {
            "model": model,
            "messages": messages,
            "temperature": kwargs.get("temperature", 0.1),
            "max_tokens": kwargs.get("max_tokens", 4000)
        }
        return json.dumps(sig_data, sort_keys=True)
    
    async def deduplicate_request(self, signature: str, request_func, *args, **kwargs):
        """Deduplicate request execution"""
        if signature in self.pending_requests:
            # Request is already pending, wait for it
            future = asyncio.Future()
            self.pending_requests[signature].append(future)
            return await future
        
        # First request with this signature
        self.pending_requests[signature] = []
        
        try:
            result = await request_func(*args, **kwargs)
            
            # Notify all waiting requests
            for future in self.pending_requests[signature]:
                if not future.done():
                    future.set_result(result)
            
            return result
            
        except Exception as e:
            # Notify all waiting requests of the error
            for future in self.pending_requests[signature]:
                if not future.done():
                    future.set_exception(e)
            raise
        finally:
            # Clean up
            self.pending_requests.pop(signature, None)


class PerformanceOptimizer:
    """Main performance optimization engine"""
    
    def __init__(self):
        self.config = get_config()
        self.optimization_config = self.config.optimization
        self.logger = logging.getLogger(__name__)
        
        # Components
        self.cache_manager: Optional[CacheManager] = None
        self.deduplicator = RequestDeduplicator()
        
        # State
        self.enabled_strategies: Set[OptimizationStrategy] = set()
        self.metrics = PerformanceMetrics()
        self.batch_queues: Dict[str, BatchRequest] = {}
        self
        # Resource management
        self.request_semaphore = asyncio.Semaphore(self.optimization_config.max_concurrent_requests)
        self.resource_pools: Dict[str, asyncio.Queue] = {}
        
        # Optimization settings
        self.batch_size_limits = {
            "llm_requests": 5,
            "content_extraction": 3,
            "validation": 10
        }
        
        self.cache_ttl_overrides = {
            CacheType.LLM_RESPONSE: timedelta(hours=6),
            CacheType.WEBSITE_ANALYSIS: timedelta(hours=2),
            CacheType.EXTRACTED_CONTENT: timedelta(days=3)
        }
        
        # Background tasks
        self._optimization_task: Optional[asyncio.Task] = None
        self._metrics_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def start(self):
        """Start the performance optimizer"""
        if self._is_running:
            return
        
        self.logger.info("Starting performance optimizer")
        
        # Initialize cache manager
        self.cache_manager = await get_cache_manager()
        
        # Enable default optimization strategies
        self.enabled_strategies.update([
            OptimizationStrategy.CACHE_AGGRESSIVE,
            OptimizationStrategy.REQUEST_DEDUPLICATION,
            OptimizationStrategy.PARALLEL_PROCESSING,
            OptimizationStrategy.SMART_RETRY
        ])
        
        # Start background tasks
        self._is_running = True
        self._optimization_task = asyncio.create_task(self._optimization_loop())
        self._metrics_task = asyncio.create_task(self._metrics_collection_loop())
        
        self.logger.info(f"Performance optimizer started with strategies: {[s.value for s in self.enabled_strategies]}")
    
    async def stop(self):
        """Stop the performance optimizer"""
        if not self._is_running:
            return
        
        self._is_running = False
        
        # Cancel background tasks
        if self._optimization_task:
            self._optimization_task.cancel()
        if self._metrics_task:
            self._metrics_task.cancel()
        
        self.logger.info("Performance optimizer stopped")
    
    async def optimize_llm_request(
        self,
        model: str,
        messages: List[Dict],
        tools: Optional[List[Dict]] = None,
        request_func = None,
        **kwargs
    ) -> Any:
        """Optimize LLM request with caching, deduplication, and batching"""
        start_time = datetime.utcnow()
        
        async with self.request_semaphore:
            self.metrics.concurrent_requests += 1
            self.metrics.max_concurrent_requests = max(
                self.metrics.max_concurrent_requests, 
                self.metrics.concurrent_requests
            )
            
            try:
                # Step 1: Try cache first
                if OptimizationStrategy.CACHE_AGGRESSIVE in self.enabled_strategies:
                    cache_key = await self.cache_manager.create_llm_cache_key(
                        model, messages, tools, kwargs.get("temperature", 0.1)
                    )
                    
                    cached_result = await self.cache_manager.get(
                        cache_key, CacheType.LLM_RESPONSE
                    )
                    
                    if cached_result:
                        self.metrics.cached_responses += 1
                        return cached_result
                
                # Step 2: Request deduplication
                if OptimizationStrategy.REQUEST_DEDUPLICATION in self.enabled_strategies:
                    signature = self.deduplicator.get_request_signature(model, messages, **kwargs)
                    
                    result = await self.deduplicator.deduplicate_request(
                        signature, self._execute_llm_request, 
                        model, messages, tools, request_func, **kwargs
                    )
                    
                    if signature in self.deduplicator.pending_requests:
                        self.metrics.deduplicated_requests += len(
                            self.deduplicator.pending_requests[signature]
                        )
                else:
                    # Direct execution
                    result = await self._execute_llm_request(
                        model, messages, tools, request_func, **kwargs
                    )
                
                # Step 3: Cache result
                if (OptimizationStrategy.CACHE_AGGRESSIVE in self.enabled_strategies and 
                    self.cache_manager):
                    
                    cache_ttl = self.cache_ttl_overrides.get(
                        CacheType.LLM_RESPONSE, 
                        timedelta(hours=1)
                    )
                    
                    await self.cache_manager.set(
                        cache_key, result, CacheType.LLM_RESPONSE, ttl=cache_ttl
                    )
                
                return result
                
            except Exception as e:
                self.metrics.failed_requests += 1
                
                # Smart retry logic
                if OptimizationStrategy.SMART_RETRY in self.enabled_strategies:
                    return await self._smart_retry_request(
                        model, messages, tools, request_func, e, **kwargs
                    )
                else:
                    raise
            
            finally:
                # Update metrics
                self.metrics.concurrent_requests -= 1
                response_time = (datetime.utcnow() - start_time).total_seconds()
                self._update_response_time_metrics(response_time)
    
    async def optimize_content_extraction(
        self,
        urls: List[str],
        extraction_func,
        **kwargs
    ) -> List[Any]:
        """Optimize content extraction with parallel processing and caching"""
        if not urls:
            return []
        
        # Check cache for each URL
        results = []
        uncached_urls = []
        url_to_index = {}
        
        if OptimizationStrategy.CACHE_AGGRESSIVE in self.enabled_strategies:
            for i, url in enumerate(urls):
                cache_key = await self.cache_manager.create_content_cache_key(
                    url, kwargs.get("extraction_method", "default")
                )
                
                cached_result = await self.cache_manager.get(
                    cache_key, CacheType.EXTRACTED_CONTENT
                )
                
                if cached_result:
                    results.append((i, cached_result))
                    self.metrics.cached_responses += 1
                else:
                    uncached_urls.append(url)
                    url_to_index[url] = i
        else:
            uncached_urls = urls
            url_to_index = {url: i for i, url in enumerate(urls)}
        
        # Process uncached URLs
        if uncached_urls:
            if OptimizationStrategy.PARALLEL_PROCESSING in self.enabled_strategies:
                # Parallel processing with concurrency limit
                semaphore = asyncio.Semaphore(
                    min(len(uncached_urls), self.optimization_config.max_parallel_extractions)
                )
                
                async def extract_with_semaphore(url):
                    async with semaphore:
                        return await extraction_func(url, **kwargs)
                
                extraction_results = await asyncio.gather(
                    *[extract_with_semaphore(url) for url in uncached_urls],
                    return_exceptions=True
                )
                
                self.metrics.parallel_executions += len(uncached_urls)
            else:
                # Sequential processing
                extraction_results = []
                for url in uncached_urls:
                    try:
                        result = await extraction_func(url, **kwargs)
                        extraction_results.append(result)
                    except Exception as e:
                        extraction_results.append(e)
            
            # Cache results and add to final results
            for url, result in zip(uncached_urls, extraction_results):
                index = url_to_index[url]
                
                if not isinstance(result, Exception):
                    # Cache successful result
                    if (OptimizationStrategy.CACHE_AGGRESSIVE in self.enabled_strategies and 
                        self.cache_manager):
                        
                        cache_key = await self.cache_manager.create_content_cache_key(
                            url, kwargs.get("extraction_method", "default")
                        )
                        
                        cache_ttl = self.cache_ttl_overrides.get(
                            CacheType.EXTRACTED_CONTENT,
                            timedelta(days=1)
                        )
                        
                        await self.cache_manager.set(
                            cache_key, result, CacheType.EXTRACTED_CONTENT, ttl=cache_ttl
                        )
                
                results.append((index, result))
        
        # Sort results by original index and extract values
        results.sort(key=lambda x: x[0])
        final_results = []
        
        for _, result in results:
            if isinstance(result, Exception):
                raise result
            final_results.append(result)
        
        return final_results
    
    async def optimize_batch_processing(
        self,
        batch_type: str,
        items: List[Any],
        process_func,
        batch_size: Optional[int] = None,
        **kwargs
    ) -> List[Any]:
        """Optimize batch processing with intelligent batching"""
        if not items:
            return []
        
        if batch_size is None:
            batch_size = self.batch_size_limits.get(batch_type, 5)
        
        # Split into batches
        batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
        
        if OptimizationStrategy.PARALLEL_PROCESSING in self.enabled_strategies:
            # Process batches in parallel
            batch_results = await asyncio.gather(
                *[process_func(batch, **kwargs) for batch in batches],
                return_exceptions=True
            )
            
            self.metrics.batch_requests += len(batches)
        else:
            # Sequential batch processing
            batch_results = []
            for batch in batches:
                try:
                    result = await process_func(batch, **kwargs)
                    batch_results.append(result)
                except Exception as e:
                    batch_results.append(e)
        
        # Flatten results
        final_results = []
        for batch_result in batch_results:
            if isinstance(batch_result, Exception):
                raise batch_result
            elif isinstance(batch_result, list):
                final_results.extend(batch_result)
            else:
                final_results.append(batch_result)
        
        return final_results
    
    async def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics"""
        cache_stats = await self.cache_manager.get_cache_stats() if self.cache_manager else {}
        
        # Calculate derived metrics
        total_requests = self.metrics.total_requests
        cache_hit_rate = (
            self.metrics.cached_responses / total_requests 
            if total_requests > 0 else 0.0
        )
        
        deduplication_rate = (
            self.metrics.deduplicated_requests / total_requests 
            if total_requests > 0 else 0.0
        )
        
        error_rate = (
            self.metrics.failed_requests / total_requests 
            if total_requests > 0 else 0.0
        )
        
        # Recent response time stats
        recent_times = list(self.metrics.recent_response_times)
        if recent_times:
            recent_avg = statistics.mean(recent_times)
            recent_median = statistics.median(recent_times)
            recent_p95 = statistics.quantiles(recent_times, n=20)[18] if len(recent_times) >= 20 else max(recent_times)
        else:
            recent_avg = recent_median = recent_p95 = 0.0
        
        return {
            "enabled_strategies": [s.value for s in self.enabled_strategies],
            "request_metrics": {
                "total_requests": total_requests,
                "cached_responses": self.metrics.cached_responses,
                "deduplicated_requests": self.metrics.deduplicated_requests,
                "batch_requests": self.metrics.batch_requests,
                "parallel_executions": self.metrics.parallel_executions,
                "failed_requests": self.metrics.failed_requests,
                "retry_attempts": self.metrics.retry_attempts
            },
            "performance_rates": {
                "cache_hit_rate": cache_hit_rate,
                "deduplication_rate": deduplication_rate,
                "error_rate": error_rate
            },
            "response_times": {
                "average": self.metrics.average_response_time,
                "min": self.metrics.min_response_time,
                "max": self.metrics.max_response_time,
                "recent_average": recent_avg,
                "recent_median": recent_median,
                "recent_p95": recent_p95
            },
            "concurrency": {
                "current_concurrent": self.metrics.concurrent_requests,
                "max_concurrent": self.metrics.max_concurrent_requests,
                "semaphore_limit": self.request_semaphore._value + self.metrics.concurrent_requests
            },
            "cache_performance": cache_stats,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def enable_strategy(self, strategy: OptimizationStrategy):
        """Enable an optimization strategy"""
        self.enabled_strategies.add(strategy)
        self.logger.info(f"Enabled optimization strategy: {strategy.value}")
    
    async def disable_strategy(self, strategy: OptimizationStrategy):
        """Disable an optimization strategy"""
        self.enabled_strategies.discard(strategy)
        self.logger.info(f"Disabled optimization strategy: {strategy.value}")
    
    async def clear_cache(self, cache_type: Optional[CacheType] = None):
        """Clear cache entries"""
        if self.cache_manager:
            if cache_type:
                await self.cache_manager.invalidate_by_pattern("*", cache_type)
            else:
                await self.cache_manager.invalidate_by_pattern("*")
            
            self.logger.info(f"Cleared cache for type: {cache_type.value if cache_type else 'all'}")
    
    # Private methods
    async def _execute_llm_request(
        self, 
        model: str, 
        messages: List[Dict], 
        tools: Optional[List[Dict]], 
        request_func, 
        **kwargs
    ) -> Any:
        """Execute LLM request with metrics tracking"""
        self.metrics.total_requests += 1
        
        if request_func:
            return await request_func(model=model, messages=messages, tools=tools, **kwargs)
        else:
            raise ValueError("No request function provided")
    
    async def _smart_retry_request(
        self, 
        model: str, 
        messages: List[Dict], 
        tools: Optional[List[Dict]], 
        request_func, 
        original_error: Exception, 
        **kwargs
    ) -> Any:
        """Smart retry with exponential backoff"""
        max_retries = 3
        base_delay = 1.0
        
        for attempt in range(max_retries):
            self.metrics.retry_attempts += 1
            delay = base_delay * (2 ** attempt)
            
            self.logger.warning(
                f"Retrying LLM request (attempt {attempt + 1}/{max_retries}) "
                f"after {delay}s delay. Original error: {original_error}"
            )
            
            await asyncio.sleep(delay)
            
            try:
                return await self._execute_llm_request(
                    model, messages, tools, request_func, **kwargs
                )
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                original_error = e
        
        raise original_error
    
    def _update_response_time_metrics(self, response_time: float):
        """Update response time metrics"""
        self.metrics.recent_response_times.append(response_time)
        
        # Update aggregated metrics
        total_requests = self.metrics.total_requests
        if total_requests == 1:
            self.metrics.average_response_time = response_time
        else:
            # Running average
            self.metrics.average_response_time = (
                (self.metrics.average_response_time * (total_requests - 1) + response_time) / 
                total_requests
            )
        
        self.metrics.min_response_time = min(self.metrics.min_response_time, response_time)
        self.metrics.max_response_time = max(self.metrics.max_response_time, response_time)
    
    async def _optimization_loop(self):
        """Background optimization loop"""
        while self._is_running:
            try:
                # Process batch queues
                await self._process_batch_queues()
                
                # Resource pool maintenance
                await self._maintain_resource_pools()
                
                await asyncio.sleep(1)  # Check every second
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in optimization loop: {e}")
                await asyncio.sleep(5)
    
    async def _process_batch_queues(self):
        """Process queued batch requests"""
        current_time = datetime.utcnow()
        
        for batch_id, batch_request in list(self.batch_queues.items()):
            # Check if batch should be processed
            should_process = (
                len(batch_request.requests) >= batch_request.max_batch_size or
                current_time - batch_request.created_at >= batch_request.max_wait_time
            )
            
            if should_process:
                # Process batch (implementation depends on specific use case)
                self.logger.debug(f"Processing batch {batch_id} with {len(batch_request.requests)} requests")
                del self.batch_queues[batch_id]
    
    async def _maintain_resource_pools(self):
        """Maintain resource pools for efficient resource reuse"""
        # Implementation for resource pool maintenance
        # This could include connection pools, thread pools, etc.
        pass
    
    async def _metrics_collection_loop(self):
        """Background metrics collection loop"""
        while self._is_running:
            try:
                # Collect system metrics
                await self._collect_system_metrics()
                
                await asyncio.sleep(30)  # Collect every 30 seconds
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.error(f"Error in metrics collection: {e}")
                await asyncio.sleep(60)
    
    async def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            import psutil
            
            # CPU usage
            cpu_usage = psutil.cpu_percent(interval=None)
            self.metrics.average_cpu_usage = (
                self.metrics.average_cpu_usage * 0.9 + cpu_usage * 0.1
            )
            
            # Memory usage
            memory_info = psutil.virtual_memory()
            current_memory_mb = memory_info.used / (1024 * 1024)
            self.metrics.peak_memory_usage = max(
                self.metrics.peak_memory_usage, 
                current_memory_mb
            )
            
        except ImportError:
            # psutil not available, skip system metrics
            pass
        except Exception as e:
            self.logger.debug(f"Error collecting system metrics: {e}")


# Global optimizer instance
_performance_optimizer: Optional[PerformanceOptimizer] = None

async def get_performance_optimizer() -> PerformanceOptimizer:
    """Get global performance optimizer instance"""
    global _performance_optimizer
    
    if _performance_optimizer is None:
        _performance_optimizer = PerformanceOptimizer()
        await _performance_optimizer.start()
    
    return _performance_optimizer

async def shutdown_performance_optimizer():
    """Shutdown global performance optimizer"""
    global _performance_optimizer
    
    if _performance_optimizer:
        await _performance_optimizer.stop()
        _performance_optimizer = None