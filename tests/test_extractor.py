"""
Unit tests for KYC Extractor module.

Tests cover:
- JSON response parsing and cleaning
- Markdown stripping from API responses
- Error handling for malformed responses
- Quick extraction method
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.extractor import KYCExtractor, EXTRACTION_PROMPT


class TestExtractionPrompt:
    """Tests for the extraction prompt configuration."""

    @pytest.mark.unit
    def test_prompt_contains_critical_rules(self):
        """Test that prompt contains all critical extraction rules."""
        assert "NEVER HALLUCINATE" in EXTRACTION_PROMPT
        assert "SIN" in EXTRACTION_PROMPT
        assert "null" in EXTRACTION_PROMPT

    @pytest.mark.unit
    def test_prompt_contains_multilingual_support(self):
        """Test that prompt supports Russian/Ukrainian."""
        assert "Russian" in EXTRACTION_PROMPT or "доход" in EXTRACTION_PROMPT
        assert "Ukrainian" in EXTRACTION_PROMPT or "дохід" in EXTRACTION_PROMPT

    @pytest.mark.unit
    def test_prompt_contains_exemption_thresholds(self):
        """Test that prompt contains correct NI 45-106 thresholds."""
        assert "$200k" in EXTRACTION_PROMPT or "200k" in EXTRACTION_PROMPT
        assert "$300k" in EXTRACTION_PROMPT or "300k" in EXTRACTION_PROMPT
        assert "$1M" in EXTRACTION_PROMPT or "1M" in EXTRACTION_PROMPT

    @pytest.mark.unit
    def test_prompt_contains_risk_mapping(self):
        """Test that prompt contains risk tolerance mapping."""
        assert "LOW" in EXTRACTION_PROMPT
        assert "MODERATE" in EXTRACTION_PROMPT
        assert "HIGH" in EXTRACTION_PROMPT


class TestKYCExtractorInit:
    """Tests for KYCExtractor initialization."""

    @pytest.mark.unit
    @patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"})
    def test_init_with_api_key(self):
        """Test extractor initializes with API key."""
        extractor = KYCExtractor()
        assert extractor.model == "claude-sonnet-4-20250514"
        assert extractor.client is not None


class TestResponseCleaning:
    """Tests for cleaning API responses."""

    @pytest.fixture
    def extractor(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return KYCExtractor()

    @pytest.mark.unit
    async def test_clean_json_response(self, extractor):
        """Test parsing clean JSON response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"client_name": {"first": "John"}}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("test transcript")

        assert result["client_name"]["first"] == "John"

    @pytest.mark.unit
    async def test_strip_markdown_code_block(self, extractor):
        """Test stripping markdown code blocks from response."""
        markdown_response = '```json\n{"client_name": {"first": "Jane"}}\n```'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=markdown_response)]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("test transcript")

        assert result["client_name"]["first"] == "Jane"

    @pytest.mark.unit
    async def test_strip_markdown_without_json_label(self, extractor):
        """Test stripping markdown without 'json' label."""
        markdown_response = '```\n{"client_name": {"first": "Bob"}}\n```'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=markdown_response)]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("test transcript")

        assert result["client_name"]["first"] == "Bob"

    @pytest.mark.unit
    async def test_handle_invalid_json(self, extractor):
        """Test graceful handling of invalid JSON response."""
        invalid_json = 'This is not JSON at all'
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=invalid_json)]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("test transcript")

        assert "error" in result
        assert "parse_error" in result
        assert "raw_response" in result

    @pytest.mark.unit
    async def test_handle_partial_json(self, extractor):
        """Test handling of truncated/partial JSON."""
        partial_json = '{"client_name": {"first": "John'  # Missing closing braces
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=partial_json)]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("test transcript")

        assert "error" in result


