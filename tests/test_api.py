"""
Integration tests for Skyvault KYC API endpoints.

Tests cover:
- Health check endpoint
- Webhook transcript endpoint
- Synchronous extraction endpoint
- Request validation
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestHealthCheck:
    """Tests for the health check endpoint."""

    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from app.main import app
            return TestClient(app)

    @pytest.mark.integration
    def test_health_check_returns_healthy(self, client):
        """Test that health check returns healthy status."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "Skyvault KYC API"


class TestWebhookEndpoint:
    """Tests for the /webhook/transcript endpoint."""

    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from app.main import app
            return TestClient(app)

    @pytest.fixture
    def valid_transcript_request(self):
        """Valid transcript request fixture."""
        return {
            "transcript": "Hello, my name is John Doe. I am 45 years old and work as an engineer. My annual income is $150,000.",
            "source_language": "en",
            "client_id": "test-123",
            "dealing_rep": "Test Rep",
            "call_date": "2024-01-15",
            "form_type": "individual"
        }

    @pytest.mark.integration
    def test_webhook_accepts_valid_transcript(self, client, valid_transcript_request):
        """Test webhook accepts valid transcript and returns processing status."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "first_name": "John",
                "last_name": "Doe",
                "missing_fields": []
            }

            response = client.post("/webhook/transcript", json=valid_transcript_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert data["client_name"] == "John Doe"
        assert data["form_type"] == "individual"

    @pytest.mark.integration
    def test_webhook_rejects_short_transcript(self, client):
        """Test webhook rejects transcripts that are too short."""
        response = client.post("/webhook/transcript", json={
            "transcript": "Too short"
        })

        assert response.status_code == 400
        assert "too short" in response.json()["detail"].lower()

    @pytest.mark.integration
    def test_webhook_rejects_empty_transcript(self, client):
        """Test webhook rejects empty transcripts."""
        response = client.post("/webhook/transcript", json={
            "transcript": ""
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_webhook_rejects_whitespace_only_transcript(self, client):
        """Test webhook rejects whitespace-only transcripts."""
        response = client.post("/webhook/transcript", json={
            "transcript": "   \n\t   "
        })

        assert response.status_code == 400

    @pytest.mark.integration
    def test_webhook_uses_default_values(self, client):
        """Test webhook uses default values for optional fields."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "first_name": "Test",
                "last_name": "User",
                "missing_fields": []
            }

            response = client.post("/webhook/transcript", json={
                "transcript": "A sufficiently long transcript to pass validation checks for the endpoint."
            })

        assert response.status_code == 200
        data = response.json()
        assert data["form_type"] == "individual"  # Default

    @pytest.mark.integration
    def test_webhook_handles_extraction_failure(self, client, valid_transcript_request):
        """Test webhook handles extraction failure gracefully."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.side_effect = Exception("API Error")

            response = client.post("/webhook/transcript", json=valid_transcript_request)

        assert response.status_code == 200
        data = response.json()
        assert data["client_name"] is None or data["client_name"] == "Unknown"

    @pytest.mark.integration
    def test_webhook_returns_missing_fields(self, client, valid_transcript_request):
        """Test webhook returns missing fields from quick extraction."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {
                "first_name": "John",
                "last_name": None,
                "missing_fields": ["last_name", "email"]
            }

            response = client.post("/webhook/transcript", json=valid_transcript_request)

        assert response.status_code == 200
        data = response.json()
        assert "last_name" in data["missing_fields"]


class TestSyncExtractEndpoint:
    """Tests for the /extract/sync endpoint."""

    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from app.main import app
            return TestClient(app)

    @pytest.fixture
    def valid_transcript_request(self):
        return {
            "transcript": "Hello, my name is Jane Smith. I work as a doctor with income of $200,000 per year.",
            "source_language": "en",
            "form_type": "individual"
        }

    @pytest.mark.integration
    def test_sync_extract_returns_full_data(self, client, valid_transcript_request):
        """Test sync extraction returns full extracted data."""
        mock_extracted = {
            "client_name": {"first": "Jane", "last": "Smith"},
            "employment": {"occupation": "Doctor"},
            "financials": {"annual_income": 200000}
        }

        with patch("app.main.extractor.extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = mock_extracted

            response = client.post("/extract/sync", json=valid_transcript_request)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["extracted_data"]["client_name"]["first"] == "Jane"
        assert data["extracted_data"]["financials"]["annual_income"] == 200000

    @pytest.mark.integration
    def test_sync_extract_includes_validation(self, client, valid_transcript_request):
        """Test sync extraction includes validation results."""
        mock_extracted = {
            "client_name": {"first": "Jane", "last": "Smith"},
            "financials": {"annual_income": 250000, "income_stable_2_years": True}
        }

        with patch("app.main.extractor.extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = mock_extracted

            response = client.post("/extract/sync", json=valid_transcript_request)

        assert response.status_code == 200
        data = response.json()
        assert "validation" in data

    @pytest.mark.integration
    def test_sync_extract_supports_corporate_form(self, client):
        """Test sync extraction works with corporate form type."""
        mock_extracted = {
            "corporate_name": "Test Corp Inc",
            "business_number": "123456789"
        }

        with patch("app.main.extractor.extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = mock_extracted

            response = client.post("/extract/sync", json={
                "transcript": "This is a corporate KYC call for Test Corp Inc, business number 123456789.",
                "form_type": "corporate"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["extracted_data"]["corporate_name"] == "Test Corp Inc"


class TestRequestValidation:
    """Tests for request validation."""

    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from app.main import app
            return TestClient(app)

    @pytest.mark.integration
    def test_missing_transcript_field(self, client):
        """Test request without transcript field is rejected."""
        response = client.post("/webhook/transcript", json={
            "source_language": "en"
        })

        assert response.status_code == 422  # Validation error

    @pytest.mark.integration
    def test_invalid_json_body(self, client):
        """Test invalid JSON body is rejected."""
        response = client.post(
            "/webhook/transcript",
            content="not valid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_accepts_minimal_request(self, client):
        """Test accepts request with only required fields."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_extract:
            mock_extract.return_value = {"first_name": "Test", "last_name": "User", "missing_fields": []}

            response = client.post("/webhook/transcript", json={
                "transcript": "This is a minimal request with just the transcript field that meets minimum length."
            })

        assert response.status_code == 200


class TestBackgroundProcessing:
    """Tests for background task processing."""

    @pytest.fixture
    def client(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            from app.main import app
            return TestClient(app)

    @pytest.mark.integration
    def test_background_task_is_queued(self, client):
        """Test that background processing task is queued."""
        with patch("app.main.extractor.quick_extract", new_callable=AsyncMock) as mock_quick:
            mock_quick.return_value = {"first_name": "John", "last_name": "Doe", "missing_fields": []}

            with patch("app.main.BackgroundTasks.add_task") as mock_add_task:
                # Note: TestClient runs background tasks synchronously by default
                response = client.post("/webhook/transcript", json={
                    "transcript": "A long enough transcript to process for background task testing purposes."
                })

        assert response.status_code == 200
        # Response returns immediately with "processing" status
        assert response.json()["status"] == "processing"
