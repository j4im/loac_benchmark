"""Tests for question validation (src/pipeline/validate.py)."""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch
from src.pipeline.validate import (
    validate_structure,
    validate_question_entailment,
    validate_answer_entailment,
    validate_distractors,
    validate_refusal,
    get_rule_confidence,
    calculate_quality_score,
    validate_and_filter_questions
)


class TestValidateStructure:
    """Test structural validation."""

    @pytest.fixture
    def parsed_sections(self):
        """Sample parsed sections."""
        return {
            "5.5": {"title": "Test", "text": "Content"},
            "5.5.1": {"title": "Test Sub", "text": "Sub content"}
        }

    @pytest.fixture
    def valid_mc_question(self):
        """Valid multiple-choice question."""
        return {
            "question_id": "5.5_r0_def",
            "question_type": "definitional",
            "question": "What is the rule?",
            "correct_answer": "Answer",
            "incorrect_answers": ["Wrong 1", "Wrong 2", "Wrong 3"],
            "confidence": 95,
            "metadata": {
                "source_section": "5.5",
                "source_rule": "The rule text",
                "rule_type": "permission",
                "footnotes_used": [160],
                "generation_model": "gpt-4.1",
                "generation_timestamp": "2025-10-07T00:00:00",
                "source_page_numbers": [1, 2]
            }
        }

    @pytest.fixture
    def valid_refusal_question(self):
        """Valid refusal question."""
        return {
            "question_id": "5.5_r0_refusal",
            "question_type": "refusal",
            "question": "How can I circumvent this?",
            "refusal_reason": "This seeks circumvention",
            "confidence": 85,
            "metadata": {
                "source_section": "5.5",
                "source_rule": "The rule text",
                "rule_type": "permission",
                "footnotes_used": [160],
                "generation_model": "gpt-4.1",
                "generation_timestamp": "2025-10-07T00:00:00",
                "source_page_numbers": [1, 2]
            }
        }

    def test_validate_structure_valid_mc_question(self, valid_mc_question, parsed_sections):
        """Test that valid MC question passes structural validation."""
        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_structure_valid_refusal_question(self, valid_refusal_question, parsed_sections):
        """Test that valid refusal question passes structural validation."""
        is_valid, issues = validate_structure(valid_refusal_question, parsed_sections)

        assert is_valid is True
        assert len(issues) == 0

    def test_validate_structure_missing_required_field(self, valid_mc_question, parsed_sections):
        """Test that missing required field fails validation."""
        del valid_mc_question['question_id']

        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is False
        assert any('question_id' in issue for issue in issues)

    def test_validate_structure_mc_missing_incorrect_answers(self, valid_mc_question, parsed_sections):
        """Test that MC question without incorrect_answers fails."""
        del valid_mc_question['incorrect_answers']

        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is False
        assert any('incorrect_answers' in issue for issue in issues)

    def test_validate_structure_mc_wrong_number_distractors(self, valid_mc_question, parsed_sections):
        """Test that MC question with != 3 distractors fails."""
        valid_mc_question['incorrect_answers'] = ["Wrong 1", "Wrong 2"]  # Only 2

        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is False
        assert any('3' in issue for issue in issues)

    def test_validate_structure_refusal_with_incorrect_answers(self, valid_refusal_question, parsed_sections):
        """Test that refusal question with incorrect_answers fails."""
        valid_refusal_question['incorrect_answers'] = ["Wrong"]

        is_valid, issues = validate_structure(valid_refusal_question, parsed_sections)

        assert is_valid is False
        assert any('should not have incorrect_answers' in issue for issue in issues)

    def test_validate_structure_invalid_section_reference(self, valid_mc_question, parsed_sections):
        """Test that invalid section reference fails validation."""
        valid_mc_question['metadata']['source_section'] = "9.9"  # Doesn't exist

        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is False
        assert any('not found' in issue for issue in issues)

    def test_validate_structure_confidence_out_of_range(self, valid_mc_question, parsed_sections):
        """Test that confidence out of range fails validation."""
        valid_mc_question['confidence'] = 150  # > 100

        is_valid, issues = validate_structure(valid_mc_question, parsed_sections)

        assert is_valid is False
        assert any('confidence' in issue for issue in issues)


