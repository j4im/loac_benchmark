"""Tests for rule extraction (src/pipeline/extract.py)."""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.pipeline.extract import estimate_cost, extract_rules, validate_verbatim_rules


class TestExtractRules:
    """Test the extract_rules function."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client with realistic response."""
        mock_client = Mock()
        mock_response = Mock()

        # Realistic response structure
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps(
            {
                "rules": [
                    {
                        "rule_text": "Combatants may make enemy combatants the object of attack.",
                        "rule_type": "permission",
                        "summary": "Combatants can target enemy combatants.",
                        "actors": ["combatants"],
                        "conditions": "during armed conflict",
                        "confidence": 95,
                        "footnote_refs": [160],
                    },
                    {
                        "rule_text": "Civilians may not be made the object of attack.",
                        "rule_type": "prohibition",
                        "summary": "Civilians cannot be targeted.",
                        "actors": ["combatants"],
                        "conditions": "during armed conflict",
                        "confidence": 98,
                        "footnote_refs": [160],
                    },
                ]
            }
        )

        # Mock usage for cost tracking
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 500
        mock_response.usage.completion_tokens = 200
        mock_response.usage.total_tokens = 700

        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @pytest.fixture
    def sample_section_data(self):
        """Sample section data for testing."""
        return {
            "title": "DISCRIMINATION IN CONDUCTING ATTACKS",
            "text": "Combatants may make enemy combatants the object of attack. Civilians may not be made the object of attack.",
            "page_numbers": [1, 2],
        }

    def test_extract_rules_returns_list(self, mock_openai_client, sample_section_data):
        """Test that extract_rules returns a list."""
        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5", sample_section_data, mock_openai_client)

            assert isinstance(rules, list)
            assert len(rules) == 2

    def test_extract_rules_calls_openai_with_correct_params(
        self, mock_openai_client, sample_section_data
    ):
        """Test that OpenAI is called with correct parameters."""
        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            extract_rules("5.5", sample_section_data, mock_openai_client)

            # Verify API was called
            assert mock_openai_client.chat.completions.create.called

            # Check call parameters
            call_kwargs = mock_openai_client.chat.completions.create.call_args[1]
            assert call_kwargs["model"] == "gpt-4.1"
            assert call_kwargs["temperature"] == 0.1
            assert call_kwargs["response_format"] == {"type": "json_object"}

    def test_extract_rules_adds_source_metadata(self, mock_openai_client, sample_section_data):
        """Test that source metadata is added to each rule."""
        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5.1", sample_section_data, mock_openai_client)

            for rule in rules:
                assert "source_section" in rule
                assert rule["source_section"] == "5.5.1"
                assert "source_page_numbers" in rule
                assert rule["source_page_numbers"] == [1, 2]

    def test_extract_rules_has_all_required_fields(self, mock_openai_client, sample_section_data):
        """Test that all required fields are present in extracted rules."""
        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5", sample_section_data, mock_openai_client)

            required_fields = [
                "rule_text",
                "rule_type",
                "summary",
                "actors",
                "conditions",
                "confidence",
                "footnote_refs",
                "source_section",
                "source_page_numbers",
            ]

            for rule in rules:
                for field in required_fields:
                    assert field in rule, f"Missing field: {field}"

    def test_extract_rules_uses_cache(self, mock_openai_client, sample_section_data, tmp_path):
        """Test that cached results are used when available."""
        # Create cache directory and file
        cache_dir = tmp_path / "cache" / "rules"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "5.5.json"

        cached_rules = [
            {
                "rule_text": "Cached rule text.",
                "rule_type": "permission",
                "summary": "This is from cache.",
                "actors": ["test"],
                "conditions": "test conditions",
                "confidence": 100,
                "footnote_refs": [1],
            }
        ]

        with open(cache_file, "w") as f:
            json.dump(cached_rules, f)

        # Mock Path to point to our tmp cache
        def mock_path_constructor(path_str):
            if "cache/rules/5.5.json" in str(path_str):
                return cache_file
            return Path(path_str)

        with patch("src.pipeline.extract.Path", side_effect=mock_path_constructor):
            rules = extract_rules("5.5", sample_section_data, mock_openai_client)

            # Should return cached rules
            assert len(rules) == 1
            assert rules[0]["rule_text"] == "Cached rule text."

            # API should NOT be called
            mock_openai_client.chat.completions.create.assert_not_called()

    def test_extract_rules_handles_api_error(self, sample_section_data):
        """Test that API errors are handled gracefully."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API connection failed")

        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5", sample_section_data, mock_client)

            # Should return empty list on error
            assert rules == []

    def test_extract_rules_handles_malformed_json(self, sample_section_data):
        """Test that malformed JSON responses are handled."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "not valid json"
        mock_client.chat.completions.create.return_value = mock_response

        with patch("src.pipeline.extract.Path") as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5", sample_section_data, mock_client)

            # Should return empty list on parse error
            assert rules == []

    def test_extract_rules_caches_results(self, mock_openai_client, sample_section_data):
        """Test that results are cached after extraction."""
        with patch("src.pipeline.extract.Path") as mock_path:
            # First call: cache doesn't exist
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            # Mock the file write
            written_data = None

            def mock_open_write(file_path, mode="r", **kwargs):
                nonlocal written_data
                if "w" in mode:
                    import io

                    buffer = io.StringIO()
                    original_close = buffer.close

                    def custom_close():
                        nonlocal written_data
                        written_data = buffer.getvalue()
                        original_close()

                    buffer.close = custom_close
                    return buffer
                return open(file_path, mode, **kwargs)

            with patch("builtins.open", side_effect=mock_open_write):
                _ = extract_rules("5.5", sample_section_data, mock_openai_client)

                # Verify data was written
                assert written_data is not None
                cached_data = json.loads(written_data)
                assert len(cached_data) == 2


