# Email Generation Assistant: Evaluation Report

IMPORTANT: the raw data and analysis below are from a `--mock` run (synthetic
stand-in outputs, used only to prove the pipeline works without an API key).
Before submitting, run `python src/run_eval.py` (no --mock, with
GEMINI_API_KEY set) and replace the table and analysis with the real numbers
from `results/eval_results.csv`.

## 1. Prompt Template (advanced strategy)

See `prompts/advanced_prompt.txt` in full. Summary of the technique: Role-
Playing (the model is assigned a "senior professional communications
specialist" persona) combined with Few-Shot examples (two worked input/output
pairs) and a lightweight Chain-of-Thought scaffold (the model is instructed to
privately plan which facts to hit and which tone markers to use before
writing, but to output only the final email). The naive baseline strategy
(`prompts/naive_prompt.txt`) skips all three and just states the intent,
facts, and tone directly.

## 2. Custom Metric Definitions and Logic

Fact Inclusion Rate (deterministic): fraction of the input key_facts whose
significant keywords appear, above a containment threshold, in some sentence
or 2-sentence window of the output. Catches dropped or ignored facts without
needing exact wording.

Tone Alignment Score (LLM-as-judge): a judge model rates 1-5 how well the
output matches the requested tone against a fixed rubric; the score is
normalized to 0-1. Used because tone-matching is a subjective judgment call
that keyword rules alone can't reliably capture. An offline keyword-cue
heuristic stands in for the judge only in --mock runs.

Structural Conciseness Score (hybrid): average of three checks - word count
inside a 60-200 word band, Flesch reading-ease above 60 (via textstat), and
presence of a subject line, greeting, and sign-off.

Full implementation: `src/metrics.py`.

## 3. Raw Evaluation Data (illustrative, from --mock run)

| Scenario | Strategy | Fact Inclusion | Tone Alignment | Structural Conciseness |
|---|---|---|---|---|
| 1 | advanced | 1.00 | 0.70 | 0.889 |
| 1 | naive    | 0.667 | 0.40 | 0.553 |
| 2 | advanced | 1.00 | 0.70 | 0.851 |
| 2 | naive    | 0.667 | 0.40 | 0.553 |
| 3 | advanced | 0.667 | 0.85 | 0.889 |
| 3 | naive    | 0.667 | 0.40 | 0.550 |
| 4 | advanced | 1.00 | 0.70 | 0.889 |
| 4 | naive    | 0.667 | 0.40 | 0.543 |
| 5 | advanced | 1.00 | 0.85 | 0.889 |
| 5 | naive    | 0.667 | 0.40 | 0.550 |
| 6 | advanced | 1.00 | 0.85 | 0.945 |
| 6 | naive    | 0.667 | 0.40 | 0.547 |
| 7 | advanced | 0.667 | 0.55 | 0.889 |
| 7 | naive    | 0.667 | 0.40 | 0.524 |
| 8 | advanced | 1.00 | 0.85 | 0.889 |
| 8 | naive    | 0.667 | 0.70 | 0.557 |
| 9 | advanced | 0.667 | 0.70 | 0.822 |
| 9 | naive    | 0.667 | 0.40 | 0.547 |
| 10 | advanced | 1.00 | 0.70 | 0.862 |
| 10 | naive    | 0.667 | 0.40 | 0.546 |

Averages: advanced = Fact 0.90 / Tone 0.745 / Structure 0.881.
naive = Fact 0.667 / Tone 0.43 / Structure 0.547.

## 4. Comparative Analysis (illustrative, replace with real-run numbers)

Which performed better: the advanced strategy led on all 3 custom metrics in
this illustrative run (Fact Inclusion +0.233, Tone Alignment +0.315,
Structural Conciseness +0.334). Re-confirm this ranking against the real
(non-mock) numbers before finalizing.

Biggest failure mode of the lower-performing strategy: in this illustrative
run, the naive baseline's weakest area was tone alignment, consistent with
having no persona or examples to anchor style. Its fact inclusion was also
capped because it has no planning step, so it tends to drop a fact rather
than weave in every detail. Once real Gemini outputs are in, check which
metric actually shows the largest gap and adjust this paragraph accordingly,
quoting the specific scenario IDs where the naive output dropped a fact or
mismatched tone.

Recommendation: the advanced strategy (role-playing + few-shot + lightweight
chain-of-thought) is recommended for production, justified by its lead across
all three custom metrics, not just one. State the real average deltas here
once available, and note any per-scenario outliers worth a follow-up prompt
tweak.
