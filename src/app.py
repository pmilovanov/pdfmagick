"""Streamlit application for PDF image processing with real-time preview."""

import streamlit as st
from pathlib import Path
import tempfile
from typing import Dict, Any, Optional, Tuple, List
import io
import math
import numpy as np
import cv2
from PIL import Image, ImageDraw, ImageFont

from pdf_processor import PDFProcessor
from image_filters import ImageFilters


def init_session_state():
    """Initialize session state variables."""
    if 'pdf_processor' not in st.session_state:
        st.session_state.pdf_processor = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 0
    if 'filter_settings' not in st.session_state:
        st.session_state.filter_settings = {}
    if 'page_filters' not in st.session_state:
        st.session_state.page_filters = {}
    if 'processed_images' not in st.session_state:
        st.session_state.processed_images = {}


def get_default_filter_settings() -> Dict[str, Any]:
    """Get default filter settings."""
    return {
        'brightness': 0.0,
        'contrast': 0.0,
        'highlights': 0.0,
        'midtones': 0.0,
        'shadows': 0.0,
        'exposure': 0.0,
        'saturation': 0.0,
        'vibrance': 0.0,
        'sharpness': 0.0,
        'black_point': 0,
        'white_point': 255,
        'gamma': 1.0
    }


def get_page_sizes() -> Dict[str, Tuple[float, float]]:
    """Get standard page sizes in inches (width, height)."""
    return {
        "Auto (use PDF dimensions)": None,
        "Letter (8.5 × 11 in)": (8.5, 11.0),
        "Letter Landscape (11 × 8.5 in)": (11.0, 8.5),
        "A4 (8.27 × 11.69 in)": (8.27, 11.69),
        "A4 Landscape (11.69 × 8.27 in)": (11.69, 8.27),
        "Legal (8.5 × 14 in)": (8.5, 14.0),
        "Tabloid (11 × 17 in)": (11.0, 17.0),
        "A3 (11.69 × 16.54 in)": (11.69, 16.54),
    }


def calculate_scale_factor(actual_width: float, actual_height: float,
                          target_width: float, target_height: float) -> float:
    """Calculate scale factor to fit image within target dimensions while maintaining aspect ratio."""
    scale_x = target_width / actual_width
    scale_y = target_height / actual_height
    return min(scale_x, scale_y)


def add_padding_for_exact_size(image: Image.Image, target_width: int, target_height: int, page_num: int) -> Image.Image:
    """Add padding to reach exact target dimensions with alternating horizontal alignment for double-sided printing.

    Args:
        image: Input PIL Image
        target_width: Target width in pixels
        target_height: Target height in pixels
        page_num: Page number (1-indexed) to determine odd/even alignment

    Returns:
        Padded image with proper alignment for double-sided printing
    """
    # Determine if padding is needed
    needs_width_padding = image.width < target_width
    needs_height_padding = image.height < target_height

    # If no padding needed, return original
    if not needs_width_padding and not needs_height_padding:
        return image

    # Use the larger of the two dimensions to avoid clipping
    final_width = max(image.width, target_width)
    final_height = max(image.height, target_height)

    # Create new image with white background
    padded = Image.new('RGB', (final_width, final_height), (255, 255, 255))

    # Calculate position for pasting
    if needs_width_padding:
        # Odd pages (1, 3, 5...): align left (pad right)
        # Even pages (2, 4, 6...): align right (pad left)
        if page_num % 2 == 1:  # Odd page - align left
            x_offset = 0
        else:  # Even page - align right
            x_offset = final_width - image.width
    else:
        # Center horizontally if no width padding needed
        x_offset = (final_width - image.width) // 2

    # Always align to top for height
    y_offset = 0

    # Paste original image at calculated position
    padded.paste(image, (x_offset, y_offset))

    return padded


def arrange_pages_cut_and_stack(n: int) -> List[Optional[int]]:
    """Arrange pages for cut-and-stack double-sided printing.

    Args:
        n: Total number of pages

    Returns:
        Flat array where every 4 elements represent one sheet:
        [front_left, front_right, back_left, back_right, ...]
        Page numbers are 1-indexed, None represents blank pages
    """
    sheets_count = math.ceil(n / 4)
    output = []

    for i in range(sheets_count):
        # Calculate page numbers for each position
        front_left = 2 * i + 1
        front_right = 2 * sheets_count + 2 * i + 1
        back_left = 2 * sheets_count + 2 * i + 2
        back_right = 2 * i + 2

        # Append positions, using None for out-of-range pages
        output.append(front_left if front_left <= n else None)
        output.append(front_right if front_right <= n else None)
        output.append(back_left if back_left <= n else None)
        output.append(back_right if back_right <= n else None)

    return output