class TestValidateVerbatimRules:
    """Test the validate_verbatim_rules function."""

    def test_validate_accepts_exact_verbatim_text(self):
        """Test that exact verbatim quotes are accepted."""
        source_text = "Combatants may make enemy combatants the object of attack."
        rules = [
            {
                "rule_text": "Combatants may make enemy combatants the object of attack.",
                "rule_type": "permission",
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert "_validation_warning" not in validated[0]

    def test_validate_accepts_substring(self):
        """Test that verbatim substrings are accepted."""
        source_text = "The law states that combatants may make enemy combatants the object of attack. This is important."
        rules = [
            {
                "rule_text": "combatants may make enemy combatants the object of attack.",
                "rule_type": "permission",
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert "_validation_warning" not in validated[0]

    def test_validate_detects_paraphrase(self):
        """Test that paraphrased text is flagged."""
        source_text = "Combatants may make enemy combatants the object of attack."
        rules = [
            {
                "rule_text": "Soldiers can target enemy soldiers.",  # Paraphrased
                "rule_type": "permission",
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert "_validation_warning" in validated[0]
        assert validated[0]["_validation_warning"] == "rule_text not found verbatim in source"

    def test_validate_handles_whitespace_differences(self):
        """Test that whitespace differences are tolerated."""
        source_text = "Combatants   may\n\nmake enemy combatants   the object of attack."
        rules = [
            {
                "rule_text": "Combatants may make enemy combatants the object of attack.",
                "rule_type": "permission",
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert "_validation_warning" not in validated[0]

    def test_validate_handles_multiple_rules(self):
        """Test validation with multiple rules."""
        source_text = "Combatants may attack enemy combatants. Civilians may not be attacked."
        rules = [
            {"rule_text": "Combatants may attack enemy combatants.", "rule_type": "permission"},
            {"rule_text": "Civilians may not be attacked.", "rule_type": "prohibition"},
            {
                "rule_text": "Soldiers can fight.",  # Paraphrase
                "rule_type": "permission",
            },
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 3
        assert "_validation_warning" not in validated[0]
        assert "_validation_warning" not in validated[1]
        assert "_validation_warning" in validated[2]

    def test_validate_handles_empty_rule_text(self):
        """Test validation with empty rule text."""
        source_text = "Some text here."
        rules = [{"rule_text": "", "rule_type": "permission"}]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        # Empty string is technically found in any string, so no warning
        # This edge case is acceptable since LLM should never return empty rule_text
        assert "_validation_warning" not in validated[0]


class TestEstimateCost:
    """Test the estimate_cost function."""

    def test_estimate_cost_calculation(self):
        """Test that cost is calculated correctly."""
        usage = Mock()
        usage.prompt_tokens = 1_000_000  # 1M tokens
        usage.completion_tokens = 1_000_000  # 1M tokens

        cost = estimate_cost(usage)

        # Input: $10/1M * 1M = $10
        # Output: $30/1M * 1M = $30
        # Total: $40
        assert cost == 40.0

    def test_estimate_cost_small_usage(self):
        """Test cost calculation for small token counts."""
        usage = Mock()
        usage.prompt_tokens = 500
        usage.completion_tokens = 200

        cost = estimate_cost(usage)

        # Input: $10/1M * 500 = $0.005
        # Output: $30/1M * 200 = $0.006
        # Total: $0.011
        assert abs(cost - 0.011) < 0.0001

    def test_estimate_cost_zero_tokens(self):
        """Test cost calculation with zero tokens."""
        usage = Mock()
        usage.prompt_tokens = 0
        usage.completion_tokens = 0

        cost = estimate_cost(usage)

        assert cost == 0.0

    def test_estimate_cost_only_input_tokens(self):
        """Test cost calculation with only input tokens."""
        usage = Mock()
        usage.prompt_tokens = 100_000
        usage.completion_tokens = 0

        cost = estimate_cost(usage)

        # Input: $10/1M * 100k = $1.0
        assert cost == 1.0

    def test_estimate_cost_only_output_tokens(self):
        """Test cost calculation with only output tokens."""
        usage = Mock()
        usage.prompt_tokens = 0
        usage.completion_tokens = 100_000

        cost = estimate_cost(usage)

        # Output: $30/1M * 100k = $3.0
        assert cost == 3.0
