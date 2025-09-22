"""Pydantic models for API request/response validation."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class FilterSettings(BaseModel):
    """Image filter settings."""
    brightness: float = Field(default=0.0, ge=-100, le=100)
    contrast: float = Field(default=0.0, ge=-100, le=100)
    highlights: float = Field(default=0.0, ge=-100, le=100)
    midtones: float = Field(default=0.0, ge=-100, le=100)
    shadows: float = Field(default=0.0, ge=-100, le=100)
    exposure: float = Field(default=0.0, ge=-3, le=3)
    saturation: float = Field(default=0.0, ge=-100, le=100)
    vibrance: float = Field(default=0.0, ge=-100, le=100)
    sharpness: float = Field(default=0.0, ge=-100, le=100)
    black_point: int = Field(default=0, ge=0, le=255)
    white_point: int = Field(default=255, ge=0, le=255)
    gamma: float = Field(default=1.0, ge=0.1, le=3.0)


class PageRenderRequest(BaseModel):
    """Request for rendering a PDF page."""
    dpi: int = Field(default=150, ge=30, le=600)  # Allow low DPI for efficient previews
    format: str = Field(default="webp", pattern="^(webp|jpeg|png)$")
    quality: int = Field(default=85, ge=1, le=100)


class PageFilterRequest(BaseModel):
    """Request for applying filters to a page."""
    filters: FilterSettings
    dpi: int = Field(default=150, ge=30, le=600)  # Allow low DPI for efficient previews
    format: str = Field(default="webp", pattern="^(webp|jpeg|png)$")
    quality: int = Field(default=85, ge=1, le=100)


class PDFInfo(BaseModel):
    """PDF document information."""
    pdf_id: str
    filename: str
    page_count: int
    page_dimensions: List[Dict[str, float]]  # [{width, height, width_inches, height_inches}]


class ExportRequest(BaseModel):
    """Request for exporting processed PDF."""
    dpi: int = Field(default=300, ge=72, le=600)
    page_filters: Dict[int, FilterSettings] = Field(default_factory=dict)
    image_format: str = Field(default="jpeg", pattern="^(jpeg|png)$")
    jpeg_quality: int = Field(default=95, ge=1, le=100)

    # Optional page size override
    target_page_size: Optional[List[float]] = None  # [width, height] in inches
    pad_to_exact_size: bool = False
    first_odd_page: int = Field(default=1, ge=1)

    # 2-up layout options
    two_up_enabled: bool = False
    layout_mode: str = Field(default="sequential", pattern="^(sequential|cut_and_stack)$")
    vertical_align: str = Field(default="top", pattern="^(top|center)$")
    start_page: int = Field(default=1, ge=1)

    # Page numbering
    add_page_numbers: bool = False
    page_number_format: str = Field(default="Page {n}")
    page_number_size: int = Field(default=11, ge=8, le=24)
    page_number_margin: int = Field(default=30, ge=10, le=100)


class CacheStats(BaseModel):
    """Cache statistics."""
    hits: int
    misses: int
    evictions: int
    pdf_count: int
    rendered_pages: int
    filtered_images: int


class WebSocketMessage(BaseModel):
    """WebSocket message for real-time updates."""
    type: str  # 'filter_update', 'render_complete', 'error'
    page: Optional[int] = None
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None