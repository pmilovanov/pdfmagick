"""Image filter implementations for PDF page processing."""

import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageDraw, ImageFont
from typing import Optional, Tuple


class ImageFilters:
    """Collection of image filters and adjustments."""

    @staticmethod
    def adjust_brightness_contrast(
        image: Image.Image,
        brightness: float = 0.0,
        contrast: float = 0.0
    ) -> Image.Image:
        """Adjust brightness and contrast.

        Args:
            image: Input PIL Image
            brightness: Brightness adjustment (-100 to 100, 0 = no change)
            contrast: Contrast adjustment (-100 to 100, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        # Brightness adjustment
        if brightness != 0:
            enhancer = ImageEnhance.Brightness(image)
            factor = 1 + (brightness / 100.0)
            image = enhancer.enhance(factor)

        # Contrast adjustment
        if contrast != 0:
            enhancer = ImageEnhance.Contrast(image)
            factor = 1 + (contrast / 100.0)
            image = enhancer.enhance(factor)

        return image

    @staticmethod
    def adjust_highlights_midtones_shadows(
        image: Image.Image,
        highlights: float = 0.0,
        midtones: float = 0.0,
        shadows: float = 0.0
    ) -> Image.Image:
        """Adjust highlights, midtones, and shadows.

        Args:
            image: Input PIL Image
            highlights: Highlight adjustment (-100 to 100, 0 = no change)
            midtones: Midtone adjustment (-100 to 100, 0 = no change)
            shadows: Shadow adjustment (-100 to 100, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        # Convert to numpy array
        img_array = np.array(image).astype(np.float32) / 255.0

        # Create luminance map
        if len(img_array.shape) == 3:
            luminance = 0.299 * img_array[:, :, 0] + 0.587 * img_array[:, :, 1] + 0.114 * img_array[:, :, 2]
        else:
            luminance = img_array

        # Adjust highlights (affects bright areas more)
        if highlights != 0:
            highlight_factor = highlights / 100.0
            highlight_mask = np.power(luminance, 2)  # Quadratic for stronger effect on brights
            if len(img_array.shape) == 3:
                for i in range(3):
                    img_array[:, :, i] = img_array[:, :, i] * (1 + highlight_factor * highlight_mask)
            else:
                img_array = img_array * (1 + highlight_factor * highlight_mask)

        # Adjust midtones (affects middle luminance values more)
        if midtones != 0:
            midtone_factor = midtones / 100.0
            # Bell curve centered at 0.5 luminance
            midtone_mask = np.exp(-4 * np.power(luminance - 0.5, 2))
            if len(img_array.shape) == 3:
                for i in range(3):
                    img_array[:, :, i] = img_array[:, :, i] * (1 + midtone_factor * midtone_mask)
            else:
                img_array = img_array * (1 + midtone_factor * midtone_mask)

        # Adjust shadows (affects dark areas more)
        if shadows != 0:
            shadow_factor = shadows / 100.0
            shadow_mask = 1 - luminance  # Inverted for shadows
            if len(img_array.shape) == 3:
                for i in range(3):
                    img_array[:, :, i] = img_array[:, :, i] + shadow_factor * shadow_mask[:, :, np.newaxis][:, :, 0]
            else:
                img_array = img_array + shadow_factor * shadow_mask

        # Clip values and convert back
        img_array = np.clip(img_array, 0, 1)
        img_array = (img_array * 255).astype(np.uint8)

        return Image.fromarray(img_array)

    @staticmethod
    def adjust_exposure(
        image: Image.Image,
        exposure: float = 0.0
    ) -> Image.Image:
        """Adjust exposure (similar to camera EV adjustment).

        Args:
            image: Input PIL Image
            exposure: Exposure adjustment in stops (-3 to 3, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        if exposure == 0:
            return image

        # Convert to numpy array
        img_array = np.array(image).astype(np.float32) / 255.0

        # Apply exposure adjustment (2^exposure multiplication)
        factor = np.power(2, exposure)
        img_array = img_array * factor

        # Clip and convert back
        img_array = np.clip(img_array, 0, 1)
        img_array = (img_array * 255).astype(np.uint8)

        return Image.fromarray(img_array)

    @staticmethod
    def adjust_saturation(
        image: Image.Image,
        saturation: float = 0.0
    ) -> Image.Image:
        """Adjust color saturation.

        Args:
            image: Input PIL Image
            saturation: Saturation adjustment (-100 to 100, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        if saturation == 0:
            return image

        enhancer = ImageEnhance.Color(image)
        factor = 1 + (saturation / 100.0)
        return enhancer.enhance(factor)

    @staticmethod
    def adjust_levels(
        image: Image.Image,
        black_point: int = 0,
        white_point: int = 255,
        gamma: float = 1.0
    ) -> Image.Image:
        """Adjust levels (black point, white point, and gamma).

        Args:
            image: Input PIL Image
            black_point: Black point (0-255)
            white_point: White point (0-255)
            gamma: Gamma adjustment (0.1-3.0, 1.0 = no change)

        Returns:
            Adjusted PIL Image
        """
        # Convert to numpy array
        img_array = np.array(image).astype(np.float32)

        # Apply levels adjustment
        img_array = np.clip((img_array - black_point) / (white_point - black_point), 0, 1)

        # Apply gamma correction
        if gamma != 1.0:
            img_array = np.power(img_array, 1.0 / gamma)

        # Convert back to 8-bit
        img_array = (img_array * 255).astype(np.uint8)

        return Image.fromarray(img_array)

    @staticmethod
    def adjust_vibrance(
        image: Image.Image,
        vibrance: float = 0.0
    ) -> Image.Image:
        """Adjust vibrance (smart saturation that protects skin tones).

        Args:
            image: Input PIL Image
            vibrance: Vibrance adjustment (-100 to 100, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        if vibrance == 0:
            return image

        # Convert to numpy array
        img_array = np.array(image).astype(np.float32) / 255.0

        if len(img_array.shape) == 3 and img_array.shape[2] >= 3:
            # Convert to HSV
            img_hsv = cv2.cvtColor((img_array * 255).astype(np.uint8), cv2.COLOR_RGB2HSV).astype(np.float32)
            img_hsv[:, :, 1] /= 255.0  # Normalize saturation channel

            # Calculate saturation mask (less saturated colors get more boost)
            sat_mask = 1.0 - img_hsv[:, :, 1]

            # Apply vibrance adjustment
            factor = vibrance / 100.0
            img_hsv[:, :, 1] = img_hsv[:, :, 1] + (factor * sat_mask * img_hsv[:, :, 1])
            img_hsv[:, :, 1] = np.clip(img_hsv[:, :, 1], 0, 1)

            # Convert back to RGB
            img_hsv[:, :, 1] *= 255.0
            img_rgb = cv2.cvtColor(img_hsv.astype(np.uint8), cv2.COLOR_HSV2RGB)

            return Image.fromarray(img_rgb)

        return image

    @staticmethod
    def adjust_sharpness(
        image: Image.Image,
        sharpness: float = 0.0
    ) -> Image.Image:
        """Adjust image sharpness.

        Args:
            image: Input PIL Image
            sharpness: Sharpness adjustment (-100 to 100, 0 = no change)

        Returns:
            Adjusted PIL Image
        """
        if sharpness == 0:
            return image

        enhancer = ImageEnhance.Sharpness(image)
        factor = 1 + (sharpness / 100.0)
        return enhancer.enhance(factor)

    @staticmethod
    def auto_enhance(image: Image.Image) -> Image.Image:
        """Apply automatic enhancement based on image analysis.

        Args:
            image: Input PIL Image

        Returns:
            Enhanced PIL Image
        """
        # Convert to numpy for analysis
        img_array = np.array(image)

        # Calculate histogram statistics
        if len(img_array.shape) == 3:
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        else:
            gray = img_array

        # Find optimal black and white points (2% and 98% percentiles)
        black_point = np.percentile(gray, 2)
        white_point = np.percentile(gray, 98)

        # Apply auto levels
        image = ImageFilters.adjust_levels(image, int(black_point), int(white_point), 1.0)

        # Slight contrast boost
        image = ImageFilters.adjust_brightness_contrast(image, 0, 10)

        return image

    @staticmethod
    def apply_all_adjustments(
        image: Image.Image,
        brightness: float = 0.0,
        contrast: float = 0.0,
        highlights: float = 0.0,
        midtones: float = 0.0,
        shadows: float = 0.0,
        exposure: float = 0.0,
        saturation: float = 0.0,
        vibrance: float = 0.0,
        sharpness: float = 0.0,
        black_point: int = 0,
        white_point: int = 255,
        gamma: float = 1.0
    ) -> Image.Image:
        """Apply all adjustments in the optimal order.

        Args:
            image: Input PIL Image
            brightness: Brightness adjustment (-100 to 100)
            contrast: Contrast adjustment (-100 to 100)
            highlights: Highlight adjustment (-100 to 100)
            midtones: Midtone adjustment (-100 to 100)
            shadows: Shadow adjustment (-100 to 100)
            exposure: Exposure adjustment (-3 to 3)
            saturation: Saturation adjustment (-100 to 100)
            vibrance: Vibrance adjustment (-100 to 100)
            sharpness: Sharpness adjustment (-100 to 100)
            black_point: Black point (0-255)
            white_point: White point (0-255)
            gamma: Gamma adjustment (0.1-3.0)

        Returns:
            Adjusted PIL Image
        """
        # Apply in optimal order for best results
        result = image

        # Exposure first (affects overall brightness)
        if exposure != 0:
            result = ImageFilters.adjust_exposure(result, exposure)

        # Levels adjustment
        if black_point != 0 or white_point != 255 or gamma != 1.0:
            result = ImageFilters.adjust_levels(result, black_point, white_point, gamma)

        # Highlights, midtones and shadows
        if highlights != 0 or midtones != 0 or shadows != 0:
            result = ImageFilters.adjust_highlights_midtones_shadows(result, highlights, midtones, shadows)

        # Basic adjustments
        if brightness != 0 or contrast != 0:
            result = ImageFilters.adjust_brightness_contrast(result, brightness, contrast)

        # Color adjustments
        if saturation != 0:
            result = ImageFilters.adjust_saturation(result, saturation)

        if vibrance != 0:
            result = ImageFilters.adjust_vibrance(result, vibrance)

        # Sharpness last
        if sharpness != 0:
            result = ImageFilters.adjust_sharpness(result, sharpness)

        return result

    @staticmethod
    def add_padding_for_exact_size(image: Image.Image, target_width: int, target_height: int,
                                   page_num: int, first_odd_page: int = 1) -> Image.Image:
        """Add padding to reach exact target dimensions with alternating horizontal alignment for double-sided printing.

        Args:
            image: Input PIL Image
            target_width: Target width in pixels
            target_height: Target height in pixels
            page_num: Page number (1-indexed) to determine odd/even alignment
            first_odd_page: Which page number should be considered the first "odd" page (default=1)

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
            # Determine if this page should align left (odd) or right (even)
            # based on offset from the first odd page
            if (page_num - first_odd_page) % 2 == 0:  # This is an "odd" page - align left
                x_offset = 0
            else:  # This is an "even" page - align right
                x_offset = final_width - image.width
        else:
            # Center horizontally if no width padding needed
            x_offset = (final_width - image.width) // 2

        # Always align to top for height
        y_offset = 0

        # Paste original image at calculated position
        padded.paste(image, (x_offset, y_offset))

        return padded

    @staticmethod
    def add_page_number(image: Image.Image, page_num: int, total_pages: int,
                       format_style: str = "Page {n}", font_size: int = 14,
                       margin: int = 30) -> Image.Image:
        """Add page number to bottom-right corner of image.

        Args:
            image: Input PIL Image
            page_num: Current page number (1-indexed for display)
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
            text = f"Page {page_num}"
        elif format_style == "{n}":
            text = str(page_num)
        elif format_style == "{n} of {total}":
            text = f"{page_num} of {total_pages}"
        else:
            # Handle custom format with placeholders
            text = format_style.replace("{n}", str(page_num)).replace("{total}", str(total_pages))

        # Try to use a nice font, fall back to default if not available
        try:
            # Try common system fonts
            font_options = [
                "Helvetica.ttc", "Arial.ttf", "DejaVuSans.ttf",
                "/System/Library/Fonts/Helvetica.ttc",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/System/Library/Fonts/Supplemental/Arial.ttf",
                "/Library/Fonts/Arial.ttf"
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