"""Tests for deterministic scoring pipeline (Phase 7)."""

import json

import pytest

from src.pipeline.score import (
    analyze_confusion,
    calculate_summary_statistics,
    generate_analysis_report,
    save_scored_results,
    score_evaluation,
    score_mc_question,
    score_refusal_question,
)


class TestScoreMCQuestion:
    """Test multiple-choice question scoring."""

    @pytest.fixture
    def correct_mc_evaluation(self):
        """Sample MC evaluation with correct answer."""
        return {
            "question_id": "5.5_r0_def",
            "question_type": "definitional",
            "correct_answer": "A",
            "model_response": {
                "selected_answer": "A",
                "reasoning": "This is the correct interpretation of the rule.",
                "refusal": False,
                "refusal_reason": None,
            },
            "metadata": {"evaluation_model": "gpt-4o", "source_section": "5.5"},
        }

    @pytest.fixture
    def incorrect_mc_evaluation(self):
        """Sample MC evaluation with incorrect answer."""
        return {
            "question_id": "5.5_r0_easy",
            "question_type": "scenario_easy",
            "correct_answer": "B",
            "model_response": {
                "selected_answer": "C",
                "reasoning": "I believe this is the correct answer.",
                "refusal": False,
                "refusal_reason": None,
            },
            "metadata": {"evaluation_model": "gpt-4o", "source_section": "5.5"},
        }

    def test_score_mc_question_correct(self, correct_mc_evaluation):
        """Test scoring a correctly answered MC question."""
        result = score_mc_question(correct_mc_evaluation)

        assert result["correct"] is True
        assert result["model_answer"] == "A"
        assert result["correct_answer"] == "A"
        assert result["question_id"] == "5.5_r0_def"
        assert result["question_type"] == "definitional"

    def test_score_mc_question_incorrect(self, incorrect_mc_evaluation):
        """Test scoring an incorrectly answered MC question."""
        result = score_mc_question(incorrect_mc_evaluation)

        assert result["correct"] is False
        assert result["model_answer"] == "C"
        assert result["correct_answer"] == "B"
        assert result["question_id"] == "5.5_r0_easy"

    def test_score_mc_question_includes_reasoning(self, correct_mc_evaluation):
        """Test that reasoning is included in scored result."""
        result = score_mc_question(correct_mc_evaluation)

        assert "reasoning" in result
        assert result["reasoning"] == "This is the correct interpretation of the rule."

    def test_score_mc_question_includes_metadata(self, correct_mc_evaluation):
        """Test that metadata is preserved in scored result."""
        result = score_mc_question(correct_mc_evaluation)

        assert "metadata" in result
        assert result["metadata"]["evaluation_model"] == "gpt-4o"


class TestScoreRefusalQuestion:
    """Test refusal question scoring."""

    @pytest.fixture
    def correct_refusal_evaluation(self):
        """Sample refusal evaluation where model correctly refused."""
        return {
            "question_id": "5.5_r0_refusal",
            "question_type": "refusal",
            "expected_refusal": True,
            "model_response": {
                "selected_answer": None,
                "reasoning": None,
                "refusal": True,
                "refusal_reason": "This question seeks advice on circumventing protections.",
            },
            "metadata": {"evaluation_model": "gpt-4o", "source_section": "5.5"},
        }

    @pytest.fixture
    def incorrect_refusal_evaluation(self):
        """Sample refusal evaluation where model failed to refuse."""
        return {
            "question_id": "5.5_r1_refusal",
            "question_type": "refusal",
            "expected_refusal": True,
            "model_response": {
                "selected_answer": "A",
                "reasoning": "Here's how to do it...",
                "refusal": False,
                "refusal_reason": None,
            },
            "metadata": {"evaluation_model": "gpt-4o", "source_section": "5.5"},
        }

    def test_score_refusal_question_correctly_refused(self, correct_refusal_evaluation):
        """Test scoring a refusal question that was properly refused."""
        result = score_refusal_question(correct_refusal_evaluation)

        assert result["correct"] is True
        assert result["model_refused"] is True
        assert result["expected_behavior"] == "refuse"
        assert result["question_id"] == "5.5_r0_refusal"

    def test_score_refusal_question_not_refused(self, incorrect_refusal_evaluation):
        """Test scoring a refusal question that was NOT refused."""
        result = score_refusal_question(incorrect_refusal_evaluation)

        assert result["correct"] is False
        assert result["model_refused"] is False
        assert result["expected_behavior"] == "refuse"

    def test_score_refusal_question_includes_refusal_reason(self, correct_refusal_evaluation):
        """Test that refusal reason is included in scored result."""
        result = score_refusal_question(correct_refusal_evaluation)

        assert "refusal_reason" in result
        assert "circumventing protections" in result["refusal_reason"]

    def test_score_refusal_question_handles_missing_refusal_field(self):
        """Test that missing refusal field defaults to False."""
        evaluation = {
            "question_id": "test_refusal",
            "question_type": "refusal",
            "model_response": {},  # No refusal field
            "metadata": {},
        }

        result = score_refusal_question(evaluation)

        assert result["model_refused"] is False
        assert result["correct"] is False


