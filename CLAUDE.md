# CLAUDE.md - AI Assistant Development Guide

This document provides architectural insights and development guidance specifically for AI assistants working on the PDFMagick codebase.

For general project information, see @README.md

## 🧠 Architectural Deep Dive

### Core Design Philosophy

PDFMagick follows a **layered architecture** with clear separation of concerns:

1. **Core Layer** (`core/`): Pure Python PDF/image processing logic, framework-agnostic
2. **API Layer** (`api/`): FastAPI backend providing RESTful endpoints
3. **Frontend Layer** (`web/`): Vue 3/Nuxt 3 reactive UI

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

### Issue: 2-up Layout Not Applied

**Cause:** `target_page_size` not set in export request

**Solution:** 2-up requires a target page size to determine landscape dimensions. Always set `target_page_size` when `two_up_enabled: true`:

```json
{
  "two_up_enabled": true,
  "target_page_size": [8.5, 11.0],  // Required!
  "layout_mode": "sequential"
}
```

### Issue: 2-up Pages in Wrong Order (Cut-and-Stack)

**Cause:** Misunderstanding of the cut-and-stack algorithm

**Solution:** The algorithm is designed for a specific workflow:
1. Print all sheets double-sided (flip on short edge)
2. Cut each sheet vertically down the center
3. Stack all left halves together, stack all right halves together
4. The stacks form a sequential booklet when properly ordered

Test with a small document (4-8 pages) first to understand the pattern.

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

### 5. 2-up Layout Implementation (`core/image_filters.py` + `api/main.py`)

The 2-up functionality creates landscape sheets with two pages side-by-side for efficient printing.

**Cut-and-Stack Algorithm** (`arrange_pages_cut_and_stack()`):

For n pages, creates ceil(n/4) sheets. Each sheet has 4 positions:

```python
# For sheet i (0-indexed):
front_left = 2 * i + 1
front_right = 2 * sheets_count + 2 * i + 1
back_left = 2 * sheets_count + 2 * i + 2
back_right = 2 * i + 2
```

**Example with 8 pages:**
- Sheet 1: Front [1, 5], Back [6, 2]
- Sheet 2: Front [3, 7], Back [8, 4]

After printing double-sided and cutting vertically, stacking the halves creates a booklet.

**Compositing Logic** (`create_2up_page()`):
1. Creates landscape canvas (width and height swapped from target size)
2. Scales each page to fit in half-width while maintaining aspect ratio
3. Centers each page within its half (horizontally)
4. Applies vertical alignment (top or center)

**Critical Order of Operations** (in export endpoint):
1. Render page at export DPI
2. Apply filters (if set for that page)
3. Add page numbers (if enabled)
4. Add padding for trimming (if enabled)
5. **Then** composite into 2-up sheets
6. Generate final PDF with landscape dimensions

**Performance Notes:**
- 2-up composites are NOT cached (one-time operation during export)
- Composite images are ~2x larger than single pages
- Uses LANCZOS resampling for high quality
- Memory spike during export is expected and temporary

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

### ADR-004: 2-up Compositing at Export Time Only
**Date:** 2025-01
**Status:** Implemented
**Context:** 2-up layout requires combining pages into composite sheets
**Decision:** Perform 2-up compositing during export, not during preview
**Consequences:**
- **Pro**: Simpler architecture, no preview UI complexity
- **Pro**: No need to cache large composite images
- **Pro**: Users can preview individual pages with filters applied
- **Con**: Users cannot preview the 2-up layout before export
- **Con**: Must re-export to see layout changes

**Rationale**: Preview of 2-up would require significant UI changes (showing two pages at once, handling page navigation differently, etc.). The workflow (adjust filters → export → print) doesn't benefit much from 2-up preview since the goal is print output, not screen viewing.

### ADR-005: No Caching of 2-up Composites
**Date:** 2025-01
**Status:** Implemented
**Context:** 2-up creates large landscape composite images
**Decision:** Do not cache 2-up composite sheets
**Consequences:**
- **Pro**: Simpler cache management
- **Pro**: Lower memory footprint
- **Pro**: Export is a one-time operation anyway
- **Con**: Re-exporting with same settings requires regeneration

**Rationale**: Export is typically a one-time operation. The memory cost of caching composites (2x page size × number of sheets) would be substantial. Since users rarely export the same configuration multiple times, caching provides minimal benefit.

## 🧪 Testing

### Running Tests

```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_2up_functionality.py -v

# Run specific test class
uv run pytest tests/test_2up_functionality.py::Test2upHelperFunctions -v
```

### Test Coverage

**Current Test Suite** (`tests/test_2up_functionality.py`):
- 13 tests covering 2-up layout functionality
- 100% coverage of 2-up helper functions
- Integration tests with PDF generation

**Test Categories:**
1. **Helper Functions** (7 tests):
   - Cut-and-stack arrangement algorithm
   - 2-up page creation with various inputs
   - Edge cases (odd pages, blank pages, etc.)

2. **Integration** (3 tests):
   - Sequential 2-up with even/odd page counts
   - Cut-and-stack booklet generation
   - Full workflow from PDF to 2-up output

3. **Page Sizes** (3 parametrized tests):
   - Letter, A4, Legal formats
   - Dimension verification for each size

**Test Fixtures** (`tests/conftest.py`):
- `create_test_page`: Factory for generating test page images
- `create_test_pdf`: Factory for generating test PDF documents

**What's NOT Tested:**
- API endpoint integration (deliberately avoided to keep tests lightweight)
- Frontend ExportDialog component behavior
- WebSocket functionality
- Actual printer output (manual verification needed)

### Adding New Tests

When adding 2-up related features:

1. Add unit tests for any new helper functions in `core/image_filters.py`
2. Add integration test if the feature changes the export pipeline
3. Use existing fixtures for consistency
4. Keep tests focused on logic, not HTTP/UI behavior

---

**Remember:** When in doubt, optimize for user experience over code elegance. PDFMagick is a tool for working with potentially massive documents - performance matters.