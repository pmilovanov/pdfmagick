"""Unified cache manager for PDFMagick."""

import hashlib
import json
from typing import Optional, Dict, Any, Tuple
from PIL import Image
import io
from functools import lru_cache
import threading


class CacheManager:
    """Singleton cache manager shared between Streamlit and FastAPI.

    Provides efficient caching for:
    - Rendered PDF pages at various DPIs
    - Processed images with filter combinations
    - PDF document instances
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._pdf_cache = {}  # {pdf_id: PDFProcessor}
        self._render_cache = {}  # {(pdf_id, page_num, dpi): PIL.Image}
        self._filter_cache = LRUCache(maxsize=100)  # Recent filter combinations
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }

    def get_pdf(self, pdf_id: str) -> Optional[Any]:
        """Get cached PDF processor instance."""
        return self._pdf_cache.get(pdf_id)

    def set_pdf(self, pdf_id: str, pdf_processor: Any) -> None:
        """Cache a PDF processor instance."""
        self._pdf_cache[pdf_id] = pdf_processor

    def get_rendered_page(self, pdf_id: str, page_num: int, dpi: int) -> Optional[Image.Image]:
        """Get cached rendered page."""
        key = (pdf_id, page_num, dpi)
        if key in self._render_cache:
            self._cache_stats['hits'] += 1
            return self._render_cache[key]
        self._cache_stats['misses'] += 1
        return None

    def set_rendered_page(self, pdf_id: str, page_num: int, dpi: int, image: Image.Image) -> None:
        """Cache a rendered page."""
        key = (pdf_id, page_num, dpi)

        # Simple memory management - limit cache size
        if len(self._render_cache) > 200:  # Max 200 rendered pages
            # Remove oldest entries (simple FIFO for now)
            oldest_keys = list(self._render_cache.keys())[:50]
            for k in oldest_keys:
                del self._render_cache[k]
                self._cache_stats['evictions'] += 1

        self._render_cache[key] = image

    def get_filtered_image(self, pdf_id: str, page_num: int, dpi: int,
                          filter_settings: Dict[str, Any]) -> Optional[Image.Image]:
        """Get cached filtered image."""
        # Create cache key from filter settings
        filter_hash = self._hash_filters(filter_settings)
        key = f"{pdf_id}:{page_num}:{dpi}:{filter_hash}"

        result = self._filter_cache.get(key)
        if result:
            self._cache_stats['hits'] += 1
        else:
            self._cache_stats['misses'] += 1
        return result

    def set_filtered_image(self, pdf_id: str, page_num: int, dpi: int,
                          filter_settings: Dict[str, Any], image: Image.Image) -> None:
        """Cache a filtered image."""
        filter_hash = self._hash_filters(filter_settings)
        key = f"{pdf_id}:{page_num}:{dpi}:{filter_hash}"
        self._filter_cache.set(key, image)

    def _hash_filters(self, filter_settings: Dict[str, Any]) -> str:
        """Create a hash of filter settings for cache key."""
        # Sort keys for consistent hashing
        sorted_filters = json.dumps(filter_settings, sort_keys=True)
        return hashlib.md5(sorted_filters.encode()).hexdigest()[:12]

    def clear_pdf_cache(self, pdf_id: str) -> None:
        """Clear all cache entries for a specific PDF."""
        # Remove PDF processor
        if pdf_id in self._pdf_cache:
            del self._pdf_cache[pdf_id]

        # Remove rendered pages
        keys_to_remove = [k for k in self._render_cache.keys() if k[0] == pdf_id]
        for key in keys_to_remove:
            del self._render_cache[key]

        # Clear filter cache entries for this PDF
        self._filter_cache.clear_pdf(pdf_id)

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            **self._cache_stats,
            'pdf_count': len(self._pdf_cache),
            'rendered_pages': len(self._render_cache),
            'filtered_images': self._filter_cache.size()
        }

    def clear_all(self) -> None:
        """Clear all caches."""
        self._pdf_cache.clear()
        self._render_cache.clear()
        self._filter_cache.clear()
        self._cache_stats = {
            'hits': 0,
            'misses': 0,
            'evictions': 0
        }


class LRUCache:
    """Simple LRU cache implementation for filtered images."""

    def __init__(self, maxsize: int = 100):
        self.maxsize = maxsize
        self._cache = {}
        self._access_order = []

    def get(self, key: str) -> Optional[Image.Image]:
        """Get item from cache and update access order."""
        if key in self._cache:
            # Move to end (most recently used)
            self._access_order.remove(key)
            self._access_order.append(key)
            return self._cache[key]
        return None

    def set(self, key: str, value: Image.Image) -> None:
        """Add item to cache with LRU eviction."""
        if key in self._cache:
            # Update existing
            self._access_order.remove(key)
        elif len(self._cache) >= self.maxsize:
            # Evict least recently used
            lru_key = self._access_order.pop(0)
            del self._cache[lru_key]

        self._cache[key] = value
        self._access_order.append(key)

    def clear_pdf(self, pdf_id: str) -> None:
        """Clear entries for a specific PDF."""
        keys_to_remove = [k for k in self._cache.keys() if k.startswith(f"{pdf_id}:")]
        for key in keys_to_remove:
            del self._cache[key]
            self._access_order.remove(key)

    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._access_order.clear()

    def size(self) -> int:
        """Get current cache size."""
        return len(self._cache)