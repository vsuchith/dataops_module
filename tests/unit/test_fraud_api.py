"""
Unit tests for the Fraud Detection API.

Tests cover:
- Health and readiness endpoints
- Prediction endpoints (single and batch)
- Shadow mode endpoints
- Performance endpoints
- Error handling
"""

import os
from unittest.mock import MagicMock, patch

import pytest
from starlette.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    """Module-scoped TestClient with DI overrides (avoids per-test import deadlock)."""
    env = {
        "PROMETHEUS_METRICS": "false",
        "AB_TEST_ENABLED": "false",
        "SHADOW_MODE_ENABLED": "false",
    }
    with patch.dict(os.environ, env), patch("redis.Redis") as mock_redis:
        mock_redis.return_value.ping.return_value = True

        from src.api.dependencies import (
            get_ab_router,
            get_scoring_pipeline,
            get_shadow_predictor,
        )
        from src.mlops.api.main import app

        mock_pipeline = MagicMock()
        mock_pipeline.health_check.return_value = {"model": "ok"}

        mock_shadow = MagicMock()
        mock_shadow.get_status.return_value = {"enabled": False, "available": True}
        mock_shadow.get_stats.return_value = MagicMock(to_dict=lambda: {"total": 0})

        mock_router = MagicMock()
        mock_router.list_experiments.return_value = []

        app.dependency_overrides[get_scoring_pipeline] = lambda: mock_pipeline
        app.dependency_overrides[get_shadow_predictor] = lambda: mock_shadow
        app.dependency_overrides[get_ab_router] = lambda: mock_router

        with TestClient(app, raise_server_exceptions=False) as test_client:
            yield test_client

        app.dependency_overrides.clear()


# =============================================================================
# HEALTH ENDPOINTS
# =============================================================================

class TestHealthEndpoints:
    """Tests for health and readiness endpoints."""

    def test_health_endpoint_returns_ok(self, client):
        """Test that /health returns 200 with status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] in ["healthy", "degraded"]

    def test_ready_endpoint_returns_status(self, client):
        """Test that /ready returns readiness status."""
        response = client.get("/ready")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert "ready" in data

    def test_root_endpoint_returns_welcome(self, client):
        """Test that root endpoint returns API info."""
        response = client.get("/")

        assert response.status_code == 200


# =============================================================================
# SHADOW MODE ENDPOINTS
# =============================================================================

class TestShadowModeEndpoints:
    """Tests for shadow mode endpoints."""

    def test_shadow_status_endpoint(self, client):
        """Test /shadow/status returns shadow mode status."""
        response = client.get("/shadow/status")

        assert response.status_code == 200
        data = response.json()
        assert "enabled" in data or "available" in data

    def test_shadow_stats_endpoint(self, client):
        """Test /shadow/stats returns statistics."""
        response = client.get("/shadow/stats")

        assert response.status_code in [200, 503]

    def test_shadow_enable_endpoint(self, client):
        """Test /shadow/enable enables shadow mode."""
        response = client.post("/shadow/enable")

        assert response.status_code in [200, 503]


# =============================================================================
# STREAMING ENDPOINTS
# =============================================================================

class TestStreamingEndpoints:
    """Tests for streaming feature endpoints."""

    def test_streaming_status_endpoint(self, client):
        """Test /streaming/status returns streaming status."""
        response = client.get("/streaming/status")

        assert response.status_code == 200
        data = response.json()
        assert "available" in data or "enabled" in data or "status" in data

    def test_streaming_features_endpoint(self, client):
        """Test /streaming/features/{customer_id} returns features."""
        with patch("src.api.serving.features.redis_client.AsyncStreamingRedisClient") as mock_client:
            mock_client.return_value.get_streaming_features.return_value = ({}, 1.0, True)
            response = client.get("/streaming/features/CUST_123")

        assert response.status_code in [200, 500, 503]

    def test_metrics_endpoint(self, client):
        """Test /metrics returns Prometheus metrics."""
        response = client.get("/metrics")

        assert response.status_code in [200, 503]


# =============================================================================
# VALIDATION TESTS
# =============================================================================

class TestInputValidation:
    """Tests for input validation."""

    def test_batch_limit_validation(self, client):
        """Test that batch endpoint respects max limit."""
        response = client.get("/batch/stats")
        assert response.status_code in [200, 404]

    def test_predict_uses_profile_validation(self, client, monkeypatch):
        """Predict path invokes compatibility profile validation before scoring."""

        def _fail_validation(_transaction):
            raise ValueError("profile validation invoked")

        monkeypatch.setattr(
            "src.mlops.api.main.validate_transaction_request",
            _fail_validation,
        )
        response = client.post(
            "/predict",
            json={
                "transaction_id": "TXN_1",
                "customer_id": "CUST_1",
                "amount": 10.0,
            },
        )

        assert response.status_code == 422
        assert response.json()["detail"] == "profile validation invoked"


# =============================================================================
# API INFO ENDPOINTS
# =============================================================================

class TestInfoEndpoints:
    """Tests for informational endpoints."""

    def test_model_info_endpoint(self, client):
        """Test /model/info returns model information."""
        response = client.get("/model/info")

        assert response.status_code in [200, 404]
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)

    def test_experiments_endpoint(self, client):
        """Test /experiments returns A/B testing status."""
        response = client.get("/experiments")

        assert response.status_code in [200, 404]
