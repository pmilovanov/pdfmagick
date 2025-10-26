"""Tests for 2-up layout functionality"""
import pytest
from PIL import Image
from core.image_filters import ImageFilters
from core.pdf_processor import PDFProcessor


class Test2upHelperFunctions:
    """Test the core 2-up helper functions"""

    def test_arrange_pages_cut_and_stack_basic(self):
        """Test basic cut-and-stack arrangement for 8 pages"""
        arrangement = ImageFilters.arrange_pages_cut_and_stack(8)
        expected = [1, 5, 6, 2, 3, 7, 8, 4]
        assert arrangement == expected, f"Expected {expected}, got {arrangement}"

    def test_arrange_pages_cut_and_stack_odd_pages(self):
        """Test cut-and-stack with odd number of pages"""
        arrangement = ImageFilters.arrange_pages_cut_and_stack(5)

        # Should have 2 sheets (8 positions) with 3 blanks
        assert len(arrangement) == 8, f"Expected 8 positions for 5 pages, got {len(arrangement)}"
        assert arrangement.count(None) == 3, f"Expected 3 blanks, got {arrangement.count(None)}"

        # Verify non-None values are valid page numbers
        non_none = [x for x in arrangement if x is not None]
        assert sorted(non_none) == [1, 2, 3, 4, 5], f"Invalid page numbers: {non_none}"

    def test_arrange_pages_cut_and_stack_multiples_of_four(self):
        """Test cut-and-stack with exact multiples of 4"""
        arrangement = ImageFilters.arrange_pages_cut_and_stack(12)

        # Should have 3 sheets (12 positions) with no blanks
        assert len(arrangement) == 12, f"Expected 12 positions, got {len(arrangement)}"
        assert None not in arrangement, "Should have no blanks for 12 pages"

    def test_create_2up_page_both_images(self, create_test_page):
        """Test creating 2-up page with both left and right images"""
        left = create_test_page(1)
        right = create_test_page(2)

        composite = ImageFilters.create_2up_page(
            left, right,
            target_width=11.0,  # Letter landscape
            target_height=8.5,
            dpi=72,
            vertical_align="top"
        )

        expected_width = int(11.0 * 72)
        expected_height = int(8.5 * 72)

        assert composite.size == (expected_width, expected_height), \
            f"Expected size {expected_width}x{expected_height}, got {composite.size}"

    def test_create_2up_page_one_image(self, create_test_page):
        """Test creating 2-up page with only left image (odd last page)"""
        left = create_test_page(1)

        composite = ImageFilters.create_2up_page(
            left, None,
            target_width=11.0,
            target_height=8.5,
            dpi=72,
            vertical_align="top"
        )

        expected_width = int(11.0 * 72)
        expected_height = int(8.5 * 72)

        assert composite.size == (expected_width, expected_height)

    def test_create_2up_page_center_alignment(self, create_test_page):
        """Test creating 2-up page with center vertical alignment"""
        left = create_test_page(1)
        right = create_test_page(2)

        composite = ImageFilters.create_2up_page(
            left, right,
            target_width=11.0,
            target_height=8.5,
            dpi=72,
            vertical_align="center"
        )

        # Should produce valid image with correct dimensions
        assert composite.size == (792, 612)

    def test_create_2up_page_blank_both(self):
        """Test creating 2-up page with both images None"""
        composite = ImageFilters.create_2up_page(
            None, None,
            target_width=11.0,
            target_height=8.5,
            dpi=72,
            vertical_align="top"
        )

        # Should create blank white sheet
        assert composite.size == (792, 612)


