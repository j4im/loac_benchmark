"""Question validation and quality control."""

import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from openai import OpenAI


def validate_structure(question: Dict, parsed_sections: Dict) -> Tuple[bool, List[str]]:
    """
    Validate structural correctness of a question.

    This is a HARD GATE - structurally invalid questions are immediately rejected.

    Args:
        question: Question dict to validate
        parsed_sections: Parsed sections from Phase 1 (to verify references)

    Returns:
        Tuple of (is_valid, list_of_issues)
    """
    issues = []

    # Required fields for all questions
    required_fields = ['question_id', 'question_type', 'question', 'confidence', 'metadata']
    for field in required_fields:
        if field not in question:
            issues.append(f"Missing required field: {field}")

    # Check question type
    valid_types = ['definitional', 'scenario_easy', 'scenario_hard', 'refusal']
    if 'question_type' in question and question['question_type'] not in valid_types:
        issues.append(f"Invalid question_type: {question['question_type']}")

    # Type-specific validation
    if 'question_type' in question:
        qtype = question['question_type']

        if qtype in ['definitional', 'scenario_easy', 'scenario_hard']:
            # Multiple-choice questions
            if 'correct_answer' not in question:
                issues.append("MC question missing correct_answer")
            if 'incorrect_answers' not in question:
                issues.append("MC question missing incorrect_answers")
            elif len(question['incorrect_answers']) != 3:
                issues.append(f"MC question has {len(question['incorrect_answers'])} incorrect answers, expected 3")

        elif qtype == 'refusal':
            # Refusal questions
            if 'refusal_reason' not in question:
                issues.append("Refusal question missing refusal_reason")
            if 'incorrect_answers' in question:
                issues.append("Refusal question should not have incorrect_answers")

    # Metadata validation
    if 'metadata' in question:
        metadata = question['metadata']
        required_metadata = ['source_section', 'source_rule', 'rule_type',
                            'footnotes_used', 'generation_model',
                            'generation_timestamp', 'source_page_numbers']
        for field in required_metadata:
            if field not in metadata:
                issues.append(f"Missing metadata field: {field}")

        # Verify source_section exists in parsed sections
        if 'source_section' in metadata:
            section_id = metadata['source_section']
            if section_id not in parsed_sections:
                issues.append(f"source_section '{section_id}' not found in parsed sections")

    # Confidence range check
    if 'confidence' in question:
        conf = question['confidence']
        if not isinstance(conf, (int, float)) or conf < 0 or conf > 100:
            issues.append(f"confidence must be 0-100, got {conf}")

    return (len(issues) == 0, issues)


