import json
import re

from app.llm.client import LLMClient, LLMResponse

# Matches "Some Label: rest of the line" — the plaintext contracts/invoices in
# this project are written in that style throughout.
_KEY_VALUE_RE = re.compile(r"(?m)^([A-Za-z][A-Za-z0-9 /\-]{2,40}):[ \t]*(.+)$")

# Phrases that indicate a sentence is an imperative addressed at an
# AI/automated system rather than a fact about the document's subject matter.
_INJECTION_TRIGGER_RE = re.compile(
    r"(?i)note to (?:the )?(?:processing )?system"
    r"|please (?:mark|skip|approve|ignore|proceed)"
    r"|ignore (?:all |any )?(?:previous|prior) instructions"
    r"|as an ai\b"
    r"|without (?:additional |further )?(?:human )?review"
)


def _merge_spans(spans: list[tuple[int, int]], text: str) -> list[tuple[int, int]]:
    if not spans:
        return []
    spans = sorted(spans)
    merged = [list(spans[0])]
    for start, end in spans[1:]:
        last = merged[-1]
        gap = text[last[1] : start] if start > last[1] else ""
        if start <= last[1] or gap.strip() == "":
            last[1] = max(last[1], end)
        else:
            merged.append([start, end])
    return [(s, e) for s, e in merged]


def _find_injection_spans(text: str) -> list[tuple[int, int]]:
    raw_spans = []
    for match in _INJECTION_TRIGGER_RE.finditer(text):
        prev_period = text.rfind(".", 0, match.start())
        start = prev_period + 1 if prev_period != -1 else 0
        while start < len(text) and text[start] in " \t\r\n":
            start += 1

        next_period = text.find(".", match.end())
        end = next_period + 1 if next_period != -1 else len(text)

        raw_spans.append((start, end))
    return _merge_spans(raw_spans, text)


def _in_any_span(pos: int, spans: list[tuple[int, int]]) -> bool:
    return any(start <= pos < end for start, end in spans)


def _mock_generate_deliverable(user_prompt: str) -> str:
    """Deterministic stand-in for deliverable drafting: one section per
    distinct fact_key, one citation per fact so every sentence traces back
    to a fact_id, as the real prompt requires.
    """
    facts = json.loads(user_prompt)["facts"]

    by_key: dict[str, list[dict]] = {}
    for fact in facts:
        by_key.setdefault(fact["fact_key"], []).append(fact)

    sections = []
    for fact_key, group in by_key.items():
        lines = []
        citations = []
        for fact in group:
            sentence = f"{fact_key.replace('_', ' ').capitalize()}: {fact['fact_value']}."
            lines.append(sentence)
            citations.append({"sentence": sentence, "fact_id": fact["fact_id"]})
        sections.append(
            {
                "title": fact_key.replace("_", " ").title(),
                "content": " ".join(lines),
                "citations": citations,
            }
        )

    return json.dumps({"sections": sections})


def _mock_examine_rule(user_prompt: str) -> str:
    """Deterministic stand-in for rule checking: understands "max_days"
    style numeric-bound rule_specs by matching facts whose key mentions
    "day"/"term", extracting the first integer in the value, and comparing.
    """
    data = json.loads(user_prompt)
    rule = data["rule"]
    facts = data["facts"]
    rule_spec = rule.get("rule_spec") or {}
    findings = []

    max_days = rule_spec.get("max_days")
    if max_days is not None:
        for fact in facts:
            key_lower = fact["fact_key"].lower()
            if "day" not in key_lower and "term" not in key_lower:
                continue
            number_match = re.search(r"\d+", fact["fact_value"])
            if not number_match:
                continue
            value = int(number_match.group())
            if value > max_days:
                findings.append(
                    {
                        "rule_id": rule["id"],
                        "document_id": fact["document_id"],
                        "char_start": fact.get("char_start"),
                        "char_end": fact.get("char_end"),
                        "severity": "high",
                        "description": f"{fact['fact_key']} = {value} exceeds max_days={max_days}",
                    }
                )

    return json.dumps({"findings": findings})


class MockLLMClient(LLMClient):
    """Deterministic, rule-based stand-in for a real LLM.

    Extracts "Label: value" lines as facts and flags any sentence that reads
    like an instruction directed at an AI/automated system, without ever
    acting on it. Lets extraction be exercised and tested with no API key.
    Also handles deliverable-drafting and rule-checking prompts, each
    detected by a marker phrase in the system prompt, with their own
    deterministic stand-ins.
    """

    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        if "deliverable-drafting engine" in system_prompt:
            content = _mock_generate_deliverable(user_prompt)
            return LLMResponse(
                content=content,
                prompt_tokens=len(user_prompt.split()),
                completion_tokens=len(content.split()),
                cost_usd=0.0,
            )

        if "compliance rule-checking engine" in system_prompt:
            content = _mock_examine_rule(user_prompt)
            return LLMResponse(
                content=content,
                prompt_tokens=len(user_prompt.split()),
                completion_tokens=len(content.split()),
                cost_usd=0.0,
            )

        text = user_prompt

        injection_spans = _find_injection_spans(text)
        detected_instructions = [
            {"text": text[start:end].strip(), "char_start": start, "char_end": end}
            for start, end in injection_spans
        ]

        facts = []
        for match in _KEY_VALUE_RE.finditer(text):
            if _in_any_span(match.start(), injection_spans):
                continue

            key, value = match.group(1), match.group(2)
            fact_key = re.sub(r"\s+", "_", key.strip().lower())
            facts.append(
                {
                    "fact_key": fact_key,
                    "fact_value": value,
                    "char_start": match.start(2),
                    "char_end": match.end(2),
                    "confidence": 0.9,
                }
            )

        payload = {"facts": facts, "detected_instructions": detected_instructions}
        content = json.dumps(payload)

        return LLMResponse(
            content=content,
            prompt_tokens=len(text.split()),
            completion_tokens=len(content.split()),
            cost_usd=0.0,
        )