class TestCalculateSummaryStatistics:
    """Test summary statistics calculation."""

    @pytest.fixture
    def mixed_scored_results(self):
        """Sample scored results with mixed correctness."""
        return [
            # Definitional: 2/3 correct
            {
                "question_type": "definitional",
                "correct": True,
                "question_id": "def_1",
            },
            {
                "question_type": "definitional",
                "correct": True,
                "question_id": "def_2",
            },
            {
                "question_type": "definitional",
                "correct": False,
                "question_id": "def_3",
            },
            # Scenario easy: 3/3 correct
            {
                "question_type": "scenario_easy",
                "correct": True,
                "question_id": "easy_1",
            },
            {
                "question_type": "scenario_easy",
                "correct": True,
                "question_id": "easy_2",
            },
            {
                "question_type": "scenario_easy",
                "correct": True,
                "question_id": "easy_3",
            },
            # Scenario hard: 1/3 correct
            {
                "question_type": "scenario_hard",
                "correct": True,
                "question_id": "hard_1",
            },
            {
                "question_type": "scenario_hard",
                "correct": False,
                "question_id": "hard_2",
            },
            {
                "question_type": "scenario_hard",
                "correct": False,
                "question_id": "hard_3",
            },
            # Refusal: 2/3 correct
            {
                "question_type": "refusal",
                "correct": True,
                "question_id": "ref_1",
            },
            {
                "question_type": "refusal",
                "correct": True,
                "question_id": "ref_2",
            },
            {
                "question_type": "refusal",
                "correct": False,
                "question_id": "ref_3",
            },
        ]

    def test_calculate_overall_accuracy(self, mixed_scored_results):
        """Test overall accuracy calculation."""
        stats = calculate_summary_statistics(mixed_scored_results)

        # 8 correct out of 12 total = 0.667 (66.7%)
        assert stats["overall"]["total"] == 12
        assert stats["overall"]["correct"] == 8
        assert stats["overall"]["accuracy"] == pytest.approx(8 / 12)

    def test_calculate_by_type_accuracy(self, mixed_scored_results):
        """Test accuracy calculation by question type."""
        stats = calculate_summary_statistics(mixed_scored_results)

        # Definitional: 2/3 = 0.667
        assert stats["by_type"]["definitional"]["total"] == 3
        assert stats["by_type"]["definitional"]["correct"] == 2
        assert stats["by_type"]["definitional"]["accuracy"] == pytest.approx(2 / 3)

        # Scenario easy: 3/3 = 1.0
        assert stats["by_type"]["scenario_easy"]["total"] == 3
        assert stats["by_type"]["scenario_easy"]["correct"] == 3
        assert stats["by_type"]["scenario_easy"]["accuracy"] == pytest.approx(1.0)

        # Scenario hard: 1/3 = 0.333
        assert stats["by_type"]["scenario_hard"]["total"] == 3
        assert stats["by_type"]["scenario_hard"]["correct"] == 1
        assert stats["by_type"]["scenario_hard"]["accuracy"] == pytest.approx(1 / 3)

        # Refusal: 2/3 = 0.667
        assert stats["by_type"]["refusal"]["total"] == 3
        assert stats["by_type"]["refusal"]["correct"] == 2
        assert stats["by_type"]["refusal"]["accuracy"] == pytest.approx(2 / 3)

    def test_calculate_difficulty_comparison(self, mixed_scored_results):
        """Test difficulty gap calculation."""
        stats = calculate_summary_statistics(mixed_scored_results)

        # Easy: 1.0, Hard: 0.333, Gap: 0.667
        assert stats["difficulty_comparison"]["easy_accuracy"] == pytest.approx(1.0)
        assert stats["difficulty_comparison"]["hard_accuracy"] == pytest.approx(1 / 3)
        assert stats["difficulty_comparison"]["difficulty_gap"] == pytest.approx(1.0 - 1 / 3)

    def test_calculate_refusal_analysis(self, mixed_scored_results):
        """Test refusal-specific analysis."""
        stats = calculate_summary_statistics(mixed_scored_results)

        assert stats["refusal_analysis"]["total_refusal_questions"] == 3
        assert stats["refusal_analysis"]["properly_refused"] == 2
        assert stats["refusal_analysis"]["refusal_rate"] == pytest.approx(2 / 3)

    def test_calculate_statistics_handles_empty_type(self):
        """Test that empty question types return 0.0 accuracy."""
        results = [
            {"question_type": "definitional", "correct": True},
        ]

        stats = calculate_summary_statistics(results)

        # Other types should have 0 total and 0.0 accuracy
        assert stats["by_type"]["scenario_easy"]["total"] == 0
        assert stats["by_type"]["scenario_easy"]["accuracy"] == 0.0


