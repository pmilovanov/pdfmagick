"""Shared pytest fixtures for PDFMagick tests"""
import pytest
from PIL import Image, ImageDraw, ImageFont
from core.pdf_processor import PDFProcessor
from typing import List


@pytest.fixture
def create_test_page():
    """Factory fixture to create test pages with page numbers"""
    def _create_page(page_num: int, width: int = 612, height: int = 792, color: str = 'white') -> Image.Image:
        """Create a test page with a number on it

        Args:
            page_num: Page number to display
            width: Image width in pixels
            height: Image height in pixels
            color: Background color

        Returns:
            PIL Image with page number and border
        """
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)

        # Draw page number in center
        text = f"Page {page_num}"
        font = ImageFont.load_default()
        bbox = draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        x = (width - text_width) // 2
        y = (height - text_height) // 2

        draw.text((x, y), text, fill='black', font=font)

        # Draw border
        draw.rectangle([10, 10, width-10, height-10], outline='black', width=2)

        return img

    return _create_page


@pytest.fixture
def create_test_pdf(create_test_page):
    """Factory fixture to create test PDFs"""
    def _create_pdf(num_pages: int = 4) -> bytes:
        """Create a simple test PDF

        Args:
            num_pages: Number of pages to create

        Returns:
            PDF as bytes
        """
        images = [create_test_page(i) for i in range(1, num_pages + 1)]
        return PDFProcessor.images_to_pdf(images)

    return _create_pdf
