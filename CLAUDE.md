# CLAUDE.md - AI Assistant Development Guide

This document provides architectural insights and development guidance specifically for AI assistants working on the PDFMagick codebase.

For general project information, see @README.md

## 🧠 Architectural Deep Dive

### Core Design Philosophy

PDFMagick follows a **layered architecture** with clear separation of concerns:

1. **Core Layer** (`core/`): Pure Python PDF/image processing logic, framework-agnostic
2. **API Layer** (`api/`): FastAPI backend providing RESTful endpoints
3. **Frontend Layer** (`web/`): Vue 3/Nuxt 3 reactive UI
4. **Legacy Layer** (`src/`): Original Streamlit implementation (stable but not actively developed)

### Critical Performance Paths

#### Image Rendering Pipeline
```
PDF Document → PyMuPDF → PIL Image → Filters → Cached Result
                ↓                        ↓
            (fitz.Matrix)          (OpenCV/Pillow)
```

**Key Bottlenecks:**
- PDF rendering at high DPI (>300) can consume significant memory
- Filter application is CPU-bound, especially sharpness
- Network transfer of large images (avoided by direct FastAPI access)

#### Caching Strategy

The cache manager uses a two-tier approach:
1. **Rendered pages**: Original PDF pages at specific DPI
2. **Filtered images**: Pages with applied filter settings

Cache keys: `{pdf_id}_{page_num}_{dpi}_{filters_hash}`

**Important:** Cache is in-memory only. Restarting the server clears all cached data.

### Frontend State Management

The Pinia store (`web/stores/pdf.ts`) manages:
- PDF metadata and page dimensions
- Original and processed image URLs
- Per-page filter settings
- UI state (current page, loading status)

**Critical Functions:**
- `loadPage()`: Fetches and caches page images
- `applyFilters()`: Sends filter settings to backend
- `autoEnhance()`: Applies smart enhancement algorithm

### DPI Calculation Logic

The system dynamically calculates DPI based on context:

1. **Preview Mode**: Target 700px height → DPI = 700 / page_height_inches
2. **Export Mode**: If target page size specified → DPI = base_dpi * scale_factor
3. **Constraints**: Always between 30-600 DPI (API validation)

## 🔍 Common Issues and Solutions

### Issue: 422 Unprocessable Entity on Filter API

**Cause:** DPI value below minimum constraint (30)

**Solution:** Ensure DPI calculation includes `Math.max(30, calculatedDpi)`

```typescript
const dpi = Math.max(30, Math.min(calculatedDpi, 100))
```

### Issue: Slow Page Switching

**Causes:**
1. Nuxt dev server proxy overhead (~200-300ms)
2. Oversized images for display resolution
3. Cache misses on first view

**Solutions:**
1. Direct FastAPI access: `http://localhost:8000/api/...`
2. Calculate appropriate DPI for display size
3. Consider preloading adjacent pages

### Issue: Memory Growth with Large PDFs

**Cause:** Unbounded cache growth

**Solution:** Cache manager implements LRU eviction at 100MB default

### Issue: Export Progress Not Visible

**Current Limitation:** Export is a single blocking HTTP request

**Future Solution:** Implement SSE or WebSocket progress updates

## 🛠️ Development Workflow

### Testing Changes

1. **Backend changes**: Restart `run_api.py` or `run_new.py`
2. **Frontend changes**: Hot-reload automatic with Nuxt dev server
3. **Core module changes**: Restart all Python processes

### Adding New Filters

1. Add to `FilterSettings` model in `api/models.py`
2. Implement in `core/image_filters.py`
3. Add UI control in `web/components/FilterPanel.vue`
4. Update filter state in `web/stores/pdf.ts`

### Performance Profiling

```python
# Add to api/main.py for timing analysis
import time
start = time.perf_counter()
# ... operation ...
logger.info(f"Operation took {time.perf_counter() - start:.3f}s")
```

## 🚨 Critical Code Sections

### 1. Filter Application (`core/image_filters.py`)

The `apply_all_adjustments()` function is the hot path for all image processing. Order matters:
1. Exposure/brightness/contrast (basic adjustments)
2. Shadows/midtones/highlights (tone mapping)
3. Color adjustments (saturation/vibrance)
4. Sharpness (most expensive, do last)

### 2. Page Rendering (`core/pdf_processor.py`)

