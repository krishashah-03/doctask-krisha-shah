"""Run the real extraction prompt against a document from the command line.

Reuses the same SYSTEM_PROMPT, schema, and deterministic offset-grounding as
the actual pipeline (app/graph/nodes/extract.py) — this is a harness around
that logic, not a separate copy of it. Useful for trying a document against
a provider/model without spinning up Postgres or the FastAPI app.

Examples:
    python scripts/extract_cli.py samples/01_Contract_MSA_PO4471.txt
    python scripts/extract_cli.py samples/01_Contract_MSA_PO4471.txt --provider groq
    python scripts/extract_cli.py samples/01_Contract_MSA_PO4471.txt --provider ollama
"""

import argparse
import json
import sys
from pathlib import Path

from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.graph.nodes.extract import SYSTEM_PROMPT, ExtractionResult, _locate_span  # noqa: E402
from app.llm.client import get_llm_client  # noqa: E402

SAMPLES_DIR = Path(__file__).resolve().parents[1] / "samples"

PROVIDERS = ["mock", "ollama", "groq"]


def _build_client(provider: str | None):
    if provider is None:
        return get_llm_client()

    if provider == "mock":
        from app.llm.mock import MockLLMClient

        return MockLLMClient()
    if provider == "ollama":
        from app.llm.ollama import OllamaLLMClient

        return OllamaLLMClient()
    if provider == "groq":
        from app.llm.groq import GroqLLMClient

        return GroqLLMClient()

    raise SystemExit(f"Unknown provider {provider!r}; choose from {PROVIDERS}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "file",
        nargs="?",
        default=str(SAMPLES_DIR / "01_Contract_MSA_PO4471.txt"),
        help="Path to a text document (default: a sample contract)",
    )
    parser.add_argument(
        "--provider",
        choices=PROVIDERS,
        help="Override LLM_PROVIDER from .env for this run only",
    )
    args = parser.parse_args()

    document_text = Path(args.file).read_text(encoding="utf-8")
    client = _build_client(args.provider)

    response = client.complete(SYSTEM_PROMPT, document_text)

    print(f"provider={type(client).__name__} model={getattr(client, 'model', 'n/a')}")
    print(
        f"prompt_tokens={response.prompt_tokens} "
        f"completion_tokens={response.completion_tokens} "
        f"cost_usd={response.cost_usd}"
    )
    print()

    try:
        data = json.loads(response.content)
        result = ExtractionResult.model_validate(data)
    except (json.JSONDecodeError, ValidationError) as exc:
        print("Response did not validate against the extraction schema.")
        print("--- raw content ---")
        print(response.content)
        raise SystemExit(1) from exc

    cursor = 0
    grounded = 0
    print(f"=== {len(result.facts)} facts ===")
    for fact in result.facts:
        span = _locate_span(document_text, fact.fact_value, cursor)
        if span is None:
            print(f"  [ungrounded] {fact.fact_key}: {fact.fact_value!r}")
            continue
        char_start, char_end = span
        cursor = char_end
        grounded += 1
        print(f"  [{char_start}:{char_end}] {fact.fact_key}: {fact.fact_value!r} (confidence={fact.confidence})")
    print(f"\n{grounded}/{len(result.facts)} facts grounded with an exact source span")

    if result.detected_instructions:
        print(f"\n=== {len(result.detected_instructions)} detected instruction(s) ===")
        for instruction in result.detected_instructions:
            print(f"  {instruction.text!r}")


if __name__ == "__main__":
    main()
