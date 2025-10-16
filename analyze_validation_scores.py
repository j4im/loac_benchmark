#!/usr/bin/env python3
"""Analyze score distributions from validation cache to assess anchoring and inform threshold tuning."""

import json
from pathlib import Path
from collections import defaultdict
import statistics

# Component types to analyze
components = {
    'Rule Confidence': [],
    'Question Conf (definitional)': [],
    'Question Conf (scenario_easy)': [],
    'Question Conf (scenario_hard)': [],
    'Question Conf (refusal)': [],
    'Question Entailment': [],
    'Answer Entailment': [],
    'Distractor Quality': [],
    'Refusal Appropriateness': []
}

# Prompt values for comparison (from dual examples - HIGH QUALITY value)
prompt_values = {
    'Rule Confidence': 95,
    'Question Conf (definitional)': 95,
    'Question Conf (scenario_easy)': 95,
    'Question Conf (scenario_hard)': 95,
    'Question Conf (refusal)': 95,
    'Question Entailment': 95,
    'Answer Entailment': 95,
    'Distractor Quality': 95,
    'Refusal Appropriateness': 95
}

# Load questions to get confidences
with open('data/generated/questions.json', 'r') as f:
    questions = json.load(f)

for q in questions:
    conf = q.get('confidence', 0)
    qtype = q['question_type']

    if qtype == 'definitional':
        components['Question Conf (definitional)'].append(conf)
    elif qtype == 'scenario_easy':
        components['Question Conf (scenario_easy)'].append(conf)
    elif qtype == 'scenario_hard':
        components['Question Conf (scenario_hard)'].append(conf)
    elif qtype == 'refusal':
        components['Question Conf (refusal)'].append(conf)

# Load rules to get rule confidences
with open('data/extracted/rules.json', 'r') as f:
    rules = json.load(f)

for rule in rules:
    components['Rule Confidence'].append(rule.get('confidence', 0))

# Load validation cache
cache_dir = Path('cache/validation')

for cache_file in cache_dir.glob('*.json'):
    with open(cache_file, 'r') as f:
        data = json.load(f)

    fname = cache_file.name

    # Question entailment
    if 'question_entailment' in fname:
        if isinstance(data, dict) and 'confidence' in data:
            components['Question Entailment'].append(data['confidence'])

    # Answer entailment
    elif 'answer_entailment' in fname:
        if isinstance(data, dict) and 'confidence' in data:
            components['Answer Entailment'].append(data['confidence'])

    # Distractors
    elif 'distractors' in fname:
        if isinstance(data, list):
            for d in data:
                if 'quality_score' in d:
                    components['Distractor Quality'].append(d['quality_score'])

    # Refusal
    elif fname.endswith('_refusal.json'):
        if isinstance(data, dict) and 'appropriateness_score' in data:
            components['Refusal Appropriateness'].append(data['appropriateness_score'])

# Print results
print("\n" + "="*110)
print("VALIDATION SCORE DISTRIBUTION ANALYSIS")
print("="*110)
print(f"{'Component':<35} {'n':>4}  {'Mean':>5} {'StdDev':>6}  {'Min':>3}  {'Max':>3} {'Prompt':>6}  {'%@Prompt':>9}  {'#Unique':>8}")
print("-"*110)

for name, values in components.items():
    if not values:
        continue

    n = len(values)
    mean = statistics.mean(values)
    stddev = statistics.stdev(values) if n > 1 else 0
    min_val = min(values)
    max_val = max(values)
    prompt_val = prompt_values.get(name, 0)
    at_prompt = sum(1 for v in values if v == prompt_val)
    pct_at_prompt = (at_prompt / n * 100) if n > 0 else 0
    unique = len(set(values))

    print(f"{name:<35} {n:>4}  {mean:>5.1f} {stddev:>6.2f}  {min_val:>3}  {max_val:>3} {prompt_val:>6}  {pct_at_prompt:>8.1f}%  {unique:>8}")

print("="*110)

# Print detailed distribution for each component (DECILE-BASED HISTOGRAMS)
print("\nDETAILED DISTRIBUTIONS (BY DECILE):")
print("="*110)

for name, values in components.items():
    if not values:
        continue

    print(f"\n{name}:")
    print(f"  n={len(values)}, mean={statistics.mean(values):.1f}, stddev={statistics.stdev(values) if len(values) > 1 else 0:.2f}")

    # Count frequency by decile
    deciles = {
        '  0-9': 0,
        ' 10-19': 0,
        ' 20-29': 0,
        ' 30-39': 0,
        ' 40-49': 0,
        ' 50-59': 0,
        ' 60-69': 0,
        ' 70-79': 0,
        ' 80-89': 0,
        ' 90-99': 0,
        '  100': 0
    }

    for v in values:
        if v == 100:
            deciles['  100'] += 1
        elif 0 <= v < 10:
            deciles['  0-9'] += 1
        elif 10 <= v < 20:
            deciles[' 10-19'] += 1
        elif 20 <= v < 30:
            deciles[' 20-29'] += 1
        elif 30 <= v < 40:
            deciles[' 30-39'] += 1
        elif 40 <= v < 50:
            deciles[' 40-49'] += 1
        elif 50 <= v < 60:
            deciles[' 50-59'] += 1
        elif 60 <= v < 70:
            deciles[' 60-69'] += 1
        elif 70 <= v < 80:
            deciles[' 70-79'] += 1
        elif 80 <= v < 90:
            deciles[' 80-89'] += 1
        elif 90 <= v < 100:
            deciles[' 90-99'] += 1

    # Print histogram
    print("  Decile distribution:")
    for decile, count in deciles.items():
        if count > 0:
            pct = count / len(values) * 100
            bar = "█" * min(60, int(pct * 0.6))  # Scale bars for readability
            print(f"    {decile}: {count:>4} ({pct:>5.1f}%) {bar}")

print("\n" + "="*110)
print("ANCHORING ASSESSMENT:")
print("-"*110)
print("Strong anchoring (>70% at prompt value):")
for name, values in components.items():
    if not values:
        continue
    prompt_val = prompt_values[name]
    at_prompt = sum(1 for v in values if v == prompt_val)
    pct = at_prompt / len(values) * 100
    if pct > 70:
        print(f"  - {name}: {pct:.1f}% at {prompt_val}")

print("\nModerate anchoring (30-70% at prompt value):")
for name, values in components.items():
    if not values:
        continue
    prompt_val = prompt_values[name]
    at_prompt = sum(1 for v in values if v == prompt_val)
    pct = at_prompt / len(values) * 100
    if 30 <= pct <= 70:
        print(f"  - {name}: {pct:.1f}% at {prompt_val}")

print("\nLow/No anchoring (<30% at prompt value):")
for name, values in components.items():
    if not values:
        continue
    prompt_val = prompt_values[name]
    at_prompt = sum(1 for v in values if v == prompt_val)
    pct = at_prompt / len(values) * 100
    if pct < 30:
        print(f"  - {name}: {pct:.1f}% at {prompt_val}")

print("="*110)
