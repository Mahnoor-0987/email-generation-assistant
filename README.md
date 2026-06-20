# Email Generation Assistant

A prototype that generates professional emails from (intent, key facts, tone),
plus a custom evaluation harness comparing an advanced prompting strategy
against a naive baseline using the same model (OpenRouter free tier).

---

## Setup

### 1. Clone the repo
```
git clone https://github.com/Mahnoor-0987/email-generation-assistant.git
cd email-generation-assistant
```

### 2. Create and activate a virtual environment

Mac / Linux:
```
python3 -m venv venv
source venv/bin/activate
```

Windows (Command Prompt):
```
python -m venv venv
venv\Scripts\activate.bat
```

Windows (PowerShell):
```
python -m venv venv
venv\Scripts\Activate.ps1
```

You should see `(venv)` at the start of your terminal prompt.

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Get a free OpenRouter API key
Go to https://openrouter.ai — create a free account, no credit card needed.
Click API Keys → Create Key. Copy the key (starts with sk-or-).

### 5. Set the API key in your terminal

Mac / Linux:
```
export OPENROUTER_API_KEY="sk-or-your-key-here"
```

Windows (Command Prompt):
```
set OPENROUTER_API_KEY=sk-or-your-key-here
```

Windows (PowerShell):
```
$env:OPENROUTER_API_KEY="sk-or-your-key-here"
```

This must be set in the same terminal session you run the script from.

---

## Run

### Real evaluation (recommended, needs API key):
```
python src/run_eval.py
```
Uses `openrouter/free` (Free Models Router) — auto-selects the best
available free model per request. Makes ~40 API calls total. Takes 4-6
minutes due to 5-second pacing between calls to stay within the free
tier rate limit (20 requests/minute, 50 requests/day).

### Offline demo (no API key needed):
```
python src/run_eval.py --mock
```
Uses synthetic stand-in outputs to verify the pipeline and metrics work
end to end. Do not use mock results in the final report.

---

## Output files

After a real run:
- `results/eval_results.json` — full structured report including:
  - `metric_definitions`: name, type, definition, logic for all 3 metrics
  - `results`: 20 rows (10 scenarios x 2 strategies) with scores
  - `summary`: per-strategy averages + overall_average composite
- `results/eval_results.csv` — flat table of raw scores

---

## Repo structure

```
email-generation-assistant/
  prompts/
    advanced_prompt.txt   # role-playing + few-shot + chain-of-thought prompt
    naive_prompt.txt      # zero-shot baseline for comparison
  data/
    scenarios.json        # 10 test scenarios with human reference emails
  src/
    generate.py           # prompt rendering + OpenRouter API calls
    metrics.py            # 3 custom metric implementations
    run_eval.py           # main runner: generates, scores, writes output
  results/
    eval_results.json     # full structured output (generated on run)
    eval_results.csv      # flat scores table (generated on run)
  report/
    final_report.md       # completed report with real evaluation numbers
  requirements.txt
  README.md
```

---

## Prompting techniques (Part 1B)

`prompts/advanced_prompt.txt` uses three documented techniques:
1. **Role-Playing**: model assigned a "senior professional communications specialist" persona
2. **Few-Shot**: two worked input/output examples anchor style and format
3. **Chain-of-Thought scaffold**: model instructed to silently plan before writing

`prompts/naive_prompt.txt` is a zero-shot baseline: no persona, no examples, no reasoning scaffold.

---

## Metrics (Part 2B)

1. **Fact Inclusion Rate** — deterministic, containment-based keyword matching
2. **Tone Alignment Score** — LLM-as-judge (OpenRouter, temperature=0)
3. **Structural Conciseness Score** — hybrid (word count + Flesch readability + structure checks)

Full definitions and logic in `src/metrics.py` and in `results/eval_results.json`.

---

## Deactivate the virtual environment when done
```
deactivate
```