def create_2up_page(left_img: Optional[Image.Image],
                   right_img: Optional[Image.Image],
                   target_width: float,
                   target_height: float,
                   dpi: int,
                   vertical_align: str = "top") -> Image.Image:
    """Create a landscape sheet with two pages side-by-side.

    Args:
        left_img: Image for left side (or None for blank)
        right_img: Image for right side (or None for blank)
        target_width: Target width in inches (for landscape, this is the longer dimension)
        target_height: Target height in inches (for landscape, this is the shorter dimension)
        dpi: DPI for output
        vertical_align: Vertical alignment ("top" or "center")

    Returns:
        Composite image with both pages side-by-side, vertically aligned as specified
    """
    # Create blank landscape canvas
    sheet_width_px = int(target_width * dpi)
    sheet_height_px = int(target_height * dpi)
    sheet = Image.new('RGB', (sheet_width_px, sheet_height_px), (255, 255, 255))

    # Calculate half-page dimensions
    half_width = sheet_width_px // 2

    # Place left page if exists
    if left_img:
        # Scale to fit in left half, maintaining aspect ratio
        scale = min(half_width / left_img.width, sheet_height_px / left_img.height)
        new_width = int(left_img.width * scale)
        new_height = int(left_img.height * scale)
        resized = left_img.resize((new_width, new_height), Image.LANCZOS)

        # Calculate vertical position based on alignment
        if vertical_align == "center":
            y_offset = (sheet_height_px - new_height) // 2
        else:  # top
            y_offset = 0

        # Center horizontally within the left half
        x_offset = (half_width - new_width) // 2
        sheet.paste(resized, (x_offset, y_offset))

    # Place right page if exists
    if right_img:
        # Scale to fit in right half
        scale = min(half_width / right_img.width, sheet_height_px / right_img.height)
        new_width = int(right_img.width * scale)
        new_height = int(right_img.height * scale)
        resized = right_img.resize((new_width, new_height), Image.LANCZOS)

        # Calculate vertical position based on alignment
        if vertical_align == "center":
            y_offset = (sheet_height_px - new_height) // 2
        else:  # top
            y_offset = 0

        # Center horizontally within the right half
        x_offset = half_width + (half_width - new_width) // 2
        sheet.paste(resized, (x_offset, y_offset))

    return sheet


def add_page_number(image: Image.Image, page_num: int, total_pages: int,
                   format_style: str = "Page {n}", font_size: int = 14,
                   margin: int = 30) -> Image.Image:
    """Add page number to bottom-right corner of image.

    Args:
        image: Input PIL Image
        page_num: Current page number (0-indexed)
        total_pages: Total number of pages
        format_style: Format string for page number
        font_size: Font size in points
        margin: Margin from edges in pixels

    Returns:
        Image with page number added
    """
    # Create a copy to avoid modifying original
    img_with_number = image.copy()
    draw = ImageDraw.Draw(img_with_number)

    # Format the page number text
    if format_style == "Page {n}":
        text = f"Page {page_num + 1}"
    elif format_style == "{n}":
        text = str(page_num + 1)
    elif format_style == "{n} of {total}":
        text = f"{page_num + 1} of {total_pages}"
    else:
        text = str(page_num + 1)

    # Try to use a nice font, fall back to default if not available
    try:
        # Try common system fonts
        font_options = [
            "Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
        ]
        font = None
        for font_path in font_options:
            try:
                font = ImageFont.truetype(font_path, font_size)
                break
            except:
                continue

        if font is None:
            # If no system fonts found, use default
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()

    # Calculate text position (bottom-right with margin)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = image.width - text_width - margin
    y = image.height - text_height - margin

    # Draw text with slight shadow for readability
    shadow_offset = 1
    draw.text((x + shadow_offset, y + shadow_offset), text, fill=(200, 200, 200), font=font)  # Shadow
    draw.text((x, y), text, fill=(50, 50, 50), font=font)  # Main text

    return img_with_number


