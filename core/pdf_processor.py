"""PDF processing utilities for converting PDF to images and back."""

import io
from pathlib import Path
from typing import List, Optional, Tuple
import fitz  # PyMuPDF
from PIL import Image
import numpy as np


class PDFProcessor:
    """Handles PDF to image conversion and reassembly."""

    def __init__(self, pdf_path: Optional[Path] = None, pdf_bytes: Optional[bytes] = None):
        """Initialize with either a file path or bytes."""
        if pdf_path:
            self.doc = fitz.open(pdf_path)
        elif pdf_bytes:
            self.doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        else:
            raise ValueError("Either pdf_path or pdf_bytes must be provided")

        self.page_count = len(self.doc)
        self._page_images_cache = {}

    def get_page_as_image(self, page_num: int, dpi: int = 150) -> Image.Image:
        """Convert a PDF page to PIL Image.

        Args:
            page_num: Page number (0-indexed)
            dpi: Resolution for rasterization

        Returns:
            PIL Image of the page
        """
        cache_key = (page_num, dpi)
        if cache_key in self._page_images_cache:
            return self._page_images_cache[cache_key]

        if page_num < 0 or page_num >= self.page_count:
            raise ValueError(f"Page number {page_num} out of range (0-{self.page_count-1})")

        page = self.doc[page_num]

        # Get page dimensions and calculate expected pixel size
        rect = page.rect
        width_inches = rect.width / 72.0
        height_inches = rect.height / 72.0
        expected_width = int(width_inches * dpi)
        expected_height = int(height_inches * dpi)
        expected_pixels = expected_width * expected_height

        # Warn if the image will be very large
        if expected_pixels > 50_000_000:  # 50 megapixels
            print(f"Warning: Page {page_num} at {dpi} DPI will be {expected_width}x{expected_height} "
                  f"({expected_pixels/1_000_000:.1f} megapixels). "
                  f"Original page size: {width_inches:.1f}x{height_inches:.1f} inches")

        mat = fitz.Matrix(dpi/72.0, dpi/72.0)
        pix = page.get_pixmap(matrix=mat)

        # Convert to PIL Image
        img_data = pix.tobytes("png")
        img = Image.open(io.BytesIO(img_data))

        # Cache the image
        self._page_images_cache[cache_key] = img

        return img

    def get_all_pages_as_images(self, dpi: int = 150) -> List[Image.Image]:
        """Convert all PDF pages to PIL Images.

        Args:
            dpi: Resolution for rasterization

        Returns:
            List of PIL Images
        """
        return [self.get_page_as_image(i, dpi) for i in range(self.page_count)]

    def get_page_dimensions(self, page_num: int) -> Tuple[float, float]:
        """Get the dimensions of a page in points (72 points = 1 inch).

        Args:
            page_num: Page number (0-indexed)

        Returns:
            Tuple of (width, height) in points
        """
        page = self.doc[page_num]
        rect = page.rect
        return rect.width, rect.height

    @staticmethod
    def images_to_pdf(images: List[Image.Image], output_path: Optional[Path] = None,
                     target_page_size: Optional[Tuple[float, float]] = None,
                     image_format: str = "JPEG", jpeg_quality: int = 95) -> bytes:
        """Convert a list of PIL Images to a PDF.

        Args:
            images: List of PIL Images
            output_path: Optional path to save the PDF
            target_page_size: Optional tuple of (width, height) in points for exact page size
            image_format: Image format for embedding ("JPEG" or "PNG")
            jpeg_quality: JPEG quality (1-100) if using JPEG format

        Returns:
            PDF as bytes
        """
        if not images:
            raise ValueError("No images provided")

        # Create new PDF
        doc = fitz.open()

        for img in images:
            # Convert PIL Image to bytes
            img_bytes = io.BytesIO()

            # Ensure image is in RGB mode (required for JPEG)
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Save with specified format and compression
            if image_format == "JPEG":
                img.save(img_bytes, format='JPEG', quality=jpeg_quality, optimize=True)
            else:
                img.save(img_bytes, format='PNG')

            img_bytes.seek(0)

            # Use target page size if provided, otherwise calculate from image
            if target_page_size:
                page_width, page_height = target_page_size
            else:
                # Calculate page size to match image aspect ratio
                # Using standard US Letter as base (612x792 points)
                img_width, img_height = img.size
                aspect = img_width / img_height

                if aspect > 612/792:
                    # Image is wider than page
                    page_width = 612
                    page_height = 612 / aspect
                else:
                    # Image is taller than page
                    page_height = 792
                    page_width = 792 * aspect

            # Create page with calculated or target size
            page = doc.new_page(width=page_width, height=page_height)

            # Insert image at top-left if using target size, otherwise fill page
            if target_page_size:
                # Calculate image rect to maintain aspect ratio and position at top
                img_width, img_height = img.size
                img_aspect = img_width / img_height
                page_aspect = page_width / page_height

                if img_aspect > page_aspect:
                    # Image is wider relative to page
                    rect_width = page_width
                    rect_height = page_width / img_aspect
                else:
                    # Image is taller relative to page
                    rect_height = page_height
                    rect_width = page_height * img_aspect

                # Position at top-left
                rect = fitz.Rect(0, 0, rect_width, rect_height)
            else:
                # Fill entire page
                rect = page.rect

            page.insert_image(rect, stream=img_bytes.read())

        # Save to bytes
        pdf_bytes = doc.tobytes()

        if output_path:
            doc.save(output_path)

        doc.close()

        return pdf_bytes

    def clear_cache(self):
        """Clear the image cache."""
        self._page_images_cache.clear()

    def close(self):
        """Close the PDF document."""
        self.doc.close()
        self.clear_cache()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()