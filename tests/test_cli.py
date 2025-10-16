"""Tests for CLI argument parsing and utilities (src/cli/)."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.cli.parser import create_parser, parse_args
from src.cli.utils import (
    filter_sections,
    filter_rules,
    filter_questions,
    clean_cache_by_command,
    should_use_cache,
)
import src.cli.utils as cli_utils


class TestArgumentParsing:
    """Test argument parser for all commands."""

    def test_parser_requires_command(self):
        """Test that parser requires a command."""
        parser = create_parser()
        with pytest.raises(SystemExit):
            parser.parse_args([])

    def test_parser_help_flag(self):
        """Test that --help flag works."""
        parser = create_parser()
        with pytest.raises(SystemExit) as exc_info:
            parser.parse_args(['--help'])
        assert exc_info.value.code == 0

    def test_parse_all_command_basic(self):
        """Test parsing 'all' command with defaults."""
        args = parse_args(['all'])

        assert args.command == 'all'
        assert args.pdf == 'section_5_5.pdf'
        assert args.section is None
        assert args.output_dir == 'data/'
        assert args.resume is False

    def test_parse_all_command_with_options(self):
        """Test parsing 'all' command with options."""
        args = parse_args(['all', '--section', '5.5', '--resume'])

        assert args.command == 'all'
        assert args.section == '5.5'
        assert args.resume is True

    def test_parse_parse_command_requires_pdf(self):
        """Test that 'parse' command requires --pdf."""
        with pytest.raises(SystemExit):
            parse_args(['parse'])

    def test_parse_parse_command_with_pdf(self):
        """Test parsing 'parse' command with PDF."""
        args = parse_args(['parse', '--pdf', 'test.pdf'])

        assert args.command == 'parse'
        assert args.pdf == 'test.pdf'
        assert args.section is None
        assert args.output == 'data/extracted/sections.json'

    def test_parse_parse_command_with_section_filter(self):
        """Test parsing 'parse' command with section filter."""
        args = parse_args(['parse', '--pdf', 'test.pdf', '--section', '5.5.2'])

        assert args.section == '5.5.2'

    def test_parse_rules_command_basic(self):
        """Test parsing 'rules' command with defaults."""
        args = parse_args(['rules'])

        assert args.command == 'rules'
        assert args.input == 'data/extracted/sections.json'
        assert args.section is None
        assert args.output == 'data/extracted/rules.json'

    def test_parse_rules_command_with_section(self):
        """Test parsing 'rules' command with section filter."""
        args = parse_args(['rules', '--section', '5.5'])

        assert args.section == '5.5'

    def test_parse_questions_command_basic(self):
        """Test parsing 'questions' command with defaults."""
        args = parse_args(['questions'])

        assert args.command == 'questions'
        assert args.input == 'data/extracted/rules.json'
        assert args.rule_id is None
        assert args.types is None
        assert args.output == 'data/generated/questions.json'

    def test_parse_questions_command_with_rule_filter(self):
        """Test parsing 'questions' command with rule-id filter."""
        args = parse_args(['questions', '--rule-id', '5.5_r0'])

        assert args.rule_id == '5.5_r0'

    def test_parse_questions_command_with_types(self):
        """Test parsing 'questions' command with question types."""
        args = parse_args(['questions', '--types', 'def,easy'])

        assert args.types == 'def,easy'

    def test_parse_validate_command_basic(self):
        """Test parsing 'validate' command with defaults."""
        args = parse_args(['validate'])

        assert args.command == 'validate'
        assert args.input == 'data/generated/questions.json'
        assert args.question_id is None
        assert args.threshold == 90
        assert args.output == 'data/validated/questions.json'

    def test_parse_validate_command_with_threshold(self):
        """Test parsing 'validate' command with custom threshold."""
        args = parse_args(['validate', '--threshold', '95'])

        assert args.threshold == 95

    def test_parse_validate_command_with_question_filter(self):
        """Test parsing 'validate' command with question filter."""
        args = parse_args(['validate', '--question-id', '*_refusal'])

        assert args.question_id == '*_refusal'

    def test_global_verbose_flag(self):
        """Test global --verbose flag."""
        args = parse_args(['-v', 'validate'])

        assert args.verbose is True
        assert args.command == 'validate'

    def test_global_dry_run_flag(self):
        """Test global --dry-run flag."""
        args = parse_args(['-d', 'questions', '--rule-id', '5.5_r0'])

        assert args.dry_run is True
        assert args.command == 'questions'

    def test_global_clean_cache_flag(self):
        """Test global --clean-cache flag."""
        args = parse_args(['--clean-cache', 'rules', '--section', '5.5'])

        assert args.clean_cache is True
        assert args.section == '5.5'

    def test_global_ignore_cache_flag(self):
        """Test global --ignore-cache flag."""
        args = parse_args(['--ignore-cache', 'validate'])

        assert args.ignore_cache is True

    def test_multiple_global_flags(self):
        """Test multiple global flags together."""
        args = parse_args(['-v', '-d', '--ignore-cache', 'questions'])

        assert args.verbose is True
        assert args.dry_run is True
        assert args.ignore_cache is True


class TestFilteringSections:
    """Test section filtering utility."""

    @pytest.fixture
    def sample_sections(self):
        """Sample sections data."""
        return {
            "5.5": {"title": "Section 5.5", "text": "Content"},
            "5.5.1": {"title": "Section 5.5.1", "text": "Sub content"},
            "5.5.2": {"title": "Section 5.5.2", "text": "Sub content 2"},
            "5.6": {"title": "Section 5.6", "text": "Other content"},
            "5.6.1": {"title": "Section 5.6.1", "text": "Other sub"},
        }

    def test_filter_sections_no_prefix(self, sample_sections):
        """Test filtering with no prefix returns all sections."""
        result = filter_sections(sample_sections, None)

        assert len(result) == 5
        assert result == sample_sections

    def test_filter_sections_with_prefix(self, sample_sections):
        """Test filtering by section prefix."""
        result = filter_sections(sample_sections, "5.5")

        assert len(result) == 3
        assert "5.5" in result
        assert "5.5.1" in result
        assert "5.5.2" in result
        assert "5.6" not in result

    def test_filter_sections_specific_subsection(self, sample_sections):
        """Test filtering by specific subsection."""
        result = filter_sections(sample_sections, "5.5.1")

        assert len(result) == 1
        assert "5.5.1" in result

    def test_filter_sections_no_matches(self, sample_sections):
        """Test filtering with no matches returns empty dict."""
        result = filter_sections(sample_sections, "9.9")

        assert len(result) == 0
        assert result == {}


class TestFilteringRules:
    """Test rule filtering utility."""

    @pytest.fixture
    def sample_rules(self):
        """Sample rules data."""
        return [
            {"rule_id": "5.5_r0", "rule_text": "Rule 0"},
            {"rule_id": "5.5_r1", "rule_text": "Rule 1"},
            {"rule_id": "5.5.1_r0", "rule_text": "Subsection rule"},
            {"rule_id": "5.5.2_r0", "rule_text": "Another subsection"},
            {"rule_id": "5.6_r0", "rule_text": "Different section"},
        ]

    def test_filter_rules_no_pattern(self, sample_rules):
        """Test filtering with no pattern returns all rules."""
        result = filter_rules(sample_rules, None)

        assert len(result) == 5
        assert result == sample_rules

    def test_filter_rules_exact_match(self, sample_rules):
        """Test filtering by exact rule ID."""
        result = filter_rules(sample_rules, "5.5_r0")

        assert len(result) == 1
        assert result[0]["rule_id"] == "5.5_r0"

    def test_filter_rules_wildcard_section(self, sample_rules):
        """Test filtering by section wildcard."""
        result = filter_rules(sample_rules, "5.5_*")

        assert len(result) == 2
        assert result[0]["rule_id"] == "5.5_r0"
        assert result[1]["rule_id"] == "5.5_r1"

    def test_filter_rules_wildcard_subsection(self, sample_rules):
        """Test filtering by subsection wildcard."""
        result = filter_rules(sample_rules, "5.5.2_*")

        assert len(result) == 1
        assert result[0]["rule_id"] == "5.5.2_r0"

    def test_filter_rules_wildcard_rule_index(self, sample_rules):
        """Test filtering by rule index wildcard."""
        result = filter_rules(sample_rules, "*_r0")

        assert len(result) == 4
        # All rules with index 0

    def test_filter_rules_no_matches(self, sample_rules):
        """Test filtering with no matches returns empty list."""
        result = filter_rules(sample_rules, "9.9_*")

        assert len(result) == 0
        assert result == []


class TestFilteringQuestions:
    """Test question filtering utility."""

    @pytest.fixture
    def sample_questions(self):
        """Sample questions data."""
        return [
            {"question_id": "5.5_r0_def", "question_type": "definitional"},
            {"question_id": "5.5_r0_scenario_easy", "question_type": "scenario_easy"},
            {"question_id": "5.5_r0_scenario_hard", "question_type": "scenario_hard"},
            {"question_id": "5.5_r0_refusal", "question_type": "refusal"},
            {"question_id": "5.5_r1_def", "question_type": "definitional"},
            {"question_id": "5.6_r0_refusal", "question_type": "refusal"},
        ]

    def test_filter_questions_no_pattern(self, sample_questions):
        """Test filtering with no pattern returns all questions."""
        result = filter_questions(sample_questions, None)

        assert len(result) == 6
        assert result == sample_questions

    def test_filter_questions_exact_match(self, sample_questions):
        """Test filtering by exact question ID."""
        result = filter_questions(sample_questions, "5.5_r0_def")

        assert len(result) == 1
        assert result[0]["question_id"] == "5.5_r0_def"

    def test_filter_questions_by_rule(self, sample_questions):
        """Test filtering all questions for a rule."""
        result = filter_questions(sample_questions, "5.5_r0_*")

        assert len(result) == 4
        # All questions from rule 5.5_r0

    def test_filter_questions_by_type(self, sample_questions):
        """Test filtering by question type."""
        result = filter_questions(sample_questions, "*_refusal")

        assert len(result) == 2
        assert all(q["question_type"] == "refusal" for q in result)

    def test_filter_questions_by_scenario(self, sample_questions):
        """Test filtering scenario questions."""
        result = filter_questions(sample_questions, "*_scenario_*")

        assert len(result) == 2
        assert result[0]["question_type"] == "scenario_easy"
        assert result[1]["question_type"] == "scenario_hard"

    def test_filter_questions_no_matches(self, sample_questions):
        """Test filtering with no matches returns empty list."""
        result = filter_questions(sample_questions, "9.9_*")

        assert len(result) == 0


class TestCacheManagement:
    """Test cache management utilities."""

    def test_should_use_cache_default(self):
        """Test should_use_cache returns True by default."""
        cli_utils.IGNORE_CACHE = False

        assert should_use_cache() is True

    def test_should_use_cache_when_ignore_flag_set(self):
        """Test should_use_cache returns False when IGNORE_CACHE is True."""
        cli_utils.IGNORE_CACHE = True

        assert should_use_cache() is False

        # Cleanup
        cli_utils.IGNORE_CACHE = False

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_parse(self, mock_clean):
        """Test cleaning cache for 'parse' command."""
        clean_cache_by_command('parse')

        mock_clean.assert_called_once_with('cache/parse')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_rules(self, mock_clean):
        """Test cleaning cache for 'rules' command."""
        clean_cache_by_command('rules')

        mock_clean.assert_called_once_with('cache/rules')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_rules_with_section(self, mock_clean):
        """Test cleaning cache for 'rules' command with section filter."""
        clean_cache_by_command('rules', section='5.5')

        mock_clean.assert_called_once_with('cache/rules', pattern='5.5*')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_questions(self, mock_clean):
        """Test cleaning cache for 'questions' command."""
        clean_cache_by_command('questions')

        mock_clean.assert_called_once_with('cache/questions')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_questions_with_rule_id(self, mock_clean):
        """Test cleaning cache for 'questions' command with rule filter."""
        clean_cache_by_command('questions', rule_id='5.5_r0')

        mock_clean.assert_called_once_with('cache/questions', pattern='5.5_r0*')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_validate(self, mock_clean):
        """Test cleaning cache for 'validate' command."""
        clean_cache_by_command('validate')

        mock_clean.assert_called_once_with('cache/validation')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_validate_with_question_id(self, mock_clean):
        """Test cleaning cache for 'validate' command with question filter."""
        clean_cache_by_command('validate', question_id='*_refusal')

        mock_clean.assert_called_once_with('cache/validation', pattern='*_refusal*')

    @patch('src.cli.utils.clean_cache_dir')
    def test_clean_cache_by_command_all(self, mock_clean):
        """Test cleaning cache for 'all' command cleans all caches."""
        clean_cache_by_command('all')

        # Should call clean_cache_dir 4 times (once for each cache directory)
        assert mock_clean.call_count == 4


class TestUtilityHelpers:
    """Test utility helper functions."""

    def test_log_verbose_when_disabled(self, capsys):
        """Test log_verbose doesn't print when verbose mode disabled."""
        cli_utils.VERBOSE_MODE = False
        cli_utils.DRY_RUN_MODE = False

        cli_utils.log_verbose("Test message")

        captured = capsys.readouterr()
        assert "Test message" not in captured.err

    def test_log_verbose_when_enabled(self, capsys):
        """Test log_verbose prints when verbose mode enabled."""
        cli_utils.VERBOSE_MODE = True

        cli_utils.log_verbose("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.err

        # Cleanup
        cli_utils.VERBOSE_MODE = False

    def test_log_verbose_in_dry_run_mode(self, capsys):
        """Test log_verbose prints in dry-run mode."""
        cli_utils.DRY_RUN_MODE = True

        cli_utils.log_verbose("Test message")

        captured = capsys.readouterr()
        assert "Test message" in captured.err

        # Cleanup
        cli_utils.DRY_RUN_MODE = False

    def test_load_json_file_success(self, tmp_path):
        """Test loading valid JSON file."""
        import json

        test_file = tmp_path / "test.json"
        test_data = {"key": "value"}
        test_file.write_text(json.dumps(test_data))

        result = cli_utils.load_json_file(str(test_file))

        assert result == test_data

    def test_load_json_file_not_found(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            cli_utils.load_json_file("/nonexistent/file.json")

    def test_save_json_file(self, tmp_path):
        """Test saving JSON file."""
        import json

        test_file = tmp_path / "output.json"
        test_data = {"key": "value", "nested": {"data": [1, 2, 3]}}

        cli_utils.save_json_file(test_data, str(test_file))

        assert test_file.exists()
        loaded_data = json.loads(test_file.read_text())
        assert loaded_data == test_data