def apply_filters_to_image(image, settings):
    """Apply filter settings to an image."""
    return ImageFilters.apply_all_adjustments(
        image,
        brightness=settings.get('brightness', 0.0),
        contrast=settings.get('contrast', 0.0),
        highlights=settings.get('highlights', 0.0),
        midtones=settings.get('midtones', 0.0),
        shadows=settings.get('shadows', 0.0),
        exposure=settings.get('exposure', 0.0),
        saturation=settings.get('saturation', 0.0),
        vibrance=settings.get('vibrance', 0.0),
        sharpness=settings.get('sharpness', 0.0),
        black_point=settings.get('black_point', 0),
        white_point=settings.get('white_point', 255),
        gamma=settings.get('gamma', 1.0)
    )


def create_slider_with_input(label, key_prefix, min_val, max_val, default_val, step, page_num, settings_dict):
    """Create a slider with an accompanying number input for precise control."""
    col1, col2 = st.columns([3, 1])

    with col2:
        num_val = st.number_input(
            label,
            min_value=float(min_val),
            max_value=float(max_val),
            value=float(settings_dict.get(key_prefix, default_val)),
            step=float(step),
            key=f"{key_prefix}_num_{page_num}",
            label_visibility="collapsed"
        )

    with col1:
        slider_val = st.slider(
            label,
            min_value=float(min_val),
            max_value=float(max_val),
            value=num_val,  # Use number input value
            step=float(step),
            key=f"{key_prefix}_slider_{page_num}",
            label_visibility="visible"
        )

    # Return the slider value (which is synced with number input)
    return slider_val


