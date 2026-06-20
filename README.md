# Email Generation Assistant

A prototype that generates professional emails from (intent, key facts, tone),
plus a custom evaluation harness comparing an advanced prompting strategy
against a naive baseline on the same model (Gemini 2.5 Flash, free tier).

---

## Setup

### 1. Clone the repo
```
git clone https://github.com/YOUR-USERNAME/email-generation-assistant.git
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

You should see `(venv)` at the start of your terminal prompt. All following
commands must be run with the venv active.

### 3. Install dependencies
```
pip install -r requirements.txt
```

### 4. Get a free Gemini API key
Go to https://aistudio.google.com — sign in with any Google account, no
credit card needed. Click "Get API key" → "Create API key". Copy the key.

### 5. Set the API key in your terminal

Mac / Linux:
```
export GEMINI_API_KEY="your-key-here"
```

Windows (Command Prompt):
```
set GEMINI_API_KEY=your-key-here
```

Windows (PowerShell):
```
$env:GEMINI_API_KEY="your-key-here"
```

This must be set in the same terminal session you run the script from.

---

## Run

### Real evaluation (recommended, needs API key):
```
python src/run_eval.py
```
Calls Gemini ~40 times (generation + judging). Takes 2-5 minutes.
Well within the free daily limit of ~1,500 requests.

### Offline demo (no API key needed):
```
python src/run_eval.py --mock
```
Uses synthetic stand-in outputs to prove the pipeline and metrics work
end to end. Do not submit this as your real evaluation.

---

## Output files

After a real run:
- `results/eval_results.json` — full structured report:
  - `metric_definitions`: name, type, definition, logic for all 3 metrics
  - `results`: 20 rows (10 scenarios x 2 strategies) with scores
  - `summary`: per-strategy averages + overall_average composite
- `results/eval_results.csv` — flat table of raw scores, paste into report

---

## Repo structure

```
email_assistant/
  prompts/
    advanced_prompt.txt   # role-playing + few-shot + chain-of-thought prompt
    naive_prompt.txt      # zero-shot baseline for comparison
  data/
    scenarios.json        # 10 test scenarios with human reference emails
  src/
    generate.py           # prompt rendering + Gemini API calls
    metrics.py            # 3 custom metric implementations
    run_eval.py           # main runner: generates, scores, writes output
  results/
    eval_results.json     # full structured output (generated on run)
    eval_results.csv      # flat scores table (generated on run)
  report/
    final_report_template.md  # fill in with real numbers after running
  requirements.txt
  README.md
```

---

## Prompting techniques used (Part 1B)

`prompts/advanced_prompt.txt` uses three documented techniques:
1. Role-Playing: model is assigned a "senior professional communications specialist" persona
2. Few-Shot: two worked input/output examples anchor style and format
3. Chain-of-Thought scaffold: model is told to privately plan before writing, then output only the final email

`prompts/naive_prompt.txt` is a zero-shot baseline with no persona, no examples, no reasoning scaffold.

---

## Metrics (Part 2B)

1. Fact Inclusion Rate — deterministic, containment-based
2. Tone Alignment Score — LLM-as-judge (Gemini, temperature=0)
3. Structural Conciseness Score — hybrid (word count band + Flesch readability + structure checks)

Full definitions and logic are in `src/metrics.py` and in the JSON output file.

---

## Deactivate the virtual environment when done
```
deactivate
```
