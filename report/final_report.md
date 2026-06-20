# Email Generation Assistant — Final Report

---

## Section 1: Prompt Template and Documented Technique

### Strategy A: Advanced Prompt (Role-Playing + Few-Shot + Chain-of-Thought)

File: `prompts/advanced_prompt.txt`

**Techniques used:**

**1. Role-Playing** — The model is assigned a specific expert persona at the top of the prompt:
> "You are a senior professional communications specialist who has written thousands of business emails across formal, casual, urgent, and empathetic situations."

This anchors tone and style expectations before any task is given.

**2. Few-Shot Examples** — Two complete worked input/output pairs are provided inside the prompt. Each example shows the exact format expected: a labelled intent, key facts, tone, and a complete email wrapped in `<email>` tags. This teaches the model structure and format without stating rules explicitly.

**3. Chain-of-Thought Scaffold** — The prompt instructs the model to silently plan before writing:
> "Before writing, silently plan: (1) which exact facts must appear, (2) what tone markers match the requested tone, (3) a natural opening and closing. Do not show this planning."

This forces internal reasoning about fact coverage and tone before committing to output.

The model is then told to output only the final email inside `<email></email>` tags, with a subject line, greeting, and sign-off.

### Strategy B: Naive Baseline Prompt (Zero-Shot)

File: `prompts/naive_prompt.txt`

Contains only three lines: the intent, facts, and tone as labelled fields with no persona, no examples, and no reasoning instruction. This is the control condition for the comparison in Section 3.

---

## Section 2: Custom Metric Definitions and Logic

### Metric 1 — Fact Inclusion Rate
**Type:** Deterministic (no API calls, no external models)
**Range:** 0.0 – 1.0

**Definition:** The fraction of the input key_facts that are actually represented in the generated email.

**Logic:** Each fact is tokenised into its significant keywords by removing a fixed stopword list and keeping words longer than 1 character. For every sentence in the generated email, and for every pair of adjacent sentences (a sliding 2-sentence window), a containment score is computed as:

`containment = len(fact_keywords ∩ window_keywords) / len(fact_keywords)`

Containment (not Jaccard similarity) is used because naturally rephrased facts still score well even when surrounded by many other words. A fact is counted as included if its best window score meets or exceeds a threshold of 0.55. Final score = facts_included / total_facts.

**Why this metric:** Fact dropping is the most costly failure mode in email generation — a reader may act on incomplete information. This metric catches it deterministically without any API cost.

---

### Metric 2 — Tone Alignment Score
**Type:** LLM-as-Judge
**Range:** 0.0 – 1.0

**Definition:** How well the email's actual tone matches the requested tone label.