def main():
    st.set_page_config(
        page_title="PDFMagick - PDF Image Processor",
        page_icon="🎨",
        layout="wide"
    )

    init_session_state()

    st.title("🎨 PDFMagick - PDF Image Processor")
    st.markdown("Upload a PDF, adjust image filters with real-time preview, and export the enhanced PDF.")

    # Sidebar for file upload and page navigation
    with st.sidebar:
        st.header("📄 PDF Upload")

        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf")

        if uploaded_file is not None:
            # Load PDF if new file uploaded
            if st.session_state.pdf_processor is None or \
               getattr(st.session_state, 'current_file_name', None) != uploaded_file.name:
                pdf_bytes = uploaded_file.read()
                st.session_state.pdf_processor = PDFProcessor(pdf_bytes=pdf_bytes)
                st.session_state.current_file_name = uploaded_file.name
                st.session_state.current_page = 0
                st.session_state.page_filters = {}
                st.session_state.processed_images = {}

            pdf_proc = st.session_state.pdf_processor

            st.success(f"PDF loaded: {pdf_proc.page_count} pages")

            # Page Size Override
            st.header("📐 Page Size Override")

            # Get first page dimensions to show as example
            first_page_width, first_page_height = pdf_proc.get_page_dimensions(0)
            detected_width_in = first_page_width / 72
            detected_height_in = first_page_height / 72

            # Check if dimensions seem suspicious (> 15 inches)
            if detected_width_in > 15 or detected_height_in > 15:
                st.warning(f"⚠️ Detected unusual page size: {detected_width_in:.1f} × {detected_height_in:.1f} inches")

            page_sizes = get_page_sizes()
            selected_size = st.selectbox(
                "Page Size",
                options=list(page_sizes.keys()),
                index=0,
                help="Override detected page dimensions if they seem incorrect"
            )

            # Store the selected page size in session state
            st.session_state.page_size_override = page_sizes[selected_size]

            # Show scaling information if override is selected
            if st.session_state.page_size_override:
                target_w, target_h = st.session_state.page_size_override
                scale_factor = calculate_scale_factor(
                    detected_width_in, detected_height_in,
                    target_w, target_h
                )
                scaled_width = detected_width_in * scale_factor
                scaled_height = detected_height_in * scale_factor

                st.info(f"📊 Scaling: {detected_width_in:.1f}×{detected_height_in:.1f}\" → "
                       f"{scaled_width:.1f}×{scaled_height:.1f}\" (factor: {scale_factor:.2f})")

                # Show effective resolution
                for dpi_setting in [150, 300]:
                    effective_dpi = int(dpi_setting * scale_factor)
                    st.text(f"• {dpi_setting} DPI setting → {effective_dpi} DPI effective")

            # Debug: Show page dimensions
            if st.checkbox("Show PDF Details", value=False):
                for i in range(min(3, pdf_proc.page_count)):  # Show first 3 pages
                    width, height = pdf_proc.get_page_dimensions(i)
                    width_in = width / 72
                    height_in = height / 72
                    st.text(f"Page {i+1}: {width:.0f}x{height:.0f} pts ({width_in:.1f}x{height_in:.1f} inches)")

                    # Apply scale factor if override is selected
                    if st.session_state.page_size_override:
                        target_w, target_h = st.session_state.page_size_override
                        scale = calculate_scale_factor(width_in, height_in, target_w, target_h)
                        st.text(f"  Scale factor: {scale:.3f}")
                        for dpi in [150, 200, 300, 400]:
                            effective_dpi = int(dpi * scale)
                            px_w = int(width_in * effective_dpi)
                            px_h = int(height_in * effective_dpi)
                            megapixels = (px_w * px_h) / 1_000_000
                            st.text(f"  At {dpi} DPI: {px_w}x{px_h} px ({megapixels:.1f} MP) [eff: {effective_dpi} DPI]")
                    else:
                        for dpi in [150, 200, 300, 400]:
                            px_w = int(width_in * dpi)
                            px_h = int(height_in * dpi)
                            megapixels = (px_w * px_h) / 1_000_000
                            st.text(f"  At {dpi} DPI: {px_w}x{px_h} px ({megapixels:.1f} MP)")

            # Page navigation
            st.header("📖 Page Navigation")
            col1, col2 = st.columns(2)

            with col1:
                if st.button("◀ Previous", disabled=st.session_state.current_page == 0):
                    st.session_state.current_page -= 1

            with col2:
                if st.button("Next ▶", disabled=st.session_state.current_page >= pdf_proc.page_count - 1):
                    st.session_state.current_page += 1

            st.session_state.current_page = st.select_slider(
                "Select Page",
                options=list(range(pdf_proc.page_count)),
                value=st.session_state.current_page,
                format_func=lambda x: f"Page {x + 1}"
            )

            # Batch operations
            st.header("🎯 Batch Operations")

            if st.button("📋 Copy Settings to All Pages"):
                current_settings = st.session_state.filter_settings.copy()
                for i in range(pdf_proc.page_count):
                    st.session_state.page_filters[i] = current_settings.copy()
                st.success("Settings copied to all pages!")

            if st.button("✨ Auto Enhance All Pages"):
                with st.spinner("Auto-enhancing all pages..."):
                    for page_num in range(pdf_proc.page_count):
                        # Calculate effective DPI with page size override
                        display_dpi = 150
                        if hasattr(st.session_state, 'page_size_override') and st.session_state.page_size_override:
                            page_width, page_height = pdf_proc.get_page_dimensions(page_num)
                            width_in = page_width / 72
                            height_in = page_height / 72
                            target_w, target_h = st.session_state.page_size_override
                            scale_factor = calculate_scale_factor(width_in, height_in, target_w, target_h)
                            display_dpi = int(display_dpi * scale_factor)

                        # Get the image for this page
                        img = pdf_proc.get_page_as_image(page_num, dpi=display_dpi)
                        img_array = np.array(img)

                        # Calculate grayscale for analysis
                        if len(img_array.shape) == 3:
                            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                        else:
                            gray = img_array

                        # Find optimal settings for this specific page (less aggressive)
                        black_point = int(np.percentile(gray, 5))
                        white_point = int(np.percentile(gray, 95))

                        # Create settings for this page
                        page_settings = get_default_filter_settings()

                        # Only apply if there's meaningful room for improvement
                        if black_point > 20 or white_point < 235:
                            # Moderate the adjustment
                            page_settings['black_point'] = min(black_point, 50)
                            page_settings['white_point'] = max(white_point, 205)
                            page_settings['contrast'] = 5.0
                        else:
                            # Already well-distributed, subtle enhancement only
                            page_settings['contrast'] = 3.0
                            page_settings['brightness'] = 2.0

                        # Save settings for this page
                        st.session_state.page_filters[page_num] = page_settings

                    # Update current page settings if it's the currently selected page
                    if st.session_state.current_page in st.session_state.page_filters:
                        st.session_state.filter_settings = st.session_state.page_filters[st.session_state.current_page].copy()

                st.success(f"Auto enhancement applied to all {pdf_proc.page_count} pages!")
                st.rerun()

            if st.button("🔄 Reset Current Page"):
                st.session_state.filter_settings = get_default_filter_settings()
                if st.session_state.current_page in st.session_state.page_filters:
                    del st.session_state.page_filters[st.session_state.current_page]
                if st.session_state.current_page in st.session_state.processed_images:
                    del st.session_state.processed_images[st.session_state.current_page]

            if st.button("🔄 Reset All Pages"):
                st.session_state.filter_settings = get_default_filter_settings()
                st.session_state.page_filters = {}
                st.session_state.processed_images = {}
                st.success("All pages reset!")

    # Main content area
    if st.session_state.pdf_processor is not None:
        pdf_proc = st.session_state.pdf_processor
        current_page = st.session_state.current_page

        # Load current page settings
        if current_page in st.session_state.page_filters:
            st.session_state.filter_settings = st.session_state.page_filters[current_page].copy()
        elif not st.session_state.filter_settings:
            st.session_state.filter_settings = get_default_filter_settings()

        # Create three columns: controls, original, processed
        col_controls, col_original, col_processed = st.columns([1.5, 2, 2])

        with col_controls:
            st.header("🎛️ Image Adjustments")

            # Auto enhance button
            if st.button("✨ Auto Enhance"):
                # Calculate effective DPI with page size override
                display_dpi = 150
                if hasattr(st.session_state, 'page_size_override') and st.session_state.page_size_override:
                    page_width, page_height = pdf_proc.get_page_dimensions(current_page)
                    width_in = page_width / 72
                    height_in = page_height / 72
                    target_w, target_h = st.session_state.page_size_override
                    scale_factor = calculate_scale_factor(width_in, height_in, target_w, target_h)
                    display_dpi = int(display_dpi * scale_factor)

                original_image = pdf_proc.get_page_as_image(current_page, dpi=display_dpi)

                # Calculate auto-enhance parameters
                img_array = np.array(original_image)
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array

                # Find optimal black and white points (less aggressive)
                black_point = int(np.percentile(gray, 5))
                white_point = int(np.percentile(gray, 95))

                # Only apply if there's meaningful room for improvement
                if black_point > 20 or white_point < 235:
                    # Moderate the adjustment to avoid overcorrection
                    black_point = min(black_point, 50)  # Don't push blacks too hard
                    white_point = max(white_point, 205)  # Keep some headroom in whites

                    # Update the filter settings
                    st.session_state.filter_settings['black_point'] = black_point
                    st.session_state.filter_settings['white_point'] = white_point
                    st.session_state.filter_settings['contrast'] = 5.0  # Gentler contrast boost
                else:
                    # Image is already well-distributed, just add subtle enhancement
                    st.session_state.filter_settings['contrast'] = 3.0
                    st.session_state.filter_settings['brightness'] = 2.0

                # Save to page filters
                st.session_state.page_filters[current_page] = st.session_state.filter_settings.copy()

                st.success("Auto enhancement applied!")
                st.rerun()  # Rerun to update sliders

            # Filter controls with expanders
            with st.expander("🔆 Basic Adjustments", expanded=True):
                st.session_state.filter_settings['brightness'] = create_slider_with_input(
                    "Brightness", "brightness", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['contrast'] = create_slider_with_input(
                    "Contrast", "contrast", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['exposure'] = create_slider_with_input(
                    "Exposure (EV)", "exposure", -3, 3, 0, 0.1,
                    current_page, st.session_state.filter_settings
                )

            with st.expander("💡 Tonal Adjustments"):
                st.session_state.filter_settings['highlights'] = create_slider_with_input(
                    "Highlights", "highlights", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['midtones'] = create_slider_with_input(
                    "Midtones", "midtones", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['shadows'] = create_slider_with_input(
                    "Shadows", "shadows", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

            with st.expander("🎨 Color Adjustments"):
                st.session_state.filter_settings['saturation'] = create_slider_with_input(
                    "Saturation", "saturation", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['vibrance'] = create_slider_with_input(
                    "Vibrance", "vibrance", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

            with st.expander("📊 Levels & Curves"):
                st.session_state.filter_settings['black_point'] = create_slider_with_input(
                    "Black Point", "black_point", 0, 255, 0, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['white_point'] = create_slider_with_input(
                    "White Point", "white_point", 0, 255, 255, 1,
                    current_page, st.session_state.filter_settings
                )

                st.session_state.filter_settings['gamma'] = create_slider_with_input(
                    "Gamma", "gamma", 0.1, 3.0, 1.0, 0.01,
                    current_page, st.session_state.filter_settings
                )

            with st.expander("🔍 Sharpness"):
                st.session_state.filter_settings['sharpness'] = create_slider_with_input(
                    "Sharpness", "sharpness", -100, 100, 0, 1,
                    current_page, st.session_state.filter_settings
                )

            # Save current page settings
            st.session_state.page_filters[current_page] = st.session_state.filter_settings.copy()

        # Display original image
        with col_original:
            st.header(f"📄 Original - Page {current_page + 1}")

            # Calculate effective DPI with page size override
            display_dpi = 150
            if hasattr(st.session_state, 'page_size_override') and st.session_state.page_size_override:
                page_width, page_height = pdf_proc.get_page_dimensions(current_page)
                width_in = page_width / 72
                height_in = page_height / 72
                target_w, target_h = st.session_state.page_size_override
                scale_factor = calculate_scale_factor(width_in, height_in, target_w, target_h)
                display_dpi = int(display_dpi * scale_factor)

            original_image = pdf_proc.get_page_as_image(current_page, dpi=display_dpi)
            st.image(original_image, use_container_width=True)

        # Display processed image
        with col_processed:
            st.header(f"✨ Processed - Page {current_page + 1}")

            # Apply filters
            processed_image = apply_filters_to_image(
                original_image,
                st.session_state.filter_settings
            )
            st.session_state.processed_images[current_page] = processed_image

            st.image(processed_image, use_container_width=True)

            # Status indicator for current page
            if current_page in st.session_state.page_filters:
                # Check if settings are non-default
                default_settings = get_default_filter_settings()
                if st.session_state.page_filters[current_page] != default_settings:
                    st.success("✅ Filters applied to this page")

        # Export section
        st.header("💾 Export Processed PDF")

        # Show padding option if page size override is active
        if hasattr(st.session_state, 'page_size_override') and st.session_state.page_size_override:
            pad_to_exact_size = st.checkbox(
                "📏 Pad to exact page size (for trimming)",
                value=True,  # Default to enabled when page size override is active
                help="Add padding to match exact target page size with alternating alignment for double-sided printing. "
                     "Odd pages align left (pad right), even pages align right (pad left). "
                     "This ensures proper registration when sheets are flipped along the vertical edge and trimmed."
            )

            # 2-up layout option (only available with page size override)
            two_up_enabled = st.checkbox(
                "📖 2-up layout (2 pages per sheet)",
                value=False,
                help="Arrange two pages side-by-side on landscape-oriented sheets"
            )

            if two_up_enabled:
                # Vertical alignment option
                vertical_align = st.selectbox(
                    "Vertical alignment",
                    options=["Top", "Center"],
                    index=0,  # Default to Top
                    help="How to vertically align pages on each half of the sheet"
                ).lower()

                layout_mode = st.radio(
                    "Layout mode",
                    options=["Sequential", "Cut & Stack"],
                    index=0,
                    help="Sequential: Pages in order (1,2 | 3,4...). Cut & Stack: Special imposition for booklet creation"
                )

                if layout_mode == "Cut & Stack":
                    # Starting page selector
                    start_page = st.number_input(
                        "Start from page",
                        min_value=1,
                        max_value=pdf_proc.page_count,
                        value=1,
                        step=1,
                        help="Pages before this will be excluded from the export"
                    )

                    # Show feedback about which pages will be exported
                    pages_to_export = pdf_proc.page_count - start_page + 1
                    if start_page > 1:
                        st.info(f"📄 Will export pages {start_page} to {pdf_proc.page_count} ({pages_to_export} pages)")

                    st.info(
                        "🔪 **Cut & Stack Instructions:**\n"
                        "1. Print double-sided\n"
                        "2. Cut each sheet vertically down the middle\n"
                        "3. Stack the halves to create a sequential booklet\n"
                        "4. Each half will have consecutive pages front/back"
                    )
                else:
                    start_page = 1
            else:
                layout_mode = "Sequential"
                start_page = 1
                vertical_align = "top"
        else:
            pad_to_exact_size = False
            two_up_enabled = False
            layout_mode = "Sequential"
            start_page = 1
            vertical_align = "top"

        # Page numbering options
        add_page_numbers = st.checkbox(
            "🔢 Add page numbers",
            value=False,
            help="Add page numbers to the bottom-right corner of each page"
        )

        if add_page_numbers:
            col_pn1, col_pn2, col_pn3 = st.columns(3)
            with col_pn1:
                page_number_format = st.selectbox(
                    "Format",
                    options=["Page {n}", "{n}", "{n} of {total}"],
                    index=0,
                    help="Choose how page numbers are displayed"
                )
            with col_pn2:
                page_number_size = st.selectbox(
                    "Font Size",
                    options=[10, 11, 12, 14, 16, 18],
                    index=1  # Default to 11
                )
            with col_pn3:
                page_number_margin = st.number_input(
                    "Margin (px)",
                    min_value=10,
                    max_value=100,
                    value=30,
                    step=5,
                    help="Distance from bottom-right corner"
                )
        else:
            page_number_format = "Page {n}"
            page_number_size = 11
            page_number_margin = 30

        # Compression settings
        col_comp1, col_comp2 = st.columns(2)
        with col_comp1:
            compression_format = st.selectbox(
                "Image Format",
                options=["JPEG (95% quality)", "JPEG (90% quality)", "JPEG (85% quality)", "PNG (lossless)"],
                index=0,
                help="JPEG provides much smaller file sizes with minimal quality loss. PNG preserves exact quality but creates larger files."
            )

        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 3])

        with col_exp1:
            export_dpi = st.selectbox(
                "Export Quality (DPI)",
                options=[150, 200, 300, 400],
                index=2  # Default to 300 DPI
            )

        with col_exp2:
            if st.button("🚀 Generate PDF", type="primary"):
                with st.spinner("Processing all pages and generating PDF..."):
                    # Determine which pages to process
                    if 'start_page' in locals() and start_page > 1:
                        page_range = range(start_page - 1, pdf_proc.page_count)  # Convert to 0-indexed
                    else:
                        page_range = range(pdf_proc.page_count)

                    # Process selected pages
                    processed_images = []
                    for page_num in page_range:
                        # Calculate effective DPI with page size override
                        effective_export_dpi = export_dpi
                        if hasattr(st.session_state, 'page_size_override') and st.session_state.page_size_override:
                            page_width, page_height = pdf_proc.get_page_dimensions(page_num)
                            width_in = page_width / 72
                            height_in = page_height / 72
                            target_w, target_h = st.session_state.page_size_override
                            scale_factor = calculate_scale_factor(width_in, height_in, target_w, target_h)
                            effective_export_dpi = int(export_dpi * scale_factor)

                        # Get original image at effective DPI
                        img = pdf_proc.get_page_as_image(page_num, dpi=effective_export_dpi)

                        # Apply filters if they exist for this page
                        if page_num in st.session_state.page_filters:
                            settings = st.session_state.page_filters[page_num]
                            img = apply_filters_to_image(img, settings)

                        # Add page number if enabled (before padding)
                        if add_page_numbers:
                            # Scale font size based on DPI (font points to pixels)
                            # Standard conversion: pixels = points * DPI / 72
                            scaled_font_size = int(page_number_size * effective_export_dpi / 72)
                            scaled_margin = int(page_number_margin * effective_export_dpi / 150)  # Scale margin relative to base DPI

                            # Calculate relative page number for exported pages
                            if 'start_page' in locals() and start_page > 1:
                                relative_page_num = page_num - (start_page - 1)
                                total_exported_pages = pdf_proc.page_count - (start_page - 1)
                            else:
                                relative_page_num = page_num
                                total_exported_pages = pdf_proc.page_count

                            img = add_page_number(
                                img,
                                relative_page_num,
                                total_exported_pages,
                                format_style=page_number_format,
                                font_size=scaled_font_size,
                                margin=scaled_margin
                            )

                        # Apply padding if enabled and page size override is active
                        if pad_to_exact_size and st.session_state.page_size_override:
                            target_w, target_h = st.session_state.page_size_override
                            target_width_pixels = int(target_w * export_dpi)
                            target_height_pixels = int(target_h * export_dpi)
                            # Use relative page number for odd/even determination
                            img = add_padding_for_exact_size(img, target_width_pixels, target_height_pixels, relative_page_num)

                        processed_images.append(img)

                    # Handle 2-up layout if enabled
                    if two_up_enabled and st.session_state.page_size_override:
                        target_w, target_h = st.session_state.page_size_override
                        # For landscape orientation, swap dimensions
                        landscape_w = target_h  # Height becomes width
                        landscape_h = target_w  # Width becomes height

                        composite_sheets = []

                        if layout_mode == "Cut & Stack":
                            # Get page arrangement for cut-and-stack
                            arrangement = arrange_pages_cut_and_stack(len(processed_images))

                            # Process every 4 pages (one sheet, front and back)
                            for i in range(0, len(arrangement), 4):
                                # Get page indices (convert from 1-indexed to 0-indexed)
                                front_left_idx = arrangement[i] - 1 if arrangement[i] else None
                                front_right_idx = arrangement[i+1] - 1 if arrangement[i+1] else None
                                back_left_idx = arrangement[i+2] - 1 if arrangement[i+2] else None
                                back_right_idx = arrangement[i+3] - 1 if arrangement[i+3] else None

                                # Create front side
                                front = create_2up_page(
                                    processed_images[front_left_idx] if front_left_idx is not None else None,
                                    processed_images[front_right_idx] if front_right_idx is not None else None,
                                    landscape_w,
                                    landscape_h,
                                    export_dpi,
                                    vertical_align
                                )
                                composite_sheets.append(front)

                                # Create back side
                                back = create_2up_page(
                                    processed_images[back_left_idx] if back_left_idx is not None else None,
                                    processed_images[back_right_idx] if back_right_idx is not None else None,
                                    landscape_w,
                                    landscape_h,
                                    export_dpi,
                                    vertical_align
                                )
                                composite_sheets.append(back)

                        else:  # Sequential mode
                            for i in range(0, len(processed_images), 2):
                                left = processed_images[i]
                                right = processed_images[i+1] if i+1 < len(processed_images) else None
                                sheet = create_2up_page(left, right, landscape_w, landscape_h, export_dpi, vertical_align)
                                composite_sheets.append(sheet)

                        # Use composite sheets for PDF generation
                        final_images = composite_sheets
                        # Set target page size to landscape dimensions
                        final_page_size = (landscape_w * 72, landscape_h * 72)
                    else:
                        # Regular single-page layout
                        final_images = processed_images
                        if pad_to_exact_size and st.session_state.page_size_override:
                            target_w, target_h = st.session_state.page_size_override
                            final_page_size = (target_w * 72, target_h * 72)
                        else:
                            final_page_size = None

                    # Parse compression settings
                    if compression_format.startswith("JPEG"):
                        image_format = "JPEG"
                        # Extract quality from format string
                        if "95%" in compression_format:
                            quality = 95
                        elif "90%" in compression_format:
                            quality = 90
                        elif "85%" in compression_format:
                            quality = 85
                        else:
                            quality = 95  # Default
                    else:
                        image_format = "PNG"
                        quality = None

                    # Generate PDF
                    if final_page_size:
                        pdf_bytes = PDFProcessor.images_to_pdf(
                            final_images,
                            target_page_size=final_page_size,
                            image_format=image_format,
                            jpeg_quality=quality
                        )
                    else:
                        pdf_bytes = PDFProcessor.images_to_pdf(
                            final_images,
                            image_format=image_format,
                            jpeg_quality=quality
                        )

                    # Offer download
                    st.download_button(
                        label="📥 Download Processed PDF",
                        data=pdf_bytes,
                        file_name=f"processed_{st.session_state.current_file_name}",
                        mime="application/pdf"
                    )

                st.success("PDF generated successfully!")

        with col_exp3:
            # Show processing status
            pages_with_filters = len([p for p in st.session_state.page_filters
                                     if st.session_state.page_filters[p] != get_default_filter_settings()])
            if pages_with_filters > 0:
                st.info(f"📊 {pages_with_filters} of {pdf_proc.page_count} pages have filters applied")

    else:
        # No PDF loaded
        st.info("👆 Please upload a PDF file to begin processing")

        # Instructions
        with st.expander("📖 How to use PDFMagick"):
            st.markdown("""
            1. **Upload a PDF** using the sidebar file uploader
            2. **Navigate pages** using the Previous/Next buttons or slider
            3. **Adjust filters** using the control panel - changes are shown in real-time
            4. **Apply to all pages** using "Copy Settings to All Pages" for batch processing
            5. **Export** your processed PDF with the quality setting of your choice

            ### Filter Guide:
            - **Brightness/Contrast**: Basic image adjustments
            - **Exposure**: Simulates camera exposure adjustment (in EV stops)
            - **Highlights/Shadows**: Selectively adjust bright and dark areas
            - **Saturation/Vibrance**: Color intensity (vibrance is more subtle)
            - **Levels**: Fine-tune black point, white point, and gamma
            - **Sharpness**: Enhance edge definition

            ### Tips:
            - Use "Auto Enhance" for quick improvements
            - Adjust exposure before other settings for best results
            - Vibrance is gentler than saturation for natural colors
            """)


if __name__ == "__main__":
    main()