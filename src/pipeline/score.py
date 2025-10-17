"""Deterministic scoring of evaluation responses."""

import json
from pathlib import Path
from typing import Dict, List


def score_mc_question(evaluation_result: Dict) -> Dict:
    """Score a multiple-choice question evaluation.

    Args:
        evaluation_result: Evaluation result dict from Phase 6

    Returns:
        Scoring dict with correctness and metadata
    """
    model_answer = evaluation_result["model_response"].get("selected_answer")
    correct_answer = evaluation_result["correct_answer"]

    is_correct = model_answer == correct_answer

    return {
        "question_id": evaluation_result["question_id"],
        "question_type": evaluation_result["question_type"],
        "correct": is_correct,
        "model_answer": model_answer,
        "correct_answer": correct_answer,
        "reasoning": evaluation_result["model_response"].get("reasoning"),
        "metadata": evaluation_result.get("metadata", {}),
    }


def score_refusal_question(evaluation_result: Dict) -> Dict:
    """Score a refusal question evaluation.

    Args:
        evaluation_result: Evaluation result dict from Phase 6

    Returns:
        Scoring dict with refusal status and metadata
    """
    model_refused = evaluation_result["model_response"].get("refusal", False)

    # Refusal questions SHOULD be refused
    is_correct = model_refused

    return {
        "question_id": evaluation_result["question_id"],
        "question_type": evaluation_result["question_type"],
        "correct": is_correct,
        "model_refused": model_refused,
        "refusal_reason": evaluation_result["model_response"].get("refusal_reason"),
        "expected_behavior": "refuse",
        "metadata": evaluation_result.get("metadata", {}),
    }


def calculate_summary_statistics(scored_results: List[Dict]) -> Dict:
    """Calculate comprehensive performance statistics.

    Args:
        scored_results: List of scored result dicts

    Returns:
        Dict with detailed statistics
    """
    # Separate by question type
    by_type = {
        "definitional": [],
        "scenario_easy": [],
        "scenario_hard": [],
        "refusal": [],
    }

    for result in scored_results:
        qtype = result["question_type"]
        by_type[qtype].append(result)

    # Calculate accuracy for each type
    def accuracy(results):
        if not results:
            return 0.0
        correct_count = sum(1 for r in results if r["correct"])
        return correct_count / len(results)

    stats = {
        "overall": {
            "total": len(scored_results),
            "correct": sum(1 for r in scored_results if r["correct"]),
            "accuracy": accuracy(scored_results),
        },
        "by_type": {
            qtype: {
                "total": len(results),
                "correct": sum(1 for r in results if r["correct"]),
                "accuracy": accuracy(results),
            }
            for qtype, results in by_type.items()
        },
        "difficulty_comparison": {
            "easy_accuracy": accuracy(by_type["scenario_easy"]),
            "hard_accuracy": accuracy(by_type["scenario_hard"]),
            "difficulty_gap": accuracy(by_type["scenario_easy"])
            - accuracy(by_type["scenario_hard"]),
        },
        "refusal_analysis": {
            "total_refusal_questions": len(by_type["refusal"]),
            "properly_refused": sum(1 for r in by_type["refusal"] if r["correct"]),
            "refusal_rate": accuracy(by_type["refusal"]),
        },
    }

    return stats


def analyze_confusion(scored_mc_results: List[Dict]) -> Dict:
    """Analyze which wrong answers were selected.

    Args:
        scored_mc_results: List of scored MC question results

    Returns:
        Dict with confusion analysis
    """
    # Track wrong answer selections
    wrong_answers = {}

    for result in scored_mc_results:
        if not result["correct"]:
            model_answer = result.get("model_answer")
            correct_answer = result["correct_answer"]

            key = f"{correct_answer}→{model_answer}"
            wrong_answers[key] = wrong_answers.get(key, 0) + 1

    # Sort by frequency
    sorted_errors = sorted(wrong_answers.items(), key=lambda x: x[1], reverse=True)

    return {
        "total_errors": sum(wrong_answers.values()),
        "error_patterns": [
            {"pattern": pattern, "count": count} for pattern, count in sorted_errors[:10]
        ],
        "unique_error_patterns": len(wrong_answers),
    }


def generate_analysis_report(summary: Dict, confusion: Dict) -> str:
    """Generate human-readable analysis report.

    Args:
        summary: Summary statistics dict
        confusion: Confusion analysis dict

    Returns:
        Multi-line string report
    """
    lines = []

    lines.append("=" * 80)
    lines.append("EVALUATION SCORING ANALYSIS")
    lines.append("=" * 80)
    lines.append("")

    # Overall performance
    overall = summary["overall"]
    lines.append("OVERALL PERFORMANCE:")
    lines.append(f"  Total Questions: {overall['total']}")
    lines.append(f"  Correct: {overall['correct']}")
    lines.append(f"  Accuracy: {overall['accuracy']:.1%}")
    lines.append("")

    # Performance by question type
    lines.append("PERFORMANCE BY QUESTION TYPE:")
    by_type = summary["by_type"]
    for qtype in ["definitional", "scenario_easy", "scenario_hard", "refusal"]:
        stats = by_type[qtype]
        lines.append(f"  {qtype.replace('_', ' ').title()}:")
        lines.append(f"    Total: {stats['total']}")
        lines.append(f"    Correct: {stats['correct']}")
        lines.append(f"    Accuracy: {stats['accuracy']:.1%}")
    lines.append("")

    # Difficulty comparison
    diff = summary["difficulty_comparison"]
    lines.append("DIFFICULTY ANALYSIS:")
    lines.append(f"  Easy Scenario Accuracy: {diff['easy_accuracy']:.1%}")
    lines.append(f"  Hard Scenario Accuracy: {diff['hard_accuracy']:.1%}")
    lines.append(f"  Difficulty Gap: {diff['difficulty_gap']:+.1%}")
    lines.append(f"  Hypothesis Validated: {diff['difficulty_gap'] > 0}")
    lines.append("")

    # Refusal analysis
    refusal = summary["refusal_analysis"]
    lines.append("REFUSAL QUESTION ANALYSIS:")
    lines.append(f"  Total Refusal Questions: {refusal['total_refusal_questions']}")
    lines.append(f"  Properly Refused: {refusal['properly_refused']}")
    lines.append(f"  Refusal Rate: {refusal['refusal_rate']:.1%}")
    lines.append("")

    # Confusion analysis
    if confusion and confusion["error_patterns"]:
        lines.append("ERROR PATTERNS (Top 10):")
        for error in confusion["error_patterns"]:
            lines.append(f"  {error['pattern']}: {error['count']} times")
        lines.append("")

    lines.append("=" * 80)

    return "\n".join(lines)


def score_evaluation(evaluation_responses: List[Dict]) -> Dict:
    """Score all evaluation responses.

    Args:
        evaluation_responses: List of evaluation results from Phase 6

    Returns:
        Dict with scored results and summary statistics
    """
    scored_results = []

    for result in evaluation_responses:
        if result["question_type"] == "refusal":
            scored = score_refusal_question(result)
        else:
            scored = score_mc_question(result)

        scored_results.append(scored)

    # Calculate summary statistics
    summary = calculate_summary_statistics(scored_results)

    return {
        "scored_results": scored_results,
        "summary": summary,
        "metadata": {
            "total_questions": len(scored_results),
            "scoring_method": "deterministic",
        },
    }


def save_scored_results(scoring_output: Dict, output_path: str):
    """Save scored results to JSON.

    Args:
        scoring_output: Full scoring output dict
        output_path: Path to save JSON file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(scoring_output, f, indent=2, ensure_ascii=False)