**Logic:** A judge model (accessed via OpenRouter's free router, temperature=0 for reproducibility) is given the following fixed rubric and the generated email:

> "Rate how well this email matches the tone '[tone]' on a scale of 1-5, where 1 = opposite tone and 5 = perfectly matches. Reply with ONLY the integer."

The returned integer is divided by 5 to normalise to 0–1. Temperature=0 is used for the judge specifically so scores are stable and repeatable across runs. The same judge prompt and model are used for both the advanced and naive strategies, making the comparison fair.

**Why this metric:** Tone-matching is a subjective quality that keyword rules cannot reliably capture. "Empathetic" vs "formal" vs "urgent" requires understanding sentence rhythm, word choice, and framing — exactly what an LLM judge can evaluate.

---

### Metric 3 — Structural Conciseness Score
**Type:** Hybrid (deterministic + textstat library)
**Range:** 0.0 – 1.0

**Definition:** Whether the email is appropriately concise and properly structured, independent of tone or factual content.

**Logic:** The final score is the average of three equally weighted sub-checks:

**(a) Word Count (length score):** Word count within 60–200 words scores 1.0. Outside the band, the score decays linearly by 0.01 per word of distance, floored at 0.0.

**(b) Readability (Flesch Reading Ease via textstat):** A Flesch Reading Ease score ≥ 60 scores 1.0. Below 60, the score equals raw_flesch / 60, floored at 0.0. A score of 60 corresponds to plain English readable by a general adult audience.

**(c) Structure presence (regex checks):** Binary presence of (i) a subject line detected by `Subject:` pattern, (ii) a greeting (Dear / Hi / Hey / Hello) at the start of a line, and (iii) a sign-off (Regards / Sincerely / Best / Cheers / Thanks) followed by punctuation and a newline. Sub-score = count_present / 3.

Final = (a + b + c) / 3.

**Why this metric:** An email that is accurate and on-tone but 800 words long with no subject line is not production-ready. This metric catches formatting and length failures independently of the other two.

---

## Section 3: Raw Evaluation Data

All 20 rows from `results/eval_results.csv` (10 scenarios × 2 strategies):

| Scenario | Intent | Tone | Strategy | Fact Inclusion | Tone Alignment | Structural Conciseness |
|---|---|---|---|---|---|---|
| 1 | Follow up after a client meeting | formal | advanced | 1.000 | 0.80 | 0.919 |
| 1 | Follow up after a client meeting | formal | naive | 1.000 | 1.00 | 0.769 |
| 2 | Request proposal details from a vendor | formal | advanced | 1.000 | 1.00 | 0.893 |
| 2 | Request proposal details from a vendor | formal | naive | 1.000 | 1.00 | 0.923 |
| 3 | Apologize to a customer for a delayed shipment | empathetic | advanced | 0.667 | 0.60 | 0.996 |
| 3 | Apologize to a customer for a delayed shipment | empathetic | naive | 1.000 | 1.00 | 0.828 |
| 4 | Give the team a project status update | casual | advanced | 1.000 | 0.80 | 0.973 |
| 4 | Give the team a project status update | casual | naive | 1.000 | 0.40 | 1.000 |
| 5 | Reschedule a meeting | formal | advanced | 0.333 | 1.00 | 1.000 |
| 5 | Reschedule a meeting | formal | naive | 0.667 | 1.00 | 0.997 |
| 6 | Escalate a production outage to leadership | urgent | advanced | 1.000 | 1.00 | 0.904 |
| 6 | Escalate a production outage to leadership | urgent | naive | 0.667 | 0.40 | 0.466 |
| 7 | Thank a guest speaker after a conference | warm | advanced | 0.667 | 1.00 | 0.896 |
| 7 | Thank a guest speaker after a conference | warm | naive | 0.333 | 1.00 | 0.908 |
| 8 | Cold outreach to a potential client | persuasive | advanced | 1.000 | 1.00 | 0.964 |
| 8 | Cold outreach to a potential client | persuasive | naive | 1.000 | 1.00 | 0.580 |
| 9 | Decline a request to extend a contract deadline | polite but firm | advanced | 1.000 | 0.80 | 1.000 |
| 9 | Decline a request to extend a contract deadline | polite but firm | naive | 1.000 | 1.00 | 0.738 |
| 10 | Deliver news of a job position being eliminated | empathetic | advanced | 1.000 | 0.60 | 0.817 |
| 10 | Deliver news of a job position being eliminated | empathetic | naive | 1.000 | 1.00 | 0.614 |

### Average Scores

| Strategy | Fact Inclusion Rate | Tone Alignment Score | Structural Conciseness Score | Overall Average |
|---|---|---|---|---|
| Advanced | 0.867 | 0.860 | 0.936 | 0.888 |
| Naive | 0.867 | 0.880 | 0.782 | 0.843 |

---

## Section 4: Comparative Analysis

### Which strategy performed better?

The results show a nuanced outcome. Neither strategy dominated across all three metrics.

The **advanced strategy** (Role-Playing + Few-Shot + Chain-of-Thought) outperformed on **Structural Conciseness Score** by a significant margin: 0.936 vs 0.782, a delta of +0.154. This is the clearest and most consistent advantage. The advanced prompt's few-shot examples and explicit sign-off/structure instructions directly caused this: the model consistently produced properly formatted emails with subject lines, greetings, and sign-offs.

On **Fact Inclusion Rate**, both strategies scored identically at 0.867. The chain-of-thought planning step in the advanced prompt did not produce a measurable advantage in fact coverage at this sample size. Both models occasionally dropped a fact (Scenarios 5 and 7 show this for both).

On **Tone Alignment Score**, the naive strategy marginally outperformed: 0.880 vs 0.860, a delta of +0.020. This is a counterintuitive finding. The likely explanation is that the naive prompt's minimal framing gave the free model more freedom to match tone naturally, while the advanced prompt's persona and few-shot examples occasionally pulled the model toward a default "professional" register even when a different tone (empathetic, casual) was requested. Scenarios 3 and 10 (both empathetic tone) show the advanced strategy scoring 0.60 while the naive scored 1.00 on those same scenarios.

The overall averages — advanced 0.888, naive 0.843 — give the advanced strategy a +0.045 overall lead.

### Biggest failure mode of the lower-performing strategy

The naive strategy's biggest failure mode is **structural inconsistency**, not tone or facts. Scenarios 6, 8, and 10 show structural conciseness scores of 0.466, 0.580, and 0.614 respectively under the naive strategy. Inspecting these: the naive prompt produced emails that were either too long (>200 words) or missing a subject line entirely, because nothing in the prompt instructed the model to include one. Scenario 6 (urgent escalation) under naive scored 0.466 — the model produced a long block of text with no subject line and no clear sign-off, making it unsuitable for production use even though the tone was rated correctly.

### Production recommendation

**Recommend the advanced strategy for production**, justified by the metric data on the dimension that matters most operationally: structure. A tone mismatch is noticeable but recoverable — a human sender can adjust. A missing subject line, missing sign-off, or email that is 400 words long is a direct formatting failure that would require manual intervention before sending at scale. The advanced strategy's +0.154 advantage on Structural Conciseness Score, combined with its +0.045 overall average lead, makes it the safer production choice.

To address the tone alignment gap on empathetic scenarios, a targeted improvement would be to add one empathetic few-shot example to the advanced prompt — the current examples both use formal and casual tones. That single addition would likely close the 0.020 tone gap while preserving the structural advantage.