```python
mat = fitz.Matrix(dpi/72.0, dpi/72.0)
pix = page.get_pixmap(matrix=mat, alpha=False)
```

The `alpha=False` is critical for performance - alpha channel adds 25% overhead.

### 3. Cache Key Generation

Filter settings are hashed to create cache keys. Any change to filter structure invalidates cache.

### 4. Frontend Image Loading (`web/stores/pdf.ts`)

Direct FastAPI URLs bypass Nuxt proxy:
```typescript
const url = `http://localhost:8000/api/pdf/${pdfId}/page/${pageNum}/render`
```

## 📊 Performance Benchmarks

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Render page @ 100 DPI | 20-70ms | Depends on page complexity |
| Apply all filters | 10-30ms | Sharpness is slowest |
| Cache lookup | <1ms | In-memory dictionary |
| Network transfer (local) | 5-10ms | Direct FastAPI access |
| Nuxt proxy overhead | 200-300ms | Avoided in production |

## 🔮 Future Improvements

### High Priority
1. **Progress indicators for export**: Implement SSE or WebSocket
2. **Persistent cache**: Redis or disk-based caching
3. **Batch operations**: Process multiple pages in parallel
4. **WebAssembly filters**: Client-side filter preview

### Medium Priority
1. **PDF optimization**: Reduce file size post-export
2. **Undo/redo**: Filter history management
3. **Presets**: Save and load filter combinations
4. **Keyboard shortcuts**: Power user features

### Low Priority
1. **Cloud storage integration**: S3/GCS support
2. **Collaborative editing**: Multi-user sessions
3. **Plugin system**: Custom filter extensions
4. **Mobile responsive UI**: Touch-optimized controls

## 🐛 Known Quirks

1. **Page dimensions**: PyMuPDF uses points (1/72 inch), not pixels
2. **Cache invalidation**: No automatic invalidation on PDF replacement
3. **Filter order**: Some combinations produce unexpected results
4. **Memory spikes**: Large PDFs at high DPI can consume GB of RAM
5. **Export blocking**: UI freezes during large exports

## 💡 Development Tips

1. **Always test with large PDFs** (100+ pages) to catch performance issues
2. **Monitor memory usage** - cache can grow quickly
3. **Use browser DevTools Network tab** to identify slow requests
4. **Check console for DPI calculations** - ensures optimal rendering
5. **Test filter combinations** - some interact in non-obvious ways

## 🔧 Debugging Commands

```bash
# Watch API logs
tail -f the console output from run_api.py

# Monitor cache stats
curl http://localhost:8000/api/cache/stats

# Test filter endpoint directly
curl -X POST http://localhost:8000/api/pdf/{pdf_id}/page/0/filter \
  -H "Content-Type: application/json" \
  -d '{"filters": {...}, "dpi": 100}'

# Check memory usage
ps aux | grep python | grep -E "run_api|run_new"
```

## 📝 Code Style Guidelines

### Python
- Type hints for all functions
- Docstrings for public methods
- Use `logger.info()` for important operations
- Handle exceptions explicitly

### TypeScript/Vue
- Composition API preferred
- Type all props and emits
- Use `computed` for derived state
- Avoid `any` type

### Git Commits
- Prefix: `fix:`, `feat:`, `perf:`, `refactor:`
- Present tense, imperative mood
- Reference issue numbers when applicable

## 🏗️ Architecture Decisions Record (ADR)

### ADR-001: Direct FastAPI Access from Frontend
**Date:** 2024
**Status:** Implemented
**Context:** Nuxt dev proxy adds 200-300ms latency
**Decision:** Use direct `http://localhost:8000` URLs for image endpoints
**Consequences:** Faster image loading, CORS must be configured

### ADR-002: Dynamic DPI Calculation
**Date:** 2024
**Status:** Implemented
**Context:** Fixed DPI wastes resources for different display/export sizes
**Decision:** Calculate DPI based on target dimensions
**Consequences:** Optimal performance, complex calculation logic

### ADR-003: In-Memory Caching Only
**Date:** 2024
**Status:** Current
**Context:** Simplicity vs persistence trade-off
**Decision:** Use in-memory cache with LRU eviction
**Consequences:** Fast access, lost on restart, memory constraints

---

**Remember:** When in doubt, optimize for user experience over code elegance. PDFMagick is a tool for working with potentially massive documents - performance matters.