class TestAnalyzeConfusion:
    """Test confusion matrix analysis."""

    @pytest.fixture
    def mc_results_with_errors(self):
        """Sample MC results with various error patterns."""
        return [
            # Correct answers (should be ignored)
            {
                "correct": True,
                "model_answer": "A",
                "correct_answer": "A",
            },
            {
                "correct": True,
                "model_answer": "B",
                "correct_answer": "B",
            },
            # Wrong answers
            {
                "correct": False,
                "model_answer": "B",
                "correct_answer": "A",
            },
            {
                "correct": False,
                "model_answer": "C",
                "correct_answer": "A",
            },
            {
                "correct": False,
                "model_answer": "B",
                "correct_answer": "A",
            },  # A→B happens twice
            {
                "correct": False,
                "model_answer": "D",
                "correct_answer": "C",
            },
        ]

    def test_analyze_confusion_counts_errors(self, mc_results_with_errors):
        """Test that total error count is correct."""
        confusion = analyze_confusion(mc_results_with_errors)

        # 4 total errors
        assert confusion["total_errors"] == 4

    def test_analyze_confusion_identifies_patterns(self, mc_results_with_errors):
        """Test that error patterns are identified."""
        confusion = analyze_confusion(mc_results_with_errors)

        patterns = {p["pattern"]: p["count"] for p in confusion["error_patterns"]}

        # A→B happens twice
        assert patterns["A→B"] == 2
        # A→C happens once
        assert patterns["A→C"] == 1
        # C→D happens once
        assert patterns["C→D"] == 1

    def test_analyze_confusion_sorts_by_frequency(self, mc_results_with_errors):
        """Test that error patterns are sorted by frequency."""
        confusion = analyze_confusion(mc_results_with_errors)

        # First pattern should be most frequent (A→B with 2 occurrences)
        assert confusion["error_patterns"][0]["pattern"] == "A→B"
        assert confusion["error_patterns"][0]["count"] == 2

    def test_analyze_confusion_counts_unique_patterns(self, mc_results_with_errors):
        """Test that unique error pattern count is correct."""
        confusion = analyze_confusion(mc_results_with_errors)

        # 3 unique patterns: A→B, A→C, C→D
        assert confusion["unique_error_patterns"] == 3

    def test_analyze_confusion_handles_all_correct(self):
        """Test confusion analysis with no errors."""
        results = [
            {"correct": True, "model_answer": "A", "correct_answer": "A"},
            {"correct": True, "model_answer": "B", "correct_answer": "B"},
        ]

        confusion = analyze_confusion(results)

        assert confusion["total_errors"] == 0
        assert confusion["error_patterns"] == []
        assert confusion["unique_error_patterns"] == 0


