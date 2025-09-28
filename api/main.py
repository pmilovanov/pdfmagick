"""FastAPI backend for PDFMagick."""

import hashlib
import io
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, File, UploadFile, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Add parent directory to path for core imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from core import PDFProcessor, ImageFilters
from core.cache_manager import CacheManager
from api.models import (
    FilterSettings, PageRenderRequest, PageFilterRequest,
    PDFInfo, ExportRequest, CacheStats, WebSocketMessage
)

app = FastAPI(title="PDFMagick API", version="1.0.0")

# Configure CORS for Vue frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Vue dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize cache manager (singleton)
cache = CacheManager()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "running", "service": "PDFMagick API"}


@app.post("/api/pdf/upload", response_model=PDFInfo)
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a PDF file and get its information."""
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    # Generate unique PDF ID
    pdf_content = await file.read()
    pdf_id = hashlib.md5(pdf_content).hexdigest()[:12]

    # Check if already cached
    if cache.get_pdf(pdf_id):
        pdf_proc = cache.get_pdf(pdf_id)
    else:
        # Create PDF processor and cache it
        try:
            pdf_proc = PDFProcessor(pdf_bytes=pdf_content)
            cache.set_pdf(pdf_id, pdf_proc)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid PDF: {str(e)}")

    # Get page dimensions
    page_dimensions = []
    for i in range(pdf_proc.page_count):
        width, height = pdf_proc.get_page_dimensions(i)
        page_dimensions.append({
            "width": width,
            "height": height,
            "width_inches": width / 72,
            "height_inches": height / 72
        })

    return PDFInfo(
        pdf_id=pdf_id,
        filename=file.filename,
        page_count=pdf_proc.page_count,
        page_dimensions=page_dimensions
    )


@app.get("/api/pdf/{pdf_id}/page/{page_num}/render")
async def render_page(
    pdf_id: str,
    page_num: int,
    dpi: int = 150,
    format: str = "webp",
    quality: int = 85
):
    """Render a PDF page as an image."""
    start_time = time.time()

    pdf_proc = cache.get_pdf(pdf_id)
    if not pdf_proc:
        raise HTTPException(status_code=404, detail="PDF not found")

    if page_num < 0 or page_num >= pdf_proc.page_count:
        raise HTTPException(status_code=400, detail="Invalid page number")

    # Check cache first
    cache_check_start = time.time()
    image = cache.get_rendered_page(pdf_id, page_num, dpi)
    cache_hit = image is not None
    cache_time = time.time() - cache_check_start

    if not image:
        # Render and cache
        render_start = time.time()
        try:
            image = pdf_proc.get_page_as_image(page_num, dpi)
            cache.set_rendered_page(pdf_id, page_num, dpi, image)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Render error: {str(e)}")
        render_time = time.time() - render_start
        logger.info(f"Rendered page {page_num} at {dpi}dpi in {render_time:.3f}s (size: {image.size})")
    else:
        render_time = 0
        logger.info(f"Cache hit for page {page_num} at {dpi}dpi (cache check: {cache_time:.3f}s)")

    # Convert to requested format
    encode_start = time.time()
    img_bytes = io.BytesIO()
    if format == "webp":
        # Use method=0 for fastest encoding (still good quality for previews)
        image.save(img_bytes, format='WEBP', quality=quality, method=0)
        media_type = "image/webp"
    elif format == "jpeg":
        if image.mode == 'RGBA':
            rgb_image = Image.new('RGB', image.size, (255, 255, 255))
            rgb_image.paste(image, mask=image.split()[3])
            image = rgb_image
        image.save(img_bytes, format='JPEG', quality=quality, optimize=True)
        media_type = "image/jpeg"
    else:  # png
        image.save(img_bytes, format='PNG', optimize=True)
        media_type = "image/png"

    encode_time = time.time() - encode_start
    total_time = time.time() - start_time

    logger.info(f"Page {page_num} total: {total_time:.3f}s (render: {render_time:.3f}s, encode {format}: {encode_time:.3f}s, cache: {'HIT' if cache_hit else 'MISS'})")

    img_bytes.seek(0)

    # Add cache headers for browser caching
    headers = {
        "Cache-Control": "private, max-age=3600",  # Cache for 1 hour
        "ETag": f"{pdf_id}-{page_num}-{dpi}-{format}-{quality}"
    }

    return StreamingResponse(img_bytes, media_type=media_type, headers=headers)


@app.post("/api/pdf/{pdf_id}/page/{page_num}/filter")
async def apply_filters(
    pdf_id: str,
    page_num: int,
    request: PageFilterRequest
):
    """Apply filters to a PDF page and return the processed image."""
    start_time = time.time()
    logger.info(f"Applying filters to page {page_num} at {request.dpi}dpi")

    pdf_proc = cache.get_pdf(pdf_id)
    if not pdf_proc:
        raise HTTPException(status_code=404, detail="PDF not found")

    if page_num < 0 or page_num >= pdf_proc.page_count:
        raise HTTPException(status_code=400, detail="Invalid page number")

    # Check filter cache first
    filter_dict = request.filters.dict()
    cache_start = time.time()
    filtered_image = cache.get_filtered_image(pdf_id, page_num, request.dpi, filter_dict)
    cache_time = time.time() - cache_start
    filter_cache_hit = filtered_image is not None

    if not filtered_image:
        # Get rendered page (from cache or render)
        render_start = time.time()
        base_image = cache.get_rendered_page(pdf_id, page_num, request.dpi)
        base_cache_hit = base_image is not None

        if not base_image:
            base_image = pdf_proc.get_page_as_image(page_num, request.dpi)
            cache.set_rendered_page(pdf_id, page_num, request.dpi, base_image)
        render_time = time.time() - render_start

        # Apply filters
        filter_start = time.time()
        try:
            filtered_image = ImageFilters.apply_all_adjustments(
                base_image,
                **filter_dict
            )
            # Cache the result
            cache.set_filtered_image(pdf_id, page_num, request.dpi, filter_dict, filtered_image)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Filter error: {str(e)}")
        filter_time = time.time() - filter_start

        logger.info(f"Filter processing: render {render_time:.3f}s (cache: {base_cache_hit}), filter {filter_time:.3f}s")
    else:
        logger.info(f"Filter cache HIT (lookup: {cache_time:.3f}s)")

    # Convert to requested format
    encode_start = time.time()
    img_bytes = io.BytesIO()
    if request.format == "webp":
        # Use method=0 for fastest encoding (still good quality for previews)
        filtered_image.save(img_bytes, format='WEBP', quality=request.quality, method=0)
        media_type = "image/webp"
    elif request.format == "jpeg":
        if filtered_image.mode == 'RGBA':
            rgb_image = Image.new('RGB', filtered_image.size, (255, 255, 255))
            rgb_image.paste(filtered_image, mask=filtered_image.split()[3])
            filtered_image = rgb_image
        filtered_image.save(img_bytes, format='JPEG', quality=request.quality, optimize=True)
        media_type = "image/jpeg"
    else:  # png
        filtered_image.save(img_bytes, format='PNG', optimize=True)
        media_type = "image/png"

    encode_time = time.time() - encode_start
    total_time = time.time() - start_time

    logger.info(f"Filter total: {total_time:.3f}s (encode {request.format}: {encode_time:.3f}s, filter cache: {'HIT' if filter_cache_hit else 'MISS'})")

    img_bytes.seek(0)
    return StreamingResponse(img_bytes, media_type=media_type)


@app.post("/api/pdf/{pdf_id}/export")
async def export_pdf(pdf_id: str, request: ExportRequest):
    """Export the processed PDF with all filters applied."""
    pdf_proc = cache.get_pdf(pdf_id)
    if not pdf_proc:
        raise HTTPException(status_code=404, detail="PDF not found")

    processed_images = []

    # Process each page
    for page_num in range(pdf_proc.page_count):
        # Skip pages before start_page if specified
        if request.start_page > 1 and page_num < request.start_page - 1:
            continue

        # Calculate effective DPI if target page size is specified
        # Note: Don't use effective DPI if padding is requested, as we want to render at full quality
        effective_dpi = request.dpi
        if request.target_page_size and not request.pad_to_exact_size:
            # Get original page dimensions
            page_rect = pdf_proc.doc[page_num].rect
            original_width_inches = page_rect.width / 72.0
            original_height_inches = page_rect.height / 72.0

            # Calculate scale factor to fit target size
            target_width, target_height = request.target_page_size
            scale_width = target_width / original_width_inches
            scale_height = target_height / original_height_inches
            scale = min(scale_width, scale_height)  # Maintain aspect ratio

            # Adjust DPI to render at target size
            effective_dpi = int(request.dpi * scale)
            logger.info(f"Page {page_num}: Original {original_width_inches:.1f}x{original_height_inches:.1f}\" -> "
                       f"Target {target_width}x{target_height}\" -> Effective DPI: {effective_dpi}")

        # Get page at calculated DPI
        image = pdf_proc.get_page_as_image(page_num, effective_dpi)

        # Apply filters if specified for this page
        if page_num in request.page_filters:
            filter_settings = request.page_filters[page_num]
            image = ImageFilters.apply_all_adjustments(
                image,
                **filter_settings.dict()
            )

        # Add page number if requested
        if request.add_page_numbers:
            # Calculate the actual page number (considering start_page offset)
            display_page_num = page_num + 1  # Convert from 0-indexed to 1-indexed

            # Scale font size based on DPI (font points to pixels)
            # Standard conversion: pixels = points * DPI / 72
            scaled_font_size = int(request.page_number_size * request.dpi / 72)
            scaled_margin = int(request.page_number_margin * request.dpi / 150)  # Scale margin relative to base DPI

            logger.info(f"Adding page number to page {page_num}: '{request.page_number_format}' "
                       f"font_size={scaled_font_size}px, margin={scaled_margin}px")

            image = ImageFilters.add_page_number(
                image,
                display_page_num,
                pdf_proc.page_count,
                format_style=request.page_number_format,
                font_size=scaled_font_size,
                margin=scaled_margin
            )

        # Apply padding if requested
        if request.pad_to_exact_size and request.target_page_size:
            target_width, target_height = request.target_page_size
            target_width_pixels = int(target_width * request.dpi)
            target_height_pixels = int(target_height * request.dpi)

            # Convert 0-indexed page_num to 1-indexed for padding alignment
            actual_page_num = page_num + 1

            # Log padding operation
            is_odd = (actual_page_num - request.first_odd_page) % 2 == 0
            alignment = "left" if is_odd else "right"
            logger.info(f"Page {page_num} (#{actual_page_num}): Padding from {image.width}x{image.height} to "
                       f"{target_width_pixels}x{target_height_pixels}, align {alignment}")

            image = ImageFilters.add_padding_for_exact_size(
                image,
                target_width_pixels,
                target_height_pixels,
                actual_page_num,
                request.first_odd_page
            )

        processed_images.append(image)

    # Handle 2-up layout if enabled
    if request.two_up_enabled and request.target_page_size:
        # Implementation would go here (simplified for now)
        pass

    # Generate PDF
    try:
        # Calculate target page size in points
        target_size = None
        if request.target_page_size:
            target_size = (request.target_page_size[0] * 72, request.target_page_size[1] * 72)

        pdf_bytes = PDFProcessor.images_to_pdf(
            processed_images,
            target_page_size=target_size,
            image_format=request.image_format.upper(),
            jpeg_quality=request.jpeg_quality
        )

        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=processed_{pdf_id}.pdf"
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Export error: {str(e)}")


@app.get("/api/cache/stats", response_model=CacheStats)
async def get_cache_stats():
    """Get cache statistics."""
    stats = cache.get_stats()
    return CacheStats(**stats)


@app.delete("/api/cache/clear/{pdf_id}")
async def clear_pdf_cache(pdf_id: str):
    """Clear cache for a specific PDF."""
    cache.clear_pdf_cache(pdf_id)
    return {"message": f"Cache cleared for PDF {pdf_id}"}


@app.websocket("/ws/preview/{client_id}")
async def websocket_preview(websocket: WebSocket, client_id: str):
    """WebSocket endpoint for real-time preview updates."""
    await websocket.accept()
    active_connections[client_id] = websocket

    try:
        while True:
            # Receive filter update request
            data = await websocket.receive_json()

            if data.get("type") == "filter_update":
                pdf_id = data.get("pdf_id")
                page_num = data.get("page_num")
                filters = FilterSettings(**data.get("filters", {}))
                dpi = data.get("dpi", 150)

                # Process the filter request
                pdf_proc = cache.get_pdf(pdf_id)
                if pdf_proc:
                    # Get or render base image
                    base_image = cache.get_rendered_page(pdf_id, page_num, dpi)
                    if not base_image:
                        base_image = pdf_proc.get_page_as_image(page_num, dpi)
                        cache.set_rendered_page(pdf_id, page_num, dpi, base_image)

                    # Apply filters
                    filtered_image = ImageFilters.apply_all_adjustments(
                        base_image,
                        **filters.dict()
                    )

                    # Convert to base64 for WebSocket transmission
                    img_bytes = io.BytesIO()
                    filtered_image.save(img_bytes, format='WEBP', quality=80, method=6)
                    img_bytes.seek(0)

                    # Send response
                    await websocket.send_json({
                        "type": "filter_complete",
                        "page": page_num,
                        "data": {
                            "image_url": f"data:image/webp;base64,{img_bytes.getvalue().hex()}"
                        }
                    })
                else:
                    await websocket.send_json({
                        "type": "error",
                        "error": "PDF not found"
                    })

    except WebSocketDisconnect:
        del active_connections[client_id]
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "error": str(e)
        })
        del active_connections[client_id]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)