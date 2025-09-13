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
    def images_to_pdf(images: List[Image.Image], output_path: Optional[Path] = None) -> bytes:
        """Convert a list of PIL Images to a PDF.

        Args:
            images: List of PIL Images
            output_path: Optional path to save the PDF

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
            # Convert RGBA to RGB if necessary
            if img.mode == 'RGBA':
                rgb_img = Image.new('RGB', img.size, (255, 255, 255))
                rgb_img.paste(img, mask=img.split()[3])
                img = rgb_img
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)

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

            # Create page with calculated size
            page = doc.new_page(width=page_width, height=page_height)

            # Insert image
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