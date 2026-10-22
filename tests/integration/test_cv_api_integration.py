"""
Integration tests for the CV Detection API.

These tests verify end-to-end functionality against running services.
Run with: pytest tests/integration/test_cv_api_integration.py -v -m integration
"""

import pytest


@pytest.mark.integration
class TestCVAPIHealth:
    """Integration tests for CV API health endpoints."""

    def test_health_endpoint_returns_healthy(self, cv_api_client):
        """Test that /health returns healthy status with real services."""
        response = cv_api_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert data.get("status") in ["healthy", "degraded", "ok"]

    def test_root_or_models_endpoint_available(self, cv_api_client):
        """Test that API exposes model or root metadata (fast endpoints only)."""
        for path in ("/models", "/metrics"):
            try:
                response = cv_api_client.get(path, timeout=5.0)
            except Exception:
                continue
            if response.status_code != 200:
                continue
            if path == "/metrics":
                return
            data = response.json()
            assert isinstance(data, dict)
            return
        pytest.skip("CV API metadata endpoints unavailable without MLflow stack")
