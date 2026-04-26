#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
FIELD_ORDER = [
    "invoice_number",
    "vendor_name",
    "date",
    "total_amount",
    "currency",
]
DEFAULT_PROVIDER = "anthropic"
DEFAULT_MODELS = {
    "anthropic": "claude-sonnet-4-6",
    "openai": "gpt-4.1-mini",
    "gemini": "gemini-2.5-flash",
}
PROVIDER_ENV_VARS = {
    "anthropic": "ANTHROPIC_API_KEY",
    "openai": "OPENAI_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

SYSTEM_PROMPT = """You are an invoice data extraction system.

Given OCR text from a scanned invoice, extract the following fields:
- invoice_number (string)
- vendor_name (string)
- date (ISO 8601 format)
- total_amount (number)
- currency (string, e.g. "USD")

Rules:
- Return a JSON object with the extracted fields.
- Include the original input text in a "raw_input" field for traceability.
- If a field cannot be determined from the text, use null.
- If a field is ambiguous, prefer null instead of guessing.
- Do not guess or invent values.
- For each field, include a confidence level: high, medium, or low.
- Use modified=true only when you corrected OCR noise, expanded a corrupted token, or inferred beyond a direct read.
- Do not mark a field as modified for simple normalization alone, such as formatting a clear date as ISO 8601 or parsing a clear amount into a number.

Interpretation guidance:
- "total_amount" means the final amount due on the invoice, not subtotal or balance previously paid, unless the document clearly indicates a different payable total.
- If multiple candidate totals exist and the final payable amount is ambiguous, return null with low confidence.
- If the invoice date format is ambiguous (for example 04/06/2026 with no locale signal), return null with low confidence.

Return only the JSON. No explanation, no commentary."""

EXTRACTION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "raw_input": {"type": "string"},
        "invoice_number": {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "modified": {"type": "boolean"},
            },
            "required": ["value", "confidence", "modified"],
            "additionalProperties": False,
        },
        "vendor_name": {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "modified": {"type": "boolean"},
            },
            "required": ["value", "confidence", "modified"],
            "additionalProperties": False,
        },
        "date": {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "modified": {"type": "boolean"},
            },
            "required": ["value", "confidence", "modified"],
            "additionalProperties": False,
        },
        "total_amount": {
            "type": "object",
            "properties": {
                "value": {"type": ["number", "null"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "modified": {"type": "boolean"},
            },
            "required": ["value", "confidence", "modified"],
            "additionalProperties": False,
        },
        "currency": {
            "type": "object",
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                "modified": {"type": "boolean"},
            },
            "required": ["value", "confidence", "modified"],
            "additionalProperties": False,
        },
    },
    "required": ["raw_input", "invoice_number", "vendor_name", "date", "total_amount", "currency"],
    "additionalProperties": False,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract structured invoice data from a .txt file or a directory of .txt files."
    )
    parser.add_argument("path", help="Path to a .txt invoice file or a directory containing .txt files.")
    parser.add_argument(
        "--provider",
        choices=sorted(DEFAULT_MODELS),
        default=DEFAULT_PROVIDER,
        help=f"Model provider to use. Defaults to {DEFAULT_PROVIDER}.",
    )
    parser.add_argument(
        "--model",
        help="Override the default model for the selected provider.",
    )
    return parser.parse_args()


def resolve_input_files(raw_path: str) -> list[Path]:
    path = Path(raw_path).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    path = path.resolve()

    if not path.exists():
        raise FileNotFoundError(f"Input path does not exist: {path}")

    if path.is_file():
        if path.suffix.lower() != ".txt":
            raise ValueError(f"Input file must be a .txt file: {path}")
        return [path]

    if path.is_dir():
        files = sorted(file for file in path.iterdir() if file.is_file() and file.suffix.lower() == ".txt")
        if not files:
            raise ValueError(f"No .txt files found in directory: {path}")
        return files

    raise ValueError(f"Unsupported input path: {path}")


def get_api_key(provider: str) -> str:
    env_var = PROVIDER_ENV_VARS[provider]
    api_key = os.getenv(env_var)
    if not api_key:
        raise RuntimeError(f"{env_var} is not set.")
    return api_key


