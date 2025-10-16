"""Tests for PDF parsing and rule extraction."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from src.pipeline.parse import parse_document, _add_hierarchy
from src.pipeline.extract import extract_rules, validate_verbatim_rules
from src.lib.openai_client import get_openai_client


class TestParsing:
    """Test PDF parsing functionality."""

    @pytest.fixture
    def pdf_path(self):
        """Path to test PDF."""
        return "section_5_5.pdf"

    @pytest.fixture
    def parsed_sections(self, pdf_path):
        """Parse PDF once for all tests."""
        return parse_document(pdf_path)

    def test_parse_document_returns_dict(self, parsed_sections):
        """Test that parse_document returns a dictionary."""
        assert isinstance(parsed_sections, dict)
        assert len(parsed_sections) > 0

    def test_sections_have_required_fields(self, parsed_sections):
        """Test that each section has all required fields."""
        required_fields = ['title', 'text', 'page_numbers', 'children']

        for section_id, section_data in parsed_sections.items():
            for field in required_fields:
                assert field in section_data, f"Section {section_id} missing field: {field}"

    def test_section_5_5_exists(self, parsed_sections):
        """Test that main section 5.5 is extracted."""
        assert "5.5" in parsed_sections
        assert "DISCRIMINATION" in parsed_sections["5.5"]["title"]

    def test_subsections_extracted(self, parsed_sections):
        """Test that subsections are extracted."""
        # Should have at least 5.5.1, 5.5.2, 5.5.3
        assert "5.5.1" in parsed_sections
        assert "5.5.2" in parsed_sections
        assert "5.5.3" in parsed_sections

    def test_parent_child_relationships(self, parsed_sections):
        """Test that parent-child relationships are correct."""
        # 5.5 should be parent of 5.5.1, 5.5.2, 5.5.3
        if "5.5" in parsed_sections:
            children = parsed_sections["5.5"]["children"]
            assert "5.5.1" in children or len(children) >= 2

        # 5.5.1 should have 5.5 as parent
        if "5.5.1" in parsed_sections:
            assert parsed_sections["5.5.1"]["parent"] == "5.5"

    def test_page_numbers_are_lists(self, parsed_sections):
        """Test that page numbers are lists of integers."""
        for section_id, section_data in parsed_sections.items():
            assert isinstance(section_data["page_numbers"], list)
            assert all(isinstance(p, int) for p in section_data["page_numbers"])
            assert len(section_data["page_numbers"]) > 0

    def test_text_content_not_empty(self, parsed_sections):
        """Test that sections have non-empty text."""
        for section_id, section_data in parsed_sections.items():
            assert len(section_data["text"]) > 0, f"Section {section_id} has empty text"

    def test_multiline_section_headers(self, parsed_sections):
        """Test that multi-line section headers are properly extracted."""
        # Section 5.4.8.2 has a multi-line title that ends with a period
        if "5.4.8.2" in parsed_sections:
            title = parsed_sections["5.4.8.2"]["title"]
            expected = "AP I Obligation for Combatants to Distinguish Themselves During Attacks"
            assert expected in title, \
                f"Multi-line header not properly extracted. Got: {title}"

        # Section 5.5.1 has a multi-line title
        if "5.5.1" in parsed_sections:
            title = parsed_sections["5.5.1"]["title"]
            expected_full = "Persons, Objects, and Locations That Are Not Protected From Being Made the Object of Attack"
            assert title == expected_full, \
                f"Section 5.5.1 title should be complete. Got: {title}"



class TestHierarchy:
    """Test hierarchy building functions."""

    def test_add_hierarchy_simple(self):
        """Test adding hierarchy to simple sections."""
        sections = {
            "5.5": {"title": "Test", "text": "Content", "page_numbers": [1]},
            "5.5.1": {"title": "Sub", "text": "Subcontent", "page_numbers": [1]},
        }

        result = _add_hierarchy(sections)

        assert result["5.5"]["parent"] == "5"
        assert "5.5.1" in result["5.5"]["children"]
        assert result["5.5.1"]["parent"] == "5.5"
        assert result["5.5.1"]["children"] == []

    def test_add_hierarchy_nested(self):
        """Test adding hierarchy to nested sections."""
        sections = {
            "5.5": {"title": "A", "text": "A", "page_numbers": [1]},
            "5.5.1": {"title": "B", "text": "B", "page_numbers": [1]},
            "5.5.1.1": {"title": "C", "text": "C", "page_numbers": [1]},
        }

        result = _add_hierarchy(sections)

        assert "5.5.1" in result["5.5"]["children"]
        assert "5.5.1.1" in result["5.5.1"]["children"]
        assert result["5.5.1.1"]["parent"] == "5.5.1"


class TestFootnoteExtraction:
    """Test that footnotes are properly separated from main text."""

    @pytest.fixture
    def parsed_sections(self):
        """Parse PDF once for all footnote tests."""
        return parse_document("section_5_5.pdf")

    def test_main_text_does_not_contain_footnote_content(self, parsed_sections):
        """Test that footnote text is not mixed into main section text."""
        # Section 5.5's main text should end before footnote 156
        section_5_5_text = parsed_sections["5.5"]["text"]

        # This footnote content should NOT appear in main text
        footnote_156_snippet = "wearing nothing but a singlet when Italian bombers"

        assert footnote_156_snippet not in section_5_5_text, \
            "Footnote 156 content leaked into main section text"

    def test_main_text_ends_cleanly(self, parsed_sections):
        """Test that main text ends at a complete sentence, not mid-footnote."""
        section_5_5_text = parsed_sections["5.5"]["text"]

        # Should end with something like "...law of war from being made the object of attack."
        # NOT "...law of war from being\nwearing nothing..."

        # Check that text doesn't end with incomplete sentence fragment
        assert not section_5_5_text.strip().endswith("from being"), \
            "Section text appears to be cut off mid-sentence at footnote boundary"

    def test_section_5_5_ends_with_correct_text(self, parsed_sections):
        """Test that section 5.5 ends with proper text, not garbled by footnote removal."""
        section_5_5_text = parsed_sections["5.5"]["text"]

        # The section should end with "from being\nmade the object of attack.162"
        # (with newline because page break, and footnote marker - LLM can handle both)
        # Words should be in correct order: being -> made -> the -> object -> of -> attack
        # NOT: being -> attack -> made -> the -> object -> of (wrong order)

        # Remove newlines to check word order
        normalized = section_5_5_text.replace('\n', ' ')
        assert "being made the object of attack" in normalized, \
            f"Section 5.5 should have correct word order. Actual ending: {section_5_5_text[-100:]}"


class TestOutputFormat:
    """Test that output matches expected JSON structure."""

    def test_output_file_created(self):
        """Test that the extracted JSON file exists."""
        output_path = Path("data/extracted/section_5_5.json")
        assert output_path.exists(), "Extracted JSON file should exist"

    def test_output_file_valid_json(self):
        """Test that the output file is valid JSON."""
        output_path = Path("data/extracted/section_5_5.json")
        with open(output_path, 'r') as f:
            data = json.load(f)

        assert isinstance(data, dict)
        assert len(data) > 0


class TestRuleExtraction:
    """Test rule extraction functionality."""

    @pytest.fixture
    def mock_openai_client(self):
        """Create a mock OpenAI client."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "rules": [
                {
                    "rule_text": "Combatants may make enemy combatants the object of attack.",
                    "rule_type": "permission",
                    "summary": "Combatants can target enemy combatants.",
                    "actors": ["combatants"],
                    "conditions": "during armed conflict",
                    "confidence": 95,
                    "footnote_refs": [160]
                }
            ]
        })
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 100
        mock_response.usage.completion_tokens = 50
        mock_response.usage.total_tokens = 150

        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @pytest.fixture
    def sample_section_data(self):
        """Sample section data for testing."""
        return {
            "title": "Test Section",
            "text": "Combatants may make enemy combatants the object of attack. This is a test.",
            "page_numbers": [1, 2]
        }

    def test_extract_rules_returns_list(self, mock_openai_client, sample_section_data, tmp_path):
        """Test that extract_rules returns a list of rules."""
        # Use tmp_path to avoid caching interference
        with patch('src.pipeline.extract.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("test.section", sample_section_data, mock_openai_client)

            assert isinstance(rules, list)
            assert len(rules) > 0

    def test_extract_rules_has_required_fields(self, mock_openai_client, sample_section_data, tmp_path):
        """Test that extracted rules have all required fields."""
        with patch('src.pipeline.extract.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("test.section", sample_section_data, mock_openai_client)

            required_fields = [
                'rule_text', 'rule_type', 'summary', 'actors',
                'conditions', 'confidence', 'footnote_refs',
                'source_section', 'source_page_numbers'
            ]

            for rule in rules:
                for field in required_fields:
                    assert field in rule, f"Rule missing field: {field}"

    def test_extract_rules_adds_source_metadata(self, mock_openai_client, sample_section_data):
        """Test that source metadata is added to rules."""
        with patch('src.pipeline.extract.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            rules = extract_rules("5.5.1", sample_section_data, mock_openai_client)

            assert rules[0]['source_section'] == "5.5.1"
            assert rules[0]['source_page_numbers'] == [1, 2]

    def test_validate_verbatim_accepts_verbatim_text(self):
        """Test that validate_verbatim_rules accepts verbatim quotes."""
        source_text = "Combatants may make enemy combatants the object of attack. This is law."
        rules = [
            {
                "rule_text": "Combatants may make enemy combatants the object of attack.",
                "rule_type": "permission"
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert '_validation_warning' not in validated[0]

    def test_validate_verbatim_detects_non_verbatim(self):
        """Test that validate_verbatim_rules detects non-verbatim text."""
        source_text = "Combatants may make enemy combatants the object of attack."
        rules = [
            {
                "rule_text": "Soldiers can target enemy soldiers.",  # Paraphrased!
                "rule_type": "permission"
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert '_validation_warning' in validated[0]
        assert validated[0]['_validation_warning'] == 'rule_text not found verbatim in source'

    def test_validate_verbatim_handles_whitespace_differences(self):
        """Test that validation allows minor whitespace differences."""
        source_text = "Combatants   may\nmake enemy combatants the object of attack."
        rules = [
            {
                "rule_text": "Combatants may make enemy combatants the object of attack.",
                "rule_type": "permission"
            }
        ]

        validated = validate_verbatim_rules(rules, source_text)

        assert len(validated) == 1
        assert '_validation_warning' not in validated[0]

    def test_extract_rules_handles_api_error(self, sample_section_data):
        """Test that extract_rules handles API errors gracefully."""
        mock_client = Mock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")

        rules = extract_rules("test.section", sample_section_data, mock_client)

        # Should return empty list on error
        assert isinstance(rules, list)
        assert len(rules) == 0

    def test_extract_rules_uses_cache(self, mock_openai_client, sample_section_data, tmp_path):
        """Test that extract_rules uses cached results."""
        # Create actual cache file in tmp directory
        cache_dir = tmp_path / "cache" / "rules"
        cache_dir.mkdir(parents=True)
        cache_file = cache_dir / "test.section.json"

        cached_rules = [{"rule_text": "Cached rule", "rule_type": "permission"}]
        with open(cache_file, 'w') as f:
            json.dump(cached_rules, f)

        # Mock Path to point to our tmp cache file
        def mock_path_constructor(path_str):
            if "cache/rules/test.section.json" in str(path_str):
                return cache_file
            return Path(path_str)

        with patch('src.pipeline.extract.Path', side_effect=mock_path_constructor):
            rules = extract_rules("test.section", sample_section_data, mock_openai_client)

            # Should get cached rules
            assert len(rules) == 1
            assert rules[0]['rule_text'] == "Cached rule"

            # API should NOT be called
            mock_openai_client.chat.completions.create.assert_not_called()