class TestExtractMethod:
    """Tests for the main extract() method."""

    @pytest.fixture
    def extractor(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return KYCExtractor()

    @pytest.fixture
    def complete_extraction_response(self):
        """Complete extraction response fixture."""
        return {
            "client_name": {"first": "Ivan", "middle": None, "last": "Petrov"},
            "address": {
                "street": "123 Main St",
                "city": "Toronto",
                "province": "ON",
                "postal_code": "M5V 1A1"
            },
            "contact": {"email": "ivan@example.com", "phone": "+14165551234"},
            "personal": {"dob": "1985-03-15", "citizenship": "Canada"},
            "employment": {"occupation": "Software Engineer", "employer": "Tech Corp"},
            "financials": {
                "annual_income": 150000,
                "net_financial_assets": 500000,
                "net_worth": 800000,
                "income_stable_2_years": True
            },
            "investment_profile": {
                "risk_tolerance": "MODERATE",
                "time_horizon": "10+",
                "investment_objective": "GROWTH"
            },
            "exemption_status": {
                "is_accredited": False,
                "is_eligible": True,
                "accreditation_reason": None
            },
            "aml": {"is_pep": False, "is_hio": False},
            "confidence_scores": {
                "client_name": "HIGH",
                "financials": "MEDIUM",
                "risk_profile": "HIGH"
            },
            "missing_fields": ["spouse_name", "asset_composition"],
            "ambiguous_items": [],
            "follow_up_questions": []
        }

    @pytest.mark.unit
    async def test_extract_with_language_hint(self, extractor):
        """Test extraction with language hint parameter."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"client_name": {"first": "Test"}}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            await extractor.extract("transcript", source_language="ru")

            # Verify the call was made with correct model
            mock_create.assert_called_once()
            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["model"] == "claude-sonnet-4-20250514"
            assert "ru" in call_kwargs["messages"][0]["content"]

    @pytest.mark.unit
    async def test_extract_with_form_type(self, extractor):
        """Test extraction with form type parameter."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"corporate_name": "Test Corp"}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            await extractor.extract("transcript", form_type="corporate")

            call_kwargs = mock_create.call_args.kwargs
            assert "corporate" in call_kwargs["messages"][0]["content"]

    @pytest.mark.unit
    async def test_extract_complete_response(self, extractor, complete_extraction_response):
        """Test extraction returns complete structured data."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps(complete_extraction_response))]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("Full transcript text here")

        assert result["client_name"]["first"] == "Ivan"
        assert result["financials"]["annual_income"] == 150000
        assert result["investment_profile"]["risk_tolerance"] == "MODERATE"
        assert result["exemption_status"]["is_eligible"] is True

    @pytest.mark.unit
    async def test_extract_uses_system_prompt(self, extractor):
        """Test that extraction uses the defined system prompt."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            await extractor.extract("transcript")

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["system"] == EXTRACTION_PROMPT


class TestQuickExtract:
    """Tests for quick_extract() method."""

    @pytest.fixture
    def extractor(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return KYCExtractor()

    @pytest.mark.unit
    async def test_quick_extract_success(self, extractor):
        """Test quick extraction returns name data."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"first_name": "John", "last_name": "Doe", "missing_fields": []}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.quick_extract("Hello, my name is John Doe")

        assert result["first_name"] == "John"
        assert result["last_name"] == "Doe"

    @pytest.mark.unit
    async def test_quick_extract_missing_name(self, extractor):
        """Test quick extraction when name not found."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"first_name": null, "last_name": null, "missing_fields": ["name"]}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.quick_extract("No name mentioned here")

        assert result["first_name"] is None
        assert result["last_name"] is None

    @pytest.mark.unit
    async def test_quick_extract_invalid_json_fallback(self, extractor):
        """Test quick extraction returns fallback on invalid JSON."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='not valid json')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.quick_extract("Some transcript")

        # Should return fallback structure
        assert result["first_name"] is None
        assert result["last_name"] is None
        assert "name" in result["missing_fields"]

    @pytest.mark.unit
    async def test_quick_extract_uses_shorter_max_tokens(self, extractor):
        """Test quick extraction uses fewer tokens than full extraction."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            await extractor.quick_extract("transcript")

            call_kwargs = mock_create.call_args.kwargs
            assert call_kwargs["max_tokens"] == 200

    @pytest.mark.unit
    async def test_quick_extract_truncates_long_transcript(self, extractor):
        """Test quick extraction truncates very long transcripts."""
        long_transcript = "word " * 5000  # Very long transcript
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='{"first_name": "Test", "last_name": "User", "missing_fields": []}')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            await extractor.quick_extract(long_transcript)

            call_kwargs = mock_create.call_args.kwargs
            # Should only use first 1000 chars of transcript
            assert len(call_kwargs["messages"][0]["content"]) < len(long_transcript)

    @pytest.mark.unit
    async def test_quick_extract_strips_markdown(self, extractor):
        """Test quick extraction strips markdown from response."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text='```json\n{"first_name": "Mary", "last_name": "Jane", "missing_fields": []}\n```')]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.quick_extract("transcript")

        assert result["first_name"] == "Mary"


class TestCyrillicTransliteration:
    """Tests for handling Cyrillic text in responses."""

    @pytest.fixture
    def extractor(self):
        with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}):
            return KYCExtractor()

    @pytest.mark.unit
    async def test_russian_name_transliteration(self, extractor):
        """Test that Russian names are properly transliterated."""
        # Simulating Claude's response after transliteration
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "client_name": {"first": "Ivan", "last": "Petrenko"}
        }))]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("Меня зовут Иван Петренко", source_language="ru")

        # Should receive transliterated name
        assert result["client_name"]["first"] == "Ivan"
        assert result["client_name"]["last"] == "Petrenko"

    @pytest.mark.unit
    async def test_ukrainian_name_transliteration(self, extractor):
        """Test that Ukrainian names are properly transliterated."""
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text=json.dumps({
            "client_name": {"first": "Oleksandr", "last": "Shevchenko"}
        }))]

        with patch.object(extractor.client.messages, "create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_response
            result = await extractor.extract("Мене звати Олександр Шевченко", source_language="uk")

        assert result["client_name"]["first"] == "Oleksandr"
        assert result["client_name"]["last"] == "Shevchenko"