class Test2upIntegration:
    """Integration tests for 2-up functionality with PDF generation"""

    def test_sequential_2up_even_pages(self, create_test_pdf):
        """Test sequential 2-up with even number of pages"""
        # Create test PDF with 4 pages
        pdf_bytes = create_test_pdf(4)
        pdf_proc = PDFProcessor(pdf_bytes=pdf_bytes)

        # Get all pages as images
        images = [pdf_proc.get_page_as_image(i, dpi=72) for i in range(4)]

        # Create 2-up sheets sequentially
        sheets = []
        for i in range(0, len(images), 2):
            left = images[i]
            right = images[i+1] if i+1 < len(images) else None
            sheet = ImageFilters.create_2up_page(left, right, 11.0, 8.5, 72, "top")
            sheets.append(sheet)

        # Should produce 2 sheets from 4 pages
        assert len(sheets) == 2

        # Generate PDF from sheets
        result_pdf = PDFProcessor.images_to_pdf(
            sheets,
            target_page_size=(11.0 * 72, 8.5 * 72)
        )

        # Verify result
        result_proc = PDFProcessor(pdf_bytes=result_pdf)
        assert result_proc.page_count == 2
        pdf_proc.close()
        result_proc.close()

    def test_sequential_2up_odd_pages(self, create_test_pdf):
        """Test sequential 2-up with odd number of pages"""
        pdf_bytes = create_test_pdf(5)
        pdf_proc = PDFProcessor(pdf_bytes=pdf_bytes)

        images = [pdf_proc.get_page_as_image(i, dpi=72) for i in range(5)]

        sheets = []
        for i in range(0, len(images), 2):
            left = images[i]
            right = images[i+1] if i+1 < len(images) else None
            sheet = ImageFilters.create_2up_page(left, right, 11.0, 8.5, 72, "top")
            sheets.append(sheet)

        # Should produce 3 sheets from 5 pages (last sheet has blank right side)
        assert len(sheets) == 3

        result_pdf = PDFProcessor.images_to_pdf(
            sheets,
            target_page_size=(11.0 * 72, 8.5 * 72)
        )

        result_proc = PDFProcessor(pdf_bytes=result_pdf)
        assert result_proc.page_count == 3
        pdf_proc.close()
        result_proc.close()

    def test_cut_and_stack_layout(self, create_test_pdf):
        """Test cut-and-stack layout for booklet printing"""
        pdf_bytes = create_test_pdf(4)
        pdf_proc = PDFProcessor(pdf_bytes=pdf_bytes)

        images = [pdf_proc.get_page_as_image(i, dpi=72) for i in range(4)]

        # Get arrangement
        arrangement = ImageFilters.arrange_pages_cut_and_stack(len(images))

        # Create sheets
        sheets = []
        for i in range(0, len(arrangement), 4):
            # Front side
            front_left_idx = arrangement[i] - 1 if arrangement[i] else None
            front_right_idx = arrangement[i+1] - 1 if arrangement[i+1] else None

            front = ImageFilters.create_2up_page(
                images[front_left_idx] if front_left_idx is not None else None,
                images[front_right_idx] if front_right_idx is not None else None,
                11.0, 8.5, 72, "top"
            )
            sheets.append(front)

            # Back side
            back_left_idx = arrangement[i+2] - 1 if arrangement[i+2] else None
            back_right_idx = arrangement[i+3] - 1 if arrangement[i+3] else None

            back = ImageFilters.create_2up_page(
                images[back_left_idx] if back_left_idx is not None else None,
                images[back_right_idx] if back_right_idx is not None else None,
                11.0, 8.5, 72, "top"
            )
            sheets.append(back)

        # Should produce 2 sheets (front and back of 1 physical sheet) for 4 pages
        assert len(sheets) == 2

        result_pdf = PDFProcessor.images_to_pdf(
            sheets,
            target_page_size=(11.0 * 72, 8.5 * 72)
        )

        result_proc = PDFProcessor(pdf_bytes=result_pdf)
        assert result_proc.page_count == 2
        pdf_proc.close()
        result_proc.close()


class Test2upPageSizes:
    """Test 2-up with different page sizes"""

    @pytest.mark.parametrize("size_name,width,height", [
        ("Letter", 8.5, 11.0),
        ("A4", 8.27, 11.69),
        ("Legal", 8.5, 14.0),
    ])
    def test_different_page_sizes(self, create_test_page, size_name, width, height):
        """Test 2-up creation with various standard page sizes"""
        left = create_test_page(1)
        right = create_test_page(2)

        # For 2-up, we swap width/height to get landscape
        composite = ImageFilters.create_2up_page(
            left, right,
            target_width=height,  # Swap for landscape
            target_height=width,
            dpi=72,
            vertical_align="top"
        )

        expected_width = int(height * 72)
        expected_height = int(width * 72)

        assert composite.size == (expected_width, expected_height), \
            f"{size_name}: Expected {expected_width}x{expected_height}, got {composite.size}"
