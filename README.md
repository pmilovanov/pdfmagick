# PDFMagick 🪄

A high-performance PDF processing application for adjusting image quality, applying advanced filters, and preparing PDFs for optimal printing on consumer printers.

## ✨ Features

### Core Capabilities
- **Real-time image filtering**: Brightness, contrast, exposure, saturation, vibrance, and sharpness
- **Advanced tone controls**: Separate adjustments for highlights, midtones, and shadows
- **Professional color grading**: Black/white point adjustment and gamma correction
- **Per-page settings**: Apply different filters to different pages
- **Auto-enhance**: One-click optimization for each page

### Export & Layout Options
- **Smart page sizing**: Automatic DPI adjustment for target page dimensions
- **2-up layouts**: Print two pages per sheet with sequential or booklet ordering
  - **Sequential mode**: Pages arranged in order (1,2 | 3,4 | 5,6...)
  - **Cut & stack mode**: Special imposition for DIY booklet printing
- **Page numbering**: Automatic page number addition with customizable format
- **Alternating padding**: For double-sided printing with trimming
- **Multiple formats**: Export as PDF, JPEG, or WebP with quality control

#### 2-up Layout Details

The 2-up layout feature allows efficient printing by placing two pages side-by-side on landscape-oriented sheets.

**Sequential Mode:**
- Simplest mode: pages appear in order across sheets
- Page 1 & 2 on first sheet, 3 & 4 on second sheet, etc.
- Ideal for documents that don't need booklet binding

**Cut & Stack Mode (Booklet Printing):**
- Special arrangement for creating booklets
- After printing double-sided, cut sheets vertically down the middle
- Stack the halves to create a sequential booklet
- Perfect for DIY booklet binding

**Configuration Options:**
- Vertical alignment: Top or center positioning of pages
- Works with all standard page sizes (Letter, A4, Legal, etc.)
- Requires target page size to be specified

### Performance Features
- **Intelligent caching**: LRU cache for rendered pages and filtered images
- **Optimized rendering**: Dynamic DPI calculation based on display/export needs
- **Direct API access**: Bypasses proxy overhead for image operations
- **Efficient memory usage**: Cache size limits with automatic eviction

## 🏗️ Architecture

PDFMagick features a modern full-stack architecture with Vue/Nuxt frontend and FastAPI backend:

### Component Overview

```
┌─────────────────┐
│   Vue 3 + Nuxt  │
│    Frontend     │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   FastAPI       │
│   Backend       │
└────────┬────────┘
         │
         ↓
┌─────────────────┐
│   Core Modules  │
│  (Shared Logic) │
└─────────────────┘
```

### Project Structure

```
pdfmagick/
├── core/                    # Shared PDF processing logic
│   ├── pdf_processor.py     # PDF manipulation and rendering
│   ├── image_filters.py     # Image filtering + 2-up layout algorithms
│   └── cache_manager.py     # Unified caching layer
├── api/                     # FastAPI backend
│   ├── main.py             # API endpoints and WebSocket handlers
│   └── models.py           # Pydantic models for validation
├── web/                     # Vue/Nuxt frontend
│   ├── pages/              # Application pages
│   ├── components/         # Vue components
│   │   ├── FilterPanel.vue      # Filter controls UI
│   │   ├── ImageComparison.vue  # Before/after view
│   │   ├── PageNavigator.vue    # Page navigation
│   │   ├── ExportDialog.vue     # Export configuration
│   │   └── ...
│   └── stores/             # Pinia state management
│       └── pdf.ts          # PDF state and operations
├── tests/                   # Test suite
│   ├── conftest.py         # Shared pytest fixtures
│   ├── test_2up_functionality.py   # 2-up layout tests (13 tests)
│   ├── test_auto_enhance.py        # Auto-enhance tests (11 tests)
│   └── test_auto_enhance_api.py    # API integration tests (9 tests)
└── run_*.py                # Application launchers
```

## 🚀 Installation

### Prerequisites
- Python 3.11+
- Node.js 18+ (for Vue frontend)
- uv (recommended) or pip

### Install Dependencies

```bash
# Clone the repository
git clone https://github.com/yourusername/pdfmagick.git
cd pdfmagick

# Install Python dependencies using uv (recommended)
uv pip install -e .

# Or using pip
pip install -e .

# Install frontend dependencies (for Vue/Nuxt version)
cd web
npm install
cd ..
```

## 🎯 Usage

### Quick Start
```bash
# Run both API and Vue frontend
python run_new.py
```
- 🌐 Web App: http://localhost:3000
- 📚 API Docs: http://localhost:8000/docs

### Development Mode

Run components separately for development:

```bash
# Terminal 1: API Backend
python run_api.py

# Terminal 2: Vue Frontend
cd web
npm run dev
```

### Using 2-up Layout