def default_model_for(provider: str) -> str:
    return DEFAULT_MODELS[provider]


def extract_invoice(provider: str, model: str, invoice_path: Path) -> dict[str, Any]:
    raw_text = invoice_path.read_text(encoding="utf-8")

    if provider == "anthropic":
        data = extract_with_anthropic(model, raw_text)
    elif provider == "openai":
        data = extract_with_openai(model, raw_text)
    elif provider == "gemini":
        data = extract_with_gemini(model, raw_text)
    else:  # pragma: no cover - argparse enforces choices
        raise RuntimeError(f"Unsupported provider: {provider}")

    data["raw_input"] = raw_text
    data["provider"] = provider
    data["model"] = model
    data["source_file"] = invoice_path.name
    return data


def extract_with_anthropic(model: str, raw_text: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "max_tokens": 1200,
        "system": SYSTEM_PROMPT,
        "messages": [{"role": "user", "content": raw_text}],
        "output_config": {
            "format": {
                "type": "json_schema",
                "schema": EXTRACTION_SCHEMA,
            }
        },
    }
    response = post_json(
        url="https://api.anthropic.com/v1/messages",
        headers={
            "content-type": "application/json",
            "x-api-key": get_api_key("anthropic"),
            "anthropic-version": "2023-06-01",
        },
        payload=payload,
    )

    stop_reason = response.get("stop_reason")
    if stop_reason == "refusal":
        raise RuntimeError("Model refused the request.")
    if stop_reason == "max_tokens":
        raise RuntimeError("Model hit max_tokens.")

    content = response.get("content", [])
    payload_text = "".join(block.get("text", "") for block in content if block.get("type") == "text")
    if not payload_text:
        raise RuntimeError("No JSON payload returned by Anthropic.")
    return json.loads(payload_text)


def extract_with_openai(model: str, raw_text: str) -> dict[str, Any]:
    payload = {
        "model": model,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": raw_text},
        ],
        "max_output_tokens": 1200,
        "text": {
            "format": {
                "type": "json_schema",
                "name": "invoice_extraction",
                "schema": EXTRACTION_SCHEMA,
                "strict": True,
            }
        },
    }
    response = post_json(
        url="https://api.openai.com/v1/responses",
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {get_api_key('openai')}",
        },
        payload=payload,
    )

    if response.get("status") == "incomplete":
        reason = ((response.get("incomplete_details") or {}).get("reason")) or "unknown"
        raise RuntimeError(f"OpenAI returned an incomplete response: {reason}")

    output = response.get("output", [])
    if not output:
        raise RuntimeError("No output returned by OpenAI.")

    content = output[0].get("content", [])
    if not content:
        raise RuntimeError("No content returned by OpenAI.")

    first_item = content[0]
    if first_item.get("type") == "refusal":
        raise RuntimeError(first_item.get("refusal", "OpenAI refused the request."))
    if first_item.get("type") != "output_text":
        raise RuntimeError(f"Unexpected OpenAI content type: {first_item.get('type')}")

    payload_text = first_item.get("text", "")
    if not payload_text:
        raise RuntimeError("No JSON payload returned by OpenAI.")
    return json.loads(payload_text)