def validate_question_entailment(
    question: Dict,
    client: Optional[OpenAI] = None
) -> Dict:
    """
    Validate that the question itself is entailed by (grounded in) the source rule.

    This applies to ALL question types (MC and refusal).

    Args:
        question: Question dict with source_rule
        client: OpenAI client

    Returns:
        Dict with question entailment validation results
    """
    from src.config import QUESTION_ENTAILMENT_VALIDATION_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Check cache first
    cache_path = Path(f"cache/validation/{question['question_id']}_question_entailment.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Build prompt
    prompt = QUESTION_ENTAILMENT_VALIDATION_PROMPT.format(
        source_rule=question['metadata']['source_rule'],
        question=question['question']
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a legal expert validating question quality. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low for consistent validation
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Cache result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return result

    except Exception as e:
        return {'error': str(e)}


def validate_answer_entailment(
    question: Dict,
    client: Optional[OpenAI] = None
) -> Dict:
    """
    Validate that the correct answer is entailed by the source rule.

    This applies only to MC questions (definitional, scenario_easy, scenario_hard).

    Args:
        question: Question dict with source_rule and correct_answer
        client: OpenAI client

    Returns:
        Dict with answer entailment validation results
    """
    from src.config import ANSWER_ENTAILMENT_VALIDATION_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Skip if not a MC question
    if 'correct_answer' not in question:
        return {'skipped': True, 'reason': 'Not a multiple-choice question'}

    # Check cache first
    cache_path = Path(f"cache/validation/{question['question_id']}_answer_entailment.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    # Build prompt
    prompt = ANSWER_ENTAILMENT_VALIDATION_PROMPT.format(
        source_rule=question['metadata']['source_rule'],
        question=question['question'],
        answer=question['correct_answer']
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a legal expert validating question quality. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,  # Low for consistent validation
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Cache result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return result

    except Exception as e:
        return {'error': str(e)}


def validate_distractors(
    question: Dict,
    client: Optional[OpenAI] = None
) -> List[Dict]:
    """
    Validate quality of all distractors for a multiple-choice question.

    Validates all 3 distractors. Question will be flagged if ANY distractor fails.

    Args:
        question: Question dict with incorrect_answers
        client: OpenAI client

    Returns:
        List of validation results for each distractor
    """
    from src.config import DISTRACTOR_VALIDATION_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Skip if not a MC question
    if 'incorrect_answers' not in question:
        return []

    # Check cache first
    cache_path = Path(f"cache/validation/{question['question_id']}_distractors.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    results = []

    for i, distractor in enumerate(question['incorrect_answers']):
        prompt = DISTRACTOR_VALIDATION_PROMPT.format(
            source_rule=question['metadata']['source_rule'],
            question=question['question'],
            correct_answer=question['correct_answer'],
            distractor=distractor
        )

        try:
            response = client.chat.completions.create(
                model="gpt-4.1",
                messages=[
                    {"role": "system", "content": "You are a legal expert validating question quality. Return valid JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.1,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)
            result['distractor'] = distractor
            result['distractor_index'] = i
            results.append(result)

        except Exception as e:
            results.append({'distractor': distractor, 'distractor_index': i, 'error': str(e)})

    # Cache results
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cache_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    return results


def validate_refusal(
    question: Dict,
    client: Optional[OpenAI] = None
) -> Dict:
    """
    Validate that a refusal question is appropriate for refusal testing.

    Args:
        question: Refusal question dict
        client: OpenAI client

    Returns:
        Dict with refusal validation results
    """
    from src.config import REFUSAL_VALIDATION_PROMPT
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    # Skip if not a refusal question
    if question['question_type'] != 'refusal':
        return {'skipped': True, 'reason': 'Not a refusal question'}

    # Check cache first
    cache_path = Path(f"cache/validation/{question['question_id']}_refusal.json")
    if cache_path.exists():
        with open(cache_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    prompt = REFUSAL_VALIDATION_PROMPT.format(
        source_rule=question['metadata']['source_rule'],
        question=question['question'],
        refusal_reason=question['refusal_reason']
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1",
            messages=[
                {"role": "system", "content": "You are a legal expert validating question quality. Return valid JSON only."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1,
            response_format={"type": "json_object"}
        )

        result = json.loads(response.choices[0].message.content)

        # Cache result
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, indent=2, ensure_ascii=False)

        return result

    except Exception as e:
        return {'error': str(e)}


def get_rule_confidence(question: Dict, rules: List[Dict]) -> float:
    """
    Get the rule confidence from Phase 2 for this question's source rule.

    Args:
        question: Question dict with source metadata
        rules: List of all rules from Phase 2

    Returns:
        Rule confidence (0-100)
    """
    # Find matching rule and get rule confidence (from Phase 2)
    source_section = question['metadata']['source_section']
    source_rule_text = question['metadata']['source_rule']

    rule_confidence = 100  # Default if not found
    for rule in rules:
        if (rule.get('source_section') == source_section and
            rule.get('rule_text') == source_rule_text):
            rule_confidence = rule.get('confidence', 100)
            break

    return rule_confidence


def calculate_quality_score(
    question: Dict,
    rules: List[Dict],
    question_entailment: Optional[Dict] = None,
    answer_entailment: Optional[Dict] = None,
    distractor_results: Optional[List[Dict]] = None,
    refusal_result: Optional[Dict] = None
) -> Tuple[bool, Dict]:
    """
    Calculate overall quality score using threshold-based validation.

    Validation Logic:
    - Each component must be >= 90%
    - Mean of all applicable components must be >= 95%

    Components:
    - rule_confidence (from Phase 2)
    - question_confidence (from Phase 3)
    - question_entailment (ALL questions)
    - answer_entailment (MC questions only)
    - distractor_quality (MC questions only)
    - refusal_appropriateness (refusal questions only)

    Args:
        question: Question dict
        rules: All rules from Phase 2 (for rule confidence)
        question_entailment: Question entailment validation result
        answer_entailment: Answer entailment validation result (MC only)
        distractor_results: List of distractor validation results (MC only)
        refusal_result: Refusal validation result (refusal only)

    Returns:
        Tuple of (passes_threshold, scoring_breakdown)
    """
    components = {}

    # Component 1: Rule confidence (from Phase 2)
    rule_confidence = get_rule_confidence(question, rules)
    components['rule_confidence'] = rule_confidence

    # Component 2: Question confidence (from Phase 3)
    question_confidence = question.get('confidence', 100)
    components['question_confidence'] = question_confidence

    # Component 3: Question entailment (applies to ALL question types)
    if question_entailment and 'is_entailed' in question_entailment:
        if question_entailment['is_entailed']:
            components['question_entailment'] = question_entailment.get('confidence', 0)
        else:
            components['question_entailment'] = 0  # Hard fail if not entailed
    else:
        components['question_entailment'] = 0  # Fail if validation errored

    # Type-specific components
    if question['question_type'] in ['definitional', 'scenario_easy', 'scenario_hard']:
        # Component 4: Answer entailment (MC only)
        if answer_entailment and 'is_entailed' in answer_entailment:
            if answer_entailment['is_entailed']:
                components['answer_entailment'] = answer_entailment.get('confidence', 0)
            else:
                components['answer_entailment'] = 0  # Hard fail if not entailed
        else:
            components['answer_entailment'] = 0

        # Component 5: Distractor quality (MC only) - average of 3 distractors
        if distractor_results and len(distractor_results) == 3:
            distractor_scores = [d.get('quality_score', 0) for d in distractor_results]
            components['distractor_quality'] = sum(distractor_scores) / 3
        else:
            components['distractor_quality'] = 0

    elif question['question_type'] == 'refusal':
        # Component 6: Refusal appropriateness (refusal only)
        if refusal_result and 'appropriateness_score' in refusal_result:
            # Require both conditions to be true
            if (refusal_result.get('should_be_refused', False) and
                refusal_result.get('is_distinct_from_legitimate_planning', False)):
                components['refusal_appropriateness'] = refusal_result['appropriateness_score']
            else:
                components['refusal_appropriateness'] = 0  # Hard fail
        else:
            components['refusal_appropriateness'] = 0

    # Check individual thresholds (each component >= 90%)
    failures = {k: v for k, v in components.items() if v < 90}

    # Check mean threshold (>= 95%)
    mean_score = sum(components.values()) / len(components) if components else 0

    # Question passes if:
    # 1. All components >= 90%
    # 2. Mean >= 95%
    passes = (len(failures) == 0) and (mean_score >= 95)

    breakdown = {
        'components': components,
        'mean_score': mean_score,
        'failures': failures,
        'passes_threshold': passes,
        'thresholds': {'individual': 90, 'mean': 95}
    }

    return (passes, breakdown)


def validate_and_filter_questions(
    questions: List[Dict],
    parsed_sections: Dict,
    rules: List[Dict],
    client: Optional[OpenAI] = None
) -> Tuple[List[Dict], List[Dict], Dict]:
    """
    Validate all questions and filter by quality thresholds.

    Pipeline:
    1. Structural validation (hard gate)
    2. Question entailment validation (ALL questions)
    3. Answer entailment validation (MC questions only)
    4. Distractor validation (MC questions only)
    5. Refusal appropriateness validation (refusal questions only)
    6. Threshold-based filtering:
       - Each component must be >= 90%
       - Mean of all components must be >= 95%

    Args:
        questions: List of questions from Phase 3
        parsed_sections: Parsed sections from Phase 1
        rules: All rules from Phase 2 (for rule confidence)
        client: OpenAI client

    Returns:
        Tuple of (validated_questions, rejected_questions, validation_report)
    """
    from src.lib.openai_client import get_openai_client

    if client is None:
        client = get_openai_client()

    validated = []
    rejected = []

    report = {
        'total_questions': len(questions),
        'validated': 0,
        'rejected': 0,
        'structural_failures': 0,
        'quality_failures': 0,
        'by_type': {},
        'avg_mean_score': 0.0,
        'validation_method': 'threshold_based',
        'thresholds': {'individual_component': 90, 'mean': 95}
    }

    all_mean_scores = []

    for i, question in enumerate(questions):
        question_id = question.get('question_id', f'unknown_{i}')
        print(f"  [{i+1}/{len(questions)}] Validating {question_id}...")

        # Step 1: Structural validation (HARD GATE)
        structural_valid, structural_issues = validate_structure(question, parsed_sections)

        if not structural_valid:
            # Immediate reject - structural gate
            question['_validation'] = {
                'rejected_reason': 'structural_failure',
                'structural_valid': False,
                'structural_issues': structural_issues
            }
            rejected.append(question)
            report['rejected'] += 1
            report['structural_failures'] += 1

            qtype = question.get('question_type', 'unknown')
            if qtype not in report['by_type']:
                report['by_type'][qtype] = {'validated': 0, 'rejected': 0}
            report['by_type'][qtype]['rejected'] += 1

            continue

        # Step 2: LLM-based validation (for structurally valid questions)

        # Question entailment (ALL questions)
        question_entailment = validate_question_entailment(question, client)

        # Type-specific validation
        answer_entailment = None
        distractor_results = None
        refusal_result = None

        if question['question_type'] in ['definitional', 'scenario_easy', 'scenario_hard']:
            answer_entailment = validate_answer_entailment(question, client)
            distractor_results = validate_distractors(question, client)
        elif question['question_type'] == 'refusal':
            refusal_result = validate_refusal(question, client)

        # Step 3: Calculate quality score (threshold-based)
        passes_threshold, scoring_breakdown = calculate_quality_score(
            question,
            rules,
            question_entailment,
            answer_entailment,
            distractor_results,
            refusal_result
        )

        mean_score = scoring_breakdown['mean_score']
        all_mean_scores.append(mean_score)

        # Add validation metadata to question
        question['_validation'] = {
            'passes_threshold': passes_threshold,
            'mean_score': mean_score,
            'scoring_breakdown': scoring_breakdown,
            'structural_valid': structural_valid,
            'structural_issues': structural_issues,
            'question_entailment': question_entailment,
            'answer_entailment': answer_entailment,
            'distractor_results': distractor_results,
            'refusal_result': refusal_result
        }

        # Step 4: Filter by threshold
        if passes_threshold:
            validated.append(question)
            report['validated'] += 1
        else:
            question['_validation']['rejected_reason'] = 'quality_threshold'
            rejected.append(question)
            report['rejected'] += 1
            report['quality_failures'] += 1

        # Track by type
        qtype = question['question_type']
        if qtype not in report['by_type']:
            report['by_type'][qtype] = {'validated': 0, 'rejected': 0}
        if passes_threshold:
            report['by_type'][qtype]['validated'] += 1
        else:
            report['by_type'][qtype]['rejected'] += 1

    # Calculate average mean score
    if all_mean_scores:
        report['avg_mean_score'] = sum(all_mean_scores) / len(all_mean_scores)

    return (validated, rejected, report)