1. Upload your PDF using the web interface
2. Adjust filters as needed for each page
3. Click "Export PDF" button
4. In the Export Dialog:
   - Select a **Page Size** (required for 2-up)
   - Enable **2-up layout** checkbox
   - Choose **Layout mode**: Sequential or Cut & Stack
   - Select **Vertical alignment**: Top or Center
   - Configure other export options as desired
5. Click "Export PDF" to download

**Note:** Target page size must be specified for 2-up to work. The output will be in landscape orientation (width and height swapped).

## 📡 API Endpoints

### Core Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/pdf/upload` | Upload PDF file |
| GET | `/api/pdf/{pdf_id}/page/{page_num}/render` | Render page as image |
| POST | `/api/pdf/{pdf_id}/page/{page_num}/filter` | Apply filters to page |
| POST | `/api/pdf/{pdf_id}/export` | Export processed PDF |

### Cache Management

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/cache/stats` | Get cache statistics |
| DELETE | `/api/cache/clear/{pdf_id}` | Clear cache for PDF |

### Query Parameters

**Render endpoint:**
- `dpi`: 30-600 (default: 150)
- `format`: webp, jpeg, png (default: webp)
- `quality`: 1-100 (default: 85)

## 🎨 Filter Settings

All filters can be adjusted with the following ranges:

| Filter | Range | Default | Description |
|--------|-------|---------|-------------|
| brightness | -100 to 100 | 0 | Overall image brightness |
| contrast | -100 to 100 | 0 | Image contrast |
| highlights | -100 to 100 | 0 | Bright area adjustment |
| midtones | -100 to 100 | 0 | Middle tone adjustment |
| shadows | -100 to 100 | 0 | Dark area adjustment |
| exposure | -3 to 3 | 0 | Exposure compensation |
| saturation | -100 to 100 | 0 | Color intensity |
| vibrance | -100 to 100 | 0 | Smart saturation |
| sharpness | -100 to 100 | 0 | Edge enhancement |
| black_point | 0 to 255 | 0 | Black level |
| white_point | 0 to 255 | 255 | White level |
| gamma | 0.1 to 3.0 | 1.0 | Gamma correction |

## 🛠️ Technology Stack

### Backend
- **FastAPI**: High-performance async API framework
- **PyMuPDF (fitz)**: PDF rendering and manipulation
- **Pillow**: Image processing and filtering
- **OpenCV**: Advanced image operations
- **Pydantic**: Data validation and serialization

### Frontend (Vue/Nuxt)
- **Vue 3**: Reactive UI framework
- **Nuxt 3**: Full-stack Vue framework
- **TypeScript**: Type-safe development
- **Pinia**: State management
- **Vite**: Fast build tooling

### Infrastructure
- **uvicorn**: ASGI server
- **WebSockets**: Real-time updates
- **LRU Cache**: Intelligent memory management

## 🔧 Development

### Running Tests
```bash
# Run all tests
uv run pytest tests/

# Run with verbose output
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_2up_functionality.py -v
```

**Test Coverage:**
- 13 tests for 2-up layout functionality (all passing)
- Helper function tests (cut-and-stack algorithm, page compositing)
- Integration tests (sequential and booklet modes)
- Multiple page size formats (Letter, A4, Legal)

### Code Style
- Python: Black + Ruff
- TypeScript/Vue: ESLint + Prettier

### Performance Tips
- Large PDFs benefit from lower preview DPI (50-100)
- Export at 300 DPI for print quality
- Use JPEG format for faster processing
- WebP provides best quality/size ratio
- 2-up layout processes pages sequentially during export

## 📈 Performance Characteristics

- **Page Rendering**: ~20-70ms at 100 DPI (typical)
- **Filter Application**: ~10-30ms per operation
- **Cache Hit Rate**: >90% during typical usage
- **Memory Usage**: Configurable cache size (default 100MB)

## 🔧 Troubleshooting

### Common Issues

**Issue: 2-up layout not being applied**
- **Solution**: Make sure to select a target page size in the Export Dialog. 2-up requires a page size to determine landscape dimensions.

**Issue: Port 8000 already in use**
- **Solution**: Find and kill the process using port 8000:
  ```bash
  lsof -i :8000 | grep LISTEN
  kill <PID>
  ```

**Issue: Slow page switching in UI**
- **Solution**: The frontend uses direct FastAPI access to avoid proxy overhead. If using Nuxt dev server, this is expected to be slower than production.

**Issue: Memory usage growing**
- **Solution**: The cache manager implements LRU eviction at 100MB default. For very large PDFs, restart the server to clear cache.

**Issue: Export seems frozen**
- **Cause**: Export is a blocking operation, especially for large PDFs or high DPI
- **Solution**: Wait for completion. Consider using lower DPI for large documents.

For more detailed troubleshooting, see `CLAUDE.md`.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- PyMuPDF team for excellent PDF handling
- FastAPI for the incredible async framework
- Vue.js team for the reactive UI system
- The open-source community

---

**Note**: PDFMagick features a production-ready Vue/Nuxt frontend with FastAPI backend, comprehensive testing (33+ tests), and histogram-based auto-enhancement.