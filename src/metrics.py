"""
metrics.py
Three custom metrics for judging generated emails.

1. Fact Inclusion Rate (deterministic)
   Definition: the fraction of input key_facts that are actually represented
   in the generated email.
   Logic: for each fact, strip stopwords and tokenize into significant
   keywords. Use containment scoring (fraction of the fact's keywords found
   in a sentence or 2-sentence window) rather than Jaccard, so naturally
   rephrased facts still match even when surrounded by many extra words.
   The fact counts as "included" if its best window score clears a
   containment threshold. Fully deterministic, no external dependencies.
   Score = facts_included / total_facts, range 0-1.

2. Tone Alignment Score (LLM-as-judge)
   Definition: how well the email's actual tone matches the requested tone.
   Logic: a judge model is given the target tone, a fixed 1-5 rubric, and the
   email, and returns a single integer score. This is delegated to an LLM
   because "does this read as urgent / empathetic / formal" is a judgment
   call that simple keyword rules can't capture reliably.
   Score = judge_score / 5, range 0-1. A non-LLM heuristic fallback is
   included for offline/mock runs (keyword + punctuation cues), clearly
   weaker and only meant as a placeholder when no API key is available.

3. Structural Conciseness Score (hybrid)
   Definition: whether the email is appropriately concise and properly
   formatted, independent of tone or fact content.
   Logic: averages three checks -
     a) word count falls inside an ideal band (60-200 words), scored by
        distance outside the band
     b) Flesch reading-ease score above a minimum threshold (60), via
        textstat
     c) presence of a subject line, a greeting, and a sign-off (regex /
        keyword presence checks)
   Score = average of the three sub-checks, range 0-1.
"""

import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "is", "are", "was", "were", "be",
    "to", "of", "in", "on", "for", "with", "by", "at", "as", "this", "that",
    "it", "its", "we", "our", "i", "you", "your", "they", "their", "will",
    "has", "have", "had", "from", "into", "than", "then", "so", "if",
    "about", "would", "could", "should", "can", "do", "does", "not", "no",
}


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 1}


def _split_sentences(text: str) -> list:
    return [s.strip() for s in re.split(r"[.!?\n]+", text) if s.strip()]


def fact_inclusion_rate(email: str, key_facts: list, threshold: float = 0.55) -> float:
    """
    Containment-based, not Jaccard: scores what fraction of a fact's
    significant keywords show up near each other in the email, regardless
    of how many other words surround them. Checks single sentences and
    2-sentence windows so a fact split across a comma/clause boundary by
    the simple sentence splitter still gets matched fairly.
    """
    if not key_facts:
        return 1.0
    sentences = _split_sentences(email)
    sentence_tokens = [_tokenize(s) for s in sentences]
    windows = list(sentence_tokens)
    for i in range(len(sentence_tokens) - 1):
        windows.append(sentence_tokens[i] | sentence_tokens[i + 1])

    included = 0
    for fact in key_facts:
        fact_tokens = _tokenize(fact)
        if not fact_tokens:
            continue
        best = 0.0
        for wtoks in windows:
            if not wtoks:
                continue
            containment = len(fact_tokens & wtoks) / len(fact_tokens)
            best = max(best, containment)
        if best >= threshold:
            included += 1
    return round(included / len(key_facts), 3)


def _heuristic_tone_score(email: str, tone: str) -> float:
    """Offline fallback when no judge model is available (used in --mock runs)."""
    text = email.lower()
    cues = {
        "formal": ["dear", "sincerely", "regards", "kindly"],
        "casual": ["hey", "cheers", "thanks!", "just wanted"],
        "urgent": ["urgent", "immediately", "asap", "critical", "right away"],
        "empathetic": ["sorry", "understand", "apologize", "appreciate", "truly"],
        "persuasive": ["would you", "imagine", "free", "offer", "opportunity"],
        "polite but firm": ["unable", "however", "appreciate", "unfortunately"],
        "warm": ["grateful", "wonderful", "appreciate", "so glad"],
    }
    tone_key = tone.lower()
    matched = 0
    keywords = []
    for key, words in cues.items():
        if key in tone_key:
            keywords = words
            break
    if not keywords:
        return 0.6  # neutral default if tone label isn't in our cue table
    for w in keywords:
        if w in text:
            matched += 1
    return round(min(1.0, 0.4 + 0.15 * matched), 3)


def tone_alignment_score(email: str, tone: str, judge_fn=None) -> float:
    if judge_fn is not None:
        rubric = (
            f"Rate how well this email matches the tone '{tone}' on a scale of 1-5, "
            f"where 1 = opposite tone and 5 = perfectly matches. "
            f"Reply with ONLY the integer.\n\nEmail:\n{email}"
        )
        raw = judge_fn(rubric)
        digits = re.findall(r"[1-5]", raw.strip())
        score = int(digits[0]) if digits else 3
        return round(score / 5, 3)
    return _heuristic_tone_score(email, tone)


def structural_conciseness_score(email: str) -> float:
    words = re.findall(r"[a-zA-Z']+", email)
    word_count = len(words)
    if 60 <= word_count <= 200:
        length_score = 1.0
    else:
        distance = min(abs(word_count - 60), abs(word_count - 200))
        length_score = max(0.0, 1 - distance / 100)

    try:
        import textstat
        readability = textstat.flesch_reading_ease(email)
        readability_score = 1.0 if readability >= 60 else max(0.0, readability / 60)
    except Exception:
        readability_score = 0.7  # neutral fallback if textstat isn't installed

    has_subject = bool(re.search(r"subject\s*:", email, re.IGNORECASE))
    has_greeting = bool(re.search(r"^(dear|hi|hey|hello)\b", email.strip(), re.IGNORECASE | re.MULTILINE))
    has_signoff = bool(re.search(r"(regards|sincerely|best|cheers|thanks)[,!.]?\s*\n", email, re.IGNORECASE))
    structure_score = sum([has_subject, has_greeting, has_signoff]) / 3

    return round((length_score + readability_score + structure_score) / 3, 3)


def score_email(email: str, scenario: dict, judge_fn=None) -> dict:
    return {
        "fact_inclusion_rate": fact_inclusion_rate(email, scenario["key_facts"]),
        "tone_alignment_score": tone_alignment_score(email, scenario["tone"], judge_fn),
        "structural_conciseness_score": structural_conciseness_score(email),
    }
