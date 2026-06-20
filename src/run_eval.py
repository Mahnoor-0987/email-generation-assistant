"""
run_eval.py
Runs all 10 scenarios through both prompting strategies (advanced, naive),
scores every output on the 3 custom metrics, and writes results to:
  results/eval_results.json
  results/eval_results.csv

Usage:
  Real run:   python src/run_eval.py
  Offline:    python src/run_eval.py --mock
"""

import argparse
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(__file__))
import generate
import metrics

BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH   = os.path.join(BASE_DIR, "data",    "scenarios.json")
PROMPTS_DIR = os.path.join(BASE_DIR, "prompts")
RESULTS_DIR = os.path.join(BASE_DIR, "results")

# Free tier: 15 requests/min. We wait 5s between every API call to stay safe.
API_CALL_DELAY = 5

METRIC_DEFINITIONS = {
    "fact_inclusion_rate": {
        "name": "Fact Inclusion Rate",
        "type": "deterministic",
        "range": "0.0 – 1.0",
        "definition": (
            "Fraction of the input key_facts that are actually represented in "
            "the generated email."
        ),
        "logic": (
            "Each fact is tokenised into its significant keywords (stopwords "
            "removed). For every sentence and every pair of adjacent sentences "
            "in the output, a containment score is computed as: "
            "len(fact_keywords intersect window_keywords) / len(fact_keywords). "
            "A fact is counted as included if its best window score meets or "
            "exceeds the containment threshold (0.55). "
            "Final score = facts_included / total_facts."
        ),
    },
    "tone_alignment_score": {
        "name": "Tone Alignment Score",
        "type": "LLM-as-judge (heuristic fallback in --mock mode)",
        "range": "0.0 – 1.0",
        "definition": (
            "How well the email's actual tone matches the requested tone label."
        ),
        "logic": (
            "A judge model (gemini-2.0-flash, temperature=0 for reproducibility) "
            "is given the target tone, the email, and a fixed 1-5 rubric: "
            "1 = opposite tone, 5 = perfectly matches. It replies with only the "
            "integer. Score = judge_integer / 5."
        ),
    },
    "structural_conciseness_score": {
        "name": "Structural Conciseness Score",
        "type": "hybrid (deterministic + textstat)",
        "range": "0.0 – 1.0",
        "definition": (
            "Whether the email is appropriately concise and properly structured."
        ),
        "logic": (
            "Average of three sub-checks: "
            "(a) word count in the 60-200 word band scores 1.0; outside it "
            "decays by 0.01 per word of distance. "
            "(b) Flesch Reading Ease >= 60 scores 1.0; below 60, score = raw/60. "
            "(c) Presence of subject line + greeting + sign-off via regex, "
            "scored as count_present / 3. "
            "Final = (a + b + c) / 3."
        ),
    },
}


def mock_advanced_output(scenario: dict) -> str:
    return scenario["human_reference_email"]


def mock_naive_output(scenario: dict) -> str:
    facts = scenario["key_facts"]
    kept = facts[:-1] if len(facts) > 1 else facts
    body = " ".join(kept) + "."
    return f"To Whom It May Concern, {body} Let me know if you have questions."


def run(use_mock: bool):
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        scenarios = json.load(f)

    judge_fn = None
    if not use_mock:
        judge_fn = generate.make_judge_fn()

    rows = []
    total = len(scenarios) * 2
    call_num = 0

    for scenario in scenarios:
        for strategy in ("advanced", "naive"):
            call_num += 1
            print(f"[{call_num}/{total}] Scenario {scenario['id']} | strategy: {strategy}")

            if use_mock:
                email_text = (mock_advanced_output(scenario)
                              if strategy == "advanced"
                              else mock_naive_output(scenario))
            else:
                email_text = generate.generate_email(
                    strategy, scenario, prompts_dir=PROMPTS_DIR
                )
                time.sleep(API_CALL_DELAY)  # stay under 15 req/min free tier limit

            scores = metrics.score_email(email_text, scenario, judge_fn=judge_fn)

            if not use_mock and judge_fn:
                time.sleep(API_CALL_DELAY)  # delay after the tone judge call too

            rows.append({
                "scenario_id":  scenario["id"],
                "intent":       scenario["intent"],
                "tone":         scenario["tone"],
                "strategy":     strategy,
                "email_output": email_text,
                **scores,
            })
            print(f"         scores: {scores}")

    os.makedirs(RESULTS_DIR, exist_ok=True)

    metric_keys = ["fact_inclusion_rate", "tone_alignment_score",
                   "structural_conciseness_score"]
    summary = {}
    for strategy in ("advanced", "naive"):
        strat_rows = [r for r in rows if r["strategy"] == strategy]
        per_metric = {
            m: round(sum(r[m] for r in strat_rows) / len(strat_rows), 3)
            for m in metric_keys
        }
        overall = round(sum(per_metric.values()) / len(metric_keys), 3)
        summary[strategy] = {**per_metric, "overall_average": overall}

    json_path = os.path.join(RESULTS_DIR, "eval_results.json")
    report = {
        "metric_definitions": METRIC_DEFINITIONS,
        "results":            rows,
        "summary":            summary,
    }
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    csv_path = os.path.join(RESULTS_DIR, "eval_results.csv")
    csv_fields = ["scenario_id", "intent", "tone", "strategy",
                  "fact_inclusion_rate", "tone_alignment_score",
                  "structural_conciseness_score", "email_output"]
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: row[k] for k in csv_fields})

    print(f"\n{'Strategy':<10} " + " ".join(f"{m:<32}" for m in metric_keys) + "overall_avg")
    for strategy in ("advanced", "naive"):
        s = summary[strategy]
        print(f"{strategy:<10} " + " ".join(f"{s[m]:<32}" for m in metric_keys) + str(s["overall_average"]))

    print(f"\nDone. Results in {RESULTS_DIR}")
    if use_mock:
        print("NOTE: --mock run. Run without --mock for real Gemini outputs.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mock", action="store_true")
    args = parser.parse_args()
    run(use_mock=args.mock)
