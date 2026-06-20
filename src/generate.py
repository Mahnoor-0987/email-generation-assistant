"""
generate.py
Calls OpenRouter API using the OpenAI SDK as a drop-in replacement.
Per official docs: https://openrouter.ai/docs/quickstart

Model: openrouter/free — official Free Models Router, auto-selects best
  available free model per request.
Rate limits (free tier): 50 req/day, 20 req/min.
5-second delay in run_eval.py keeps us at 12 req/min safely.
"""

import os
import re
import time

from openai import OpenAI

MODEL = "openrouter/free"


def _get_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENROUTER_API_KEY not set.\n"
            "1. Get a free key at https://openrouter.ai\n"
            "2. PowerShell: $env:OPENROUTER_API_KEY=\"sk-or-...\""
        )
    return OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/Mahnoor-0987/email-generation-assistant",
            "X-Title": "Email Generation Assistant",
        },
    )


def load_template(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def render_prompt(template: str, intent: str, facts: list, tone: str) -> str:
    return (
        template
        .replace("{intent}", intent)
        .replace("{facts}", "; ".join(facts))
        .replace("{tone}", tone)
    )


def extract_email(raw_text: str) -> str:
    """Extract from <email> tags if present, else return as-is.
    Guards against None content (empty API response / content filter)."""
    if not raw_text:
        return ""
    match = re.search(r"<email>(.*?)</email>", raw_text, re.DOTALL)
    return match.group(1).strip() if match else raw_text.strip()


def call_llm(prompt: str, temperature: float = 0.7) -> str:
    """
    Call OpenRouter per official docs (OpenAI SDK drop-in).
    Retries up to 3 times on errors or empty/None content responses.
    max_tokens=1024: emails need ~300 tokens.
    """
    client = _get_client()
    for attempt in range(3):
        try:
            response = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            # Guard: free router may return None content on content-filter or
            # transient empty responses — treat as retriable failure
            if not content or not content.strip():
                raise ValueError("API returned empty content (possible content filter or transient error)")
            return content
        except Exception as e:
            if attempt < 2:
                wait = 10 * (attempt + 1)
                print(f"  Attempt {attempt+1}/3 failed ({e}), retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise RuntimeError(
                    f"All 3 attempts failed for this scenario. Last error: {e}"
                ) from e


def generate_email(strategy: str, scenario: dict, prompts_dir: str = "prompts") -> str:
    template_path = os.path.join(prompts_dir, f"{strategy}_prompt.txt")
    template = load_template(template_path)
    prompt = render_prompt(
        template, scenario["intent"], scenario["key_facts"], scenario["tone"]
    )
    raw = call_llm(prompt)
    return extract_email(raw)


def make_judge_fn():
    """Judge at temperature=0 for reproducible scoring."""
    def judge(prompt: str) -> str:
        return call_llm(prompt, temperature=0.0)
    return judge