def extract_with_gemini(model: str, raw_text: str) -> dict[str, Any]:
    payload = {
        "systemInstruction": {
            "parts": [{"text": SYSTEM_PROMPT}],
        },
        "contents": [
            {
                "parts": [{"text": raw_text}],
            }
        ],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": EXTRACTION_SCHEMA,
        },
    }
    response = post_json(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "content-type": "application/json",
            "x-goog-api-key": get_api_key("gemini"),
        },
        payload=payload,
    )

    candidates = response.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates returned by Gemini.")

    finish_reason = candidates[0].get("finishReason")
    if finish_reason and finish_reason not in {"STOP", "MAX_TOKENS"}:
        raise RuntimeError(f"Gemini returned finishReason={finish_reason}")
    if finish_reason == "MAX_TOKENS":
        raise RuntimeError("Gemini hit max tokens.")

    parts = (((candidates[0].get("content") or {}).get("parts")) or [])
    payload_text = "".join(part.get("text", "") for part in parts if "text" in part)
    if not payload_text:
        raise RuntimeError("No JSON payload returned by Gemini.")
    return json.loads(payload_text)


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--request",
        "POST",
        url,
        "--data-binary",
        "@-",
    ]
    for key, value in headers.items():
        command.extend(["--header", f"{key}: {value}"])

    completed = subprocess.run(
        command,
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        detail = stdout or stderr or f"curl exited with code {completed.returncode}"
        raise RuntimeError(f"Request to {url} failed: {detail}")

    try:
        return json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {url}: {completed.stdout.decode('utf-8', errors='replace')}") from exc


def apply_routing_logic(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    notices: list[str] = []
    review_reasons: list[str] = []
    needs_review = False

    for field_name in FIELD_ORDER:
        field = result[field_name]
        confidence = field["confidence"]
        modified = field["modified"]

        if confidence == "low":
            notices.append(f"warning: {field_name} has low confidence")
            review_reasons.append(f"{field_name}:low_confidence")
            needs_review = True
        elif confidence != "high":
            notices.append(f"notice: {field_name} has {confidence} confidence")
            review_reasons.append(f"{field_name}:{confidence}_confidence")
            needs_review = True

        if modified:
            notices.append(f"notice: {field_name} was modified from the source text")
            review_reasons.append(f"{field_name}:modified")
            needs_review = True

    result["needs_review"] = needs_review
    result["review_reasons"] = review_reasons
    return result, notices


def write_output(provider: str, invoice_path: Path, result: dict[str, Any]) -> Path:
    provider_dir = OUTPUT_DIR / provider
    provider_dir.mkdir(parents=True, exist_ok=True)
    output_path = provider_dir / f"{invoice_path.stem}.json"
    output_path.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return output_path


def format_total(result: dict[str, Any]) -> str:
    amount = result["total_amount"]["value"]
    currency = result["currency"]["value"]
    if amount is None:
        return "-"
    if currency:
        return f"{amount:.2f} {currency}"
    return f"{amount:.2f}"


def build_summary_row(invoice_path: Path, result: dict[str, Any]) -> list[str]:
    invoice_number = result["invoice_number"]["value"] or "-"
    vendor_name = result["vendor_name"]["value"] or "-"
    review_status = "yes" if result["needs_review"] else "no"
    reasons = ", ".join(result["review_reasons"]) if result["review_reasons"] else "ok"
    return [
        result["provider"],
        invoice_path.name,
        invoice_number,
        vendor_name,
        format_total(result),
        review_status,
        reasons,
    ]


def print_summary(rows: list[list[str]]) -> None:
    headers = ["provider", "file", "invoice_number", "vendor_name", "total", "needs_review", "notes"]
    table = [headers, *rows]
    widths = [max(len(str(row[index])) for row in table) for index in range(len(headers))]

    def render(row: list[str]) -> str:
        return " | ".join(str(cell).ljust(widths[index]) for index, cell in enumerate(row))

    print("\nSummary")
    print(render(headers))
    print("-+-".join("-" * width for width in widths))
    for row in rows:
        print(render(row))


def main() -> int:
    args = parse_args()
    model = args.model or default_model_for(args.provider)

    try:
        invoice_files = resolve_input_files(args.path)
        get_api_key(args.provider)
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    summary_rows: list[list[str]] = []

    for invoice_path in invoice_files:
        print(f"\nProcessing {invoice_path.name} with {args.provider}:{model}")
        try:
            result = extract_invoice(args.provider, model, invoice_path)
            result, notices = apply_routing_logic(result)
            output_path = write_output(args.provider, invoice_path, result)
        except Exception as exc:  # pragma: no cover - API/runtime errors
            print(f"error: failed to process {invoice_path.name}: {exc}", file=sys.stderr)
            summary_rows.append([args.provider, invoice_path.name, "-", "-", "-", "error", str(exc)])
            continue

        for notice in notices:
            print(notice)
        print(f"saved: {output_path}")
        summary_rows.append(build_summary_row(invoice_path, result))

    print_summary(summary_rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
