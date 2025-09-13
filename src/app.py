"""Streamlit application for PDF image processing with real-time preview."""

import streamlit as st
from pathlib import Path
import tempfile
from typing import Dict, Any, Optional
import io
import numpy as np
import cv2

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
                        # Get the image for this page
                        img = pdf_proc.get_page_as_image(page_num, dpi=150)
                        img_array = np.array(img)

                        # Calculate grayscale for analysis
                        if len(img_array.shape) == 3:
                            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                        else:
                            gray = img_array

                        # Find optimal settings for this specific page
                        black_point = int(np.percentile(gray, 2))
                        white_point = int(np.percentile(gray, 98))

                        # Create settings for this page
                        page_settings = get_default_filter_settings()
                        page_settings['black_point'] = black_point
                        page_settings['white_point'] = white_point
                        page_settings['contrast'] = 10.0

                        # Save settings for this page
                        st.session_state.page_filters[page_num] = page_settings

                    # Update current page settings if it's the current page
                    if current_page in st.session_state.page_filters:
                        st.session_state.filter_settings = st.session_state.page_filters[current_page].copy()

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
                original_image = pdf_proc.get_page_as_image(current_page, dpi=150)

                # Calculate auto-enhance parameters
                img_array = np.array(original_image)
                if len(img_array.shape) == 3:
                    gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                else:
                    gray = img_array

                # Find optimal black and white points
                black_point = int(np.percentile(gray, 2))
                white_point = int(np.percentile(gray, 98))

                # Update the filter settings
                st.session_state.filter_settings['black_point'] = black_point
                st.session_state.filter_settings['white_point'] = white_point
                st.session_state.filter_settings['contrast'] = 10.0  # Slight contrast boost

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
            original_image = pdf_proc.get_page_as_image(current_page, dpi=150)
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
        col_exp1, col_exp2, col_exp3 = st.columns([1, 1, 3])

        with col_exp1:
            export_dpi = st.selectbox(
                "Export Quality (DPI)",
                options=[150, 200, 300, 400],
                index=1
            )

        with col_exp2:
            if st.button("🚀 Generate PDF", type="primary"):
                with st.spinner("Processing all pages and generating PDF..."):
                    # Process all pages
                    processed_images = []
                    for page_num in range(pdf_proc.page_count):
                        # Get original image at export DPI
                        img = pdf_proc.get_page_as_image(page_num, dpi=export_dpi)

                        # Apply filters if they exist for this page
                        if page_num in st.session_state.page_filters:
                            settings = st.session_state.page_filters[page_num]
                            img = apply_filters_to_image(img, settings)

                        processed_images.append(img)

                    # Generate PDF
                    pdf_bytes = PDFProcessor.images_to_pdf(processed_images)

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