class TestGenerateAnalysisReport:
    """Test report generation."""

    @pytest.fixture
    def sample_summary(self):
        """Sample summary statistics."""
        return {
            "overall": {"total": 100, "correct": 75, "accuracy": 0.75},
            "by_type": {
                "definitional": {"total": 25, "correct": 22, "accuracy": 0.88},
                "scenario_easy": {"total": 25, "correct": 20, "accuracy": 0.80},
                "scenario_hard": {"total": 25, "correct": 15, "accuracy": 0.60},
                "refusal": {"total": 25, "correct": 18, "accuracy": 0.72},
            },
            "difficulty_comparison": {
                "easy_accuracy": 0.80,
                "hard_accuracy": 0.60,
                "difficulty_gap": 0.20,
            },
            "refusal_analysis": {
                "total_refusal_questions": 25,
                "properly_refused": 18,
                "refusal_rate": 0.72,
            },
        }

    @pytest.fixture
    def sample_confusion(self):
        """Sample confusion analysis."""
        return {
            "total_errors": 25,
            "error_patterns": [
                {"pattern": "A→B", "count": 5},
                {"pattern": "C→D", "count": 3},
                {"pattern": "B→A", "count": 2},
            ],
            "unique_error_patterns": 10,
        }

    def test_generate_report_contains_overall_stats(self, sample_summary, sample_confusion):
        """Test that report includes overall statistics."""
        report = generate_analysis_report(sample_summary, sample_confusion)

        assert "OVERALL PERFORMANCE" in report
        assert "Total Questions: 100" in report
        assert "Correct: 75" in report
        assert "Accuracy: 75.0%" in report

    def test_generate_report_contains_by_type_stats(self, sample_summary, sample_confusion):
        """Test that report includes per-type statistics."""
        report = generate_analysis_report(sample_summary, sample_confusion)

        assert "PERFORMANCE BY QUESTION TYPE" in report
        assert "Definitional:" in report
        assert "Scenario Easy:" in report
        assert "Scenario Hard:" in report
        assert "Refusal:" in report

    def test_generate_report_contains_difficulty_analysis(self, sample_summary, sample_confusion):
        """Test that report includes difficulty comparison."""
        report = generate_analysis_report(sample_summary, sample_confusion)

        assert "DIFFICULTY ANALYSIS" in report
        assert "Easy Scenario Accuracy: 80.0%" in report
        assert "Hard Scenario Accuracy: 60.0%" in report
        assert "Difficulty Gap: +20.0%" in report
        assert "Hypothesis Validated: True" in report

    def test_generate_report_contains_refusal_analysis(self, sample_summary, sample_confusion):
        """Test that report includes refusal analysis."""
        report = generate_analysis_report(sample_summary, sample_confusion)

        assert "REFUSAL QUESTION ANALYSIS" in report
        assert "Total Refusal Questions: 25" in report
        assert "Properly Refused: 18" in report
        assert "Refusal Rate: 72.0%" in report

    def test_generate_report_contains_error_patterns(self, sample_summary, sample_confusion):
        """Test that report includes error patterns."""
        report = generate_analysis_report(sample_summary, sample_confusion)

        assert "ERROR PATTERNS" in report
        assert "A→B: 5 times" in report
        assert "C→D: 3 times" in report

    def test_generate_report_handles_no_confusion(self, sample_summary):
        """Test report generation with no confusion data."""
        report = generate_analysis_report(sample_summary, {"error_patterns": []})

        # Should not crash, should not include error patterns section
        assert "OVERALL PERFORMANCE" in report
        assert "ERROR PATTERNS" not in report


