"""API integration tests for auto-enhancement endpoint."""

import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
import numpy as np

from api.main import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def uploaded_pdf(client, tmp_path, create_test_pdf):
    """Upload a test PDF and return the PDF ID."""
    # Create a test PDF with a few pages
    pdf_path = tmp_path / "test.pdf"
    pdf_bytes = create_test_pdf(num_pages=3)

    with open(pdf_path, 'wb') as f:
        f.write(pdf_bytes)

    # Upload the PDF
    with open(pdf_path, 'rb') as f:
        response = client.post(
            "/api/pdf/upload",
            files={"file": ("test.pdf", f, "application/pdf")}
        )

    assert response.status_code == 200
    pdf_info = response.json()
    return pdf_info['pdf_id']


class TestAutoEnhanceAPIEndpoint:
    """Tests for the /api/pdf/{pdf_id}/page/{page_num}/auto-enhance endpoint."""

    def test_endpoint_exists(self, client, uploaded_pdf):
        """Test that the auto-enhance endpoint exists and is accessible."""
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")
        assert response.status_code == 200

    def test_returns_valid_filter_settings(self, client, uploaded_pdf):
        """Test that the endpoint returns a valid FilterSettings object."""
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")

        assert response.status_code == 200
        settings = response.json()

        # Check that all expected keys are present
        expected_keys = {
            'brightness', 'contrast', 'highlights', 'midtones', 'shadows',
            'exposure', 'saturation', 'vibrance', 'sharpness',
            'black_point', 'white_point', 'gamma'
        }
        assert set(settings.keys()) == expected_keys

    def test_values_within_valid_ranges(self, client, uploaded_pdf):
        """Test that returned values are within valid ranges."""
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")

        assert response.status_code == 200
        settings = response.json()

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

    def test_invalid_pdf_id_returns_404(self, client):
        """Test that requesting a non-existent PDF returns 404."""
        response = client.get("/api/pdf/nonexistent/page/0/auto-enhance")
        assert response.status_code == 404
        assert "PDF not found" in response.json()['detail']

    def test_invalid_page_number_returns_400(self, client, uploaded_pdf):
        """Test that requesting an invalid page number returns 400."""
        # Test negative page number
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/-1/auto-enhance")
        assert response.status_code == 400
        assert "Invalid page number" in response.json()['detail']

        # Test page number beyond document length
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/999/auto-enhance")
        assert response.status_code == 400
        assert "Invalid page number" in response.json()['detail']

    def test_custom_dpi_parameter(self, client, uploaded_pdf):
        """Test that the DPI parameter is respected."""
        # Default DPI
        response1 = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")
        assert response1.status_code == 200

        # Custom DPI (should still work, might produce slightly different results)
        response2 = client.get(
            f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance",
            params={"dpi": 300}
        )
        assert response2.status_code == 200

        # Both should return valid settings
        settings1 = response1.json()
        settings2 = response2.json()

        assert 'black_point' in settings1
        assert 'black_point' in settings2

    def test_multiple_pages_different_settings(self, client, uploaded_pdf):
        """Test that different pages can have different enhancement settings."""
        # Get settings for page 0
        response0 = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")
        settings0 = response0.json()

        # Get settings for page 1
        response1 = client.get(f"/api/pdf/{uploaded_pdf}/page/1/auto-enhance")
        settings1 = response1.json()

        # Both should be valid
        assert response0.status_code == 200
        assert response1.status_code == 200

        # Note: Depending on page content, settings might be the same or different
        # We just verify both calls succeed and return valid data
        assert 'black_point' in settings0
        assert 'black_point' in settings1

    def test_enhancement_settings_are_sensible(self, client, uploaded_pdf):
        """Test that enhancement settings make sense."""
        response = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")
        settings = response.json()

        # Black point should be less than white point
        assert settings['black_point'] < settings['white_point']

        # Gamma should be positive
        assert settings['gamma'] > 0

        # Contrast boost should be applied (either 3.0 or 5.0 based on algorithm)
        assert settings['contrast'] in [0.0, 3.0, 5.0]

    def test_consistency_across_repeated_calls(self, client, uploaded_pdf):
        """Test that the same page analyzed multiple times returns same results."""
        # Call the endpoint twice for the same page
        response1 = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")
        response2 = client.get(f"/api/pdf/{uploaded_pdf}/page/0/auto-enhance")

        assert response1.status_code == 200
        assert response2.status_code == 200

        settings1 = response1.json()
        settings2 = response2.json()

        # Should be identical
        assert settings1 == settings2
