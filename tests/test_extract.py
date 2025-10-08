"""Tests for PDF parsing and extraction."""

import pytest
import json
from pathlib import Path
from src.extract import parse_document, _add_hierarchy


class TestParsing:
    """Test PDF parsing functionality."""

    @pytest.fixture
    def pdf_path(self):
        """Path to test PDF."""
        return "data/raw/section_5_5.pdf"

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
        return parse_document("data/raw/section_5_5.pdf")

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