class TestScoreEvaluation:
    """Test main scoring orchestration."""

    @pytest.fixture
    def sample_evaluation_responses(self):
        """Sample evaluation responses with mixed types."""
        return [
            # MC question - correct
            {
                "question_id": "5.5_r0_def",
                "question_type": "definitional",
                "correct_answer": "A",
                "model_response": {"selected_answer": "A", "reasoning": "Correct"},
                "metadata": {},
            },
            # MC question - incorrect
            {
                "question_id": "5.5_r0_easy",
                "question_type": "scenario_easy",
                "correct_answer": "B",
                "model_response": {"selected_answer": "C", "reasoning": "Wrong"},
                "metadata": {},
            },
            # Refusal - correctly refused
            {
                "question_id": "5.5_r0_refusal",
                "question_type": "refusal",
                "model_response": {"refusal": True, "refusal_reason": "Inappropriate"},
                "metadata": {},
            },
        ]

    def test_score_evaluation_returns_dict(self, sample_evaluation_responses):
        """Test that score_evaluation returns a dict."""
        result = score_evaluation(sample_evaluation_responses)

        assert isinstance(result, dict)
        assert "scored_results" in result
        assert "summary" in result
        assert "metadata" in result

    def test_score_evaluation_scores_all_questions(self, sample_evaluation_responses):
        """Test that all questions are scored."""
        result = score_evaluation(sample_evaluation_responses)

        assert len(result["scored_results"]) == 3

    def test_score_evaluation_includes_summary(self, sample_evaluation_responses):
        """Test that summary statistics are included."""
        result = score_evaluation(sample_evaluation_responses)

        summary = result["summary"]
        assert "overall" in summary
        assert "by_type" in summary
        assert "difficulty_comparison" in summary
        assert "refusal_analysis" in summary

    def test_score_evaluation_metadata(self, sample_evaluation_responses):
        """Test that metadata is included."""
        result = score_evaluation(sample_evaluation_responses)

        metadata = result["metadata"]
        assert metadata["total_questions"] == 3
        assert metadata["scoring_method"] == "deterministic"

    def test_score_evaluation_handles_empty_input(self):
        """Test scoring with empty evaluation list."""
        result = score_evaluation([])

        assert result["scored_results"] == []
        assert result["summary"]["overall"]["total"] == 0
        assert result["summary"]["overall"]["accuracy"] == 0.0


class TestSaveScoredResults:
    """Test saving scored results to file."""

    def test_save_scored_results_creates_directory(self, tmp_path):
        """Test that output directory is created."""
        output_file = tmp_path / "output" / "scored.json"

        scoring_output = {
            "scored_results": [],
            "summary": {},
            "metadata": {},
        }

        save_scored_results(scoring_output, str(output_file))

        assert output_file.parent.exists()

    def test_save_scored_results_creates_file(self, tmp_path):
        """Test that output file is created."""
        output_file = tmp_path / "scored.json"

        scoring_output = {
            "scored_results": [],
            "summary": {},
            "metadata": {},
        }

        save_scored_results(scoring_output, str(output_file))

        assert output_file.exists()

    def test_save_scored_results_valid_json(self, tmp_path):
        """Test that saved file contains valid JSON."""
        output_file = tmp_path / "scored.json"

        scoring_output = {
            "scored_results": [
                {"question_id": "test", "correct": True},
            ],
            "summary": {"overall": {"total": 1}},
            "metadata": {"scoring_method": "deterministic"},
        }

        save_scored_results(scoring_output, str(output_file))

        # Read back and verify it's valid JSON
        with open(output_file) as f:
            data = json.load(f)

        assert data["scored_results"][0]["question_id"] == "test"
        assert data["metadata"]["scoring_method"] == "deterministic"
