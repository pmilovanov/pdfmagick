"""Tests for histogram-based auto-enhancement functionality."""

import numpy as np
import pytest
from PIL import Image

from core.image_filters import ImageFilters


@pytest.fixture
def dark_test_image():
    """Create a dark test image (histogram skewed low)."""
    # 100x100 image with pixels mostly in 20-80 range
    img_array = np.random.randint(20, 80, (100, 100, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def bright_test_image():
    """Create a bright test image (histogram skewed high)."""
    # 100x100 image with pixels mostly in 180-240 range
    img_array = np.random.randint(180, 240, (100, 100, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def balanced_test_image():
    """Create well-distributed test image."""
    # Even distribution across 0-255
    img_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def extreme_dark_image():
    """Create extremely dark image (nearly all pixels below 10)."""
    img_array = np.random.randint(0, 10, (100, 100, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def extreme_bright_image():
    """Create extremely bright image (nearly all pixels above 245)."""
    img_array = np.random.randint(245, 255, (100, 100, 3), dtype=np.uint8)
    return Image.fromarray(img_array)


@pytest.fixture
def grayscale_test_image():
    """Create grayscale test image."""
    img_array = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
    return Image.fromarray(img_array, mode='L')


class TestCalculateAutoEnhanceSettings:
    """Tests for the calculate_auto_enhance_settings function."""

    def test_returns_dict_with_all_filters(self, balanced_test_image):
        """Test that the function returns a dict with all filter settings."""
        settings = ImageFilters.calculate_auto_enhance_settings(balanced_test_image)

        # Check that all expected keys are present
        expected_keys = {
            'brightness', 'contrast', 'highlights', 'midtones', 'shadows',
            'exposure', 'saturation', 'vibrance', 'sharpness',
            'black_point', 'white_point', 'gamma'
        }
        assert set(settings.keys()) == expected_keys

    def test_dark_image_enhancement(self, dark_test_image):
        """Test enhancement settings for a dark image."""
        settings = ImageFilters.calculate_auto_enhance_settings(dark_test_image)

        # For a dark image, we expect:
        # - black_point should be low (at histogram 5th percentile, but capped at 50)
        # - white_point should be pulled down somewhat
        # - contrast boost applied
        assert settings['black_point'] <= 50, "Black point should be capped at 50"
        assert settings['white_point'] >= 205, "White point should be at least 205"
        assert settings['contrast'] > 0, "Should have contrast boost"

    def test_bright_image_enhancement(self, bright_test_image):
        """Test enhancement settings for a bright/washed out image."""
        settings = ImageFilters.calculate_auto_enhance_settings(bright_test_image)

        # For a bright image, we expect:
        # - black_point might be pushed up
        # - white_point should stay high (capped at minimum 205)
        # - contrast boost applied
        assert settings['black_point'] <= 50, "Black point should be capped at 50"
        assert settings['white_point'] >= 205, "White point should be at least 205"
        assert settings['contrast'] > 0, "Should have contrast boost"

    def test_well_distributed_image(self, balanced_test_image):
        """Test enhancement for a well-distributed image."""
        settings = ImageFilters.calculate_auto_enhance_settings(balanced_test_image)

        # For a well-distributed image:
        # Should detect that enhancement is minimal and apply subtle boost
        # The exact values depend on the random distribution, but we can check
        # that SOME enhancement is applied
        assert settings['contrast'] >= 3.0, "Should have at least subtle contrast boost"

        # If subtle enhancement path is taken, should have brightness boost
        if settings['black_point'] <= 20 and settings['white_point'] >= 235:
            assert settings['brightness'] == 2.0, "Subtle enhancement should include brightness"
            assert settings['contrast'] == 3.0, "Subtle enhancement should use contrast 3.0"

    def test_extreme_dark_image_capping(self, extreme_dark_image):
        """Test that black_point is properly capped for extreme dark images."""
        settings = ImageFilters.calculate_auto_enhance_settings(extreme_dark_image)

        # Even with an extremely dark image, black_point should not exceed 50
        assert settings['black_point'] <= 50, "Black point must be capped at 50"
        assert settings['black_point'] >= 0, "Black point must be non-negative"

    def test_extreme_bright_image_capping(self, extreme_bright_image):
        """Test that white_point is properly capped for extreme bright images."""
        settings = ImageFilters.calculate_auto_enhance_settings(extreme_bright_image)

        # Even with an extremely bright image, white_point should not go below 205
        assert settings['white_point'] >= 205, "White point must be at least 205"
        assert settings['white_point'] <= 255, "White point must not exceed 255"

    def test_grayscale_image_handling(self, grayscale_test_image):
        """Test that function handles grayscale images correctly."""
        settings = ImageFilters.calculate_auto_enhance_settings(grayscale_test_image)

        # Should work without errors on grayscale
        assert isinstance(settings, dict)
        assert 'black_point' in settings
        assert 'white_point' in settings
        assert settings['black_point'] <= 50
        assert settings['white_point'] >= 205

    def test_rgb_vs_grayscale_consistency(self):
        """Test that RGB and grayscale versions of same image produce similar results."""
        # Create a grayscale pattern
        gray_array = np.random.randint(50, 200, (100, 100), dtype=np.uint8)
        grayscale_img = Image.fromarray(gray_array, mode='L')

        # Create RGB version with same pattern
        rgb_array = np.stack([gray_array, gray_array, gray_array], axis=2)
        rgb_img = Image.fromarray(rgb_array, mode='RGB')

        gray_settings = ImageFilters.calculate_auto_enhance_settings(grayscale_img)
        rgb_settings = ImageFilters.calculate_auto_enhance_settings(rgb_img)

        # The histogram analysis should produce similar results
        # Allow for small differences due to float precision
        assert abs(gray_settings['black_point'] - rgb_settings['black_point']) <= 2
        assert abs(gray_settings['white_point'] - rgb_settings['white_point']) <= 2
        assert gray_settings['contrast'] == rgb_settings['contrast']

    def test_default_values_for_unused_filters(self, balanced_test_image):
        """Test that unused filters remain at default values."""
        settings = ImageFilters.calculate_auto_enhance_settings(balanced_test_image)

        # These filters should always be at default (not affected by auto-enhance)
        assert settings['highlights'] == 0.0
        assert settings['midtones'] == 0.0
        assert settings['shadows'] == 0.0
        assert settings['exposure'] == 0.0
        assert settings['saturation'] == 0.0
        assert settings['vibrance'] == 0.0
        assert settings['sharpness'] == 0.0
        assert settings['gamma'] == 1.0

    def test_values_within_valid_ranges(self, balanced_test_image):
        """Test that all returned values are within valid ranges."""
        settings = ImageFilters.calculate_auto_enhance_settings(balanced_test_image)

        # Check ranges match the FilterSettings model constraints
        assert -100 <= settings['brightness'] <= 100
        assert -100 <= settings['contrast'] <= 100
        assert -100 <= settings['highlights'] <= 100
        assert -100 <= settings['midtones'] <= 100
        assert -100 <= settings['shadows'] <= 100
        assert -3 <= settings['exposure'] <= 3
        assert -100 <= settings['saturation'] <= 100
        assert -100 <= settings['vibrance'] <= 100
        assert -100 <= settings['sharpness'] <= 100
        assert 0 <= settings['black_point'] <= 255
        assert 0 <= settings['white_point'] <= 255
        assert 0.1 <= settings['gamma'] <= 3.0

    def test_deterministic_output(self):
        """Test that the same image produces the same settings."""
        # Create a fixed test image
        np.random.seed(42)
        img_array = np.random.randint(50, 200, (100, 100, 3), dtype=np.uint8)
        test_img = Image.fromarray(img_array)

        # Calculate settings twice
        settings1 = ImageFilters.calculate_auto_enhance_settings(test_img)
        settings2 = ImageFilters.calculate_auto_enhance_settings(test_img)

        # Should be identical
        assert settings1 == settings2