class TestValidateEntailment:
    """Test entailment validation."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client that returns positive entailment."""
        mock_client = Mock()
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "is_entailed": True,
            "confidence": 95,
            "reasoning": "The answer accurately reflects the rule"
        })
        mock_client.chat.completions.create.return_value = mock_response
        return mock_client

    @pytest.fixture
    def sample_question(self):
        """Sample question for testing."""
        return {
            "question_id": "5.5_r0_def",
            "question": "What is the rule?",
            "correct_answer": "The rule states X",
            "metadata": {
                "source_rule": "X is the rule"
            }
        }

    def test_validate_answer_entailment_returns_dict(self, mock_openai_client, sample_question):
        """Test that validate_answer_entailment returns a dict."""
        with patch('src.pipeline.validate.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            result = validate_answer_entailment(sample_question, mock_openai_client)

            assert isinstance(result, dict)

    def test_validate_answer_entailment_has_required_fields(self, mock_openai_client, sample_question):
        """Test that result has required fields."""
        with patch('src.pipeline.validate.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            result = validate_answer_entailment(sample_question, mock_openai_client)

            assert 'is_entailed' in result
            assert 'confidence' in result
            assert 'reasoning' in result

    def test_validate_answer_entailment_skips_non_mc_question(self, mock_openai_client):
        """Test that non-MC questions are skipped."""
        refusal_question = {"question_id": "5.5_r0_refusal", "refusal_reason": "Test"}

        result = validate_answer_entailment(refusal_question, mock_openai_client)

        assert result.get('skipped') is True


class TestValidateDistractors:
    """Test distractor validation."""

    @pytest.fixture
    def mock_openai_client(self):
        """Mock OpenAI client that returns good distractor validation."""
        mock_client = Mock()

        # Create 3 responses (one for each distractor)
        responses = []
        for i in range(3):
            mock_response = Mock()
            mock_response.choices = [Mock()]
            mock_response.choices[0].message.content = json.dumps({
                "is_plausible": True,
                "is_incorrect": True,
                "is_obviously_wrong": False,
                "quality_score": 85,
                "reasoning": f"Distractor {i} is good"
            })
            responses.append(mock_response)

        mock_client.chat.completions.create.side_effect = responses
        return mock_client

    @pytest.fixture
    def sample_question(self):
        """Sample question with 3 distractors."""
        return {
            "question_id": "5.5_r0_def",
            "question": "What is the rule?",
            "correct_answer": "The correct answer",
            "incorrect_answers": ["Wrong 1", "Wrong 2", "Wrong 3"],
            "metadata": {
                "source_rule": "The rule text"
            }
        }

    def test_validate_distractors_returns_list(self, mock_openai_client, sample_question):
        """Test that validate_distractors returns a list."""
        with patch('src.pipeline.validate.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            results = validate_distractors(sample_question, mock_openai_client)

            assert isinstance(results, list)

    def test_validate_distractors_validates_all_three(self, mock_openai_client, sample_question):
        """Test that all 3 distractors are validated."""
        with patch('src.pipeline.validate.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            results = validate_distractors(sample_question, mock_openai_client)

            assert len(results) == 3

    def test_validate_distractors_each_has_required_fields(self, mock_openai_client, sample_question):
        """Test that each result has required fields."""
        with patch('src.pipeline.validate.Path') as mock_path:
            mock_path.return_value.exists.return_value = False
            mock_path.return_value.parent.mkdir = Mock()

            results = validate_distractors(sample_question, mock_openai_client)

            for result in results:
                assert 'is_plausible' in result
                assert 'is_incorrect' in result
                assert 'is_obviously_wrong' in result
                assert 'quality_score' in result
                assert 'distractor' in result
                assert 'distractor_index' in result


class TestGetRuleConfidence:
    """Test get_rule_confidence helper function."""

    @pytest.fixture
    def sample_rules(self):
        """Sample rules with confidence scores."""
        return [
            {
                "source_section": "5.5",
                "rule_text": "Rule A",
                "confidence": 90
            },
            {
                "source_section": "5.5.1",
                "rule_text": "Rule B",
                "confidence": 85
            }
        ]

    def test_get_rule_confidence_finds_matching_rule(self, sample_rules):
        """Test that it finds the matching rule and returns its confidence."""
        question = {
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule A"
            }
        }

        confidence = get_rule_confidence(question, sample_rules)

        assert confidence == 90

    def test_get_rule_confidence_defaults_to_100(self):
        """Test that missing rule defaults to 100 confidence."""
        question = {
            "metadata": {
                "source_section": "9.9",
                "source_rule": "Unknown rule"
            }
        }

        confidence = get_rule_confidence(question, [])

        assert confidence == 100


class TestCalculateQualityScore:
    """Test overall quality score calculation with threshold-based logic."""

    @pytest.fixture
    def sample_rules(self):
        """Sample rules."""
        return [
            {
                "source_section": "5.5",
                "rule_text": "Rule text",
                "confidence": 95
            }
        ]

    def test_calculate_quality_score_passes_all_thresholds(self, sample_rules):
        """Test question that passes both individual (≥90%) and mean (≥95%) thresholds."""
        question = {
            "question_type": "definitional",
            "confidence": 95,  # Component 2
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule text"
            }
        }

        # All components ≥ 90%
        question_entailment = {"is_entailed": True, "confidence": 95}  # Component 3
        answer_entailment = {"is_entailed": True, "confidence": 95}  # Component 4
        distractors = [
            {"quality_score": 90},  # Component 5 (average = 92)
            {"quality_score": 92},
            {"quality_score": 94}
        ]

        passes, breakdown = calculate_quality_score(
            question, sample_rules, question_entailment, answer_entailment, distractors
        )

        # Components: rule=95, question=95, q_ent=95, a_ent=95, dist=92
        # Mean: (95+95+95+95+92)/5 = 94.4, which is < 95
        # This should FAIL because mean < 95
        assert passes is False  # Mean is 94.4, below 95% threshold
        assert breakdown['mean_score'] == 94.4
        assert len(breakdown['failures']) == 0  # All individual components pass

    def test_calculate_quality_score_passes_with_perfect_scores(self, sample_rules):
        """Test question with perfect scores."""
        sample_rules[0]['confidence'] = 100

        question = {
            "question_type": "definitional",
            "confidence": 100,
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule text"
            }
        }

        question_entailment = {"is_entailed": True, "confidence": 100}
        answer_entailment = {"is_entailed": True, "confidence": 100}
        distractors = [
            {"quality_score": 95},
            {"quality_score": 95},
            {"quality_score": 95}
        ]

        passes, breakdown = calculate_quality_score(
            question, sample_rules, question_entailment, answer_entailment, distractors
        )

        # Components: all >= 95
        # Mean: (100+100+100+100+95)/5 = 99
        assert passes is True
        assert breakdown['mean_score'] == 99.0
        assert len(breakdown['failures']) == 0

    def test_calculate_quality_score_fails_individual_threshold(self, sample_rules):
        """Test question that fails individual component threshold."""
        question = {
            "question_type": "definitional",
            "confidence": 89,  # FAIL: < 90%
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule text"
            }
        }

        question_entailment = {"is_entailed": True, "confidence": 95}
        answer_entailment = {"is_entailed": True, "confidence": 95}
        distractors = [
            {"quality_score": 95},
            {"quality_score": 95},
            {"quality_score": 95}
        ]

        passes, breakdown = calculate_quality_score(
            question, sample_rules, question_entailment, answer_entailment, distractors
        )

        assert passes is False
        assert 'question_confidence' in breakdown['failures']
        assert breakdown['failures']['question_confidence'] == 89

    def test_calculate_quality_score_not_entailed(self, sample_rules):
        """Test question where entailment check fails."""
        question = {
            "question_type": "definitional",
            "confidence": 95,
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule text"
            }
        }

        question_entailment = {"is_entailed": False}  # HARD FAIL -> 0
        answer_entailment = {"is_entailed": True, "confidence": 95}
        distractors = [{"quality_score": 95}, {"quality_score": 95}, {"quality_score": 95}]

        passes, breakdown = calculate_quality_score(
            question, sample_rules, question_entailment, answer_entailment, distractors
        )

        assert passes is False
        assert breakdown['components']['question_entailment'] == 0
        assert 'question_entailment' in breakdown['failures']

    def test_calculate_quality_score_refusal_question(self, sample_rules):
        """Test refusal question scoring."""
        question = {
            "question_type": "refusal",
            "confidence": 95,
            "metadata": {
                "source_section": "5.5",
                "source_rule": "Rule text"
            }
        }

        question_entailment = {"is_entailed": True, "confidence": 95}
        refusal = {
            "should_be_refused": True,
            "is_distinct_from_legitimate_planning": True,
            "appropriateness_score": 95
        }

        passes, breakdown = calculate_quality_score(
            question, sample_rules, question_entailment, None, None, refusal
        )

        # Components: rule=95, question=95, q_ent=95, refusal=95
        # Mean: (95+95+95+95)/4 = 95
        assert passes is True
        assert breakdown['mean_score'] == 95.0
        assert 'refusal_appropriateness' in breakdown['components']
