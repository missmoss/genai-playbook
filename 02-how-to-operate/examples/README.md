# Invoice Extraction Example

This is the Chapter 2 invoice extraction example turned into working code, from system prompt to structured output, routing, and persisted JSON, with Anthropic, OpenAI, and Gemini providers.

## Setup

Set only one API key, based on the provider you plan to use:

```bash
# Anthropic
export ANTHROPIC_API_KEY="your-api-key"

# OpenAI
export OPENAI_API_KEY="your-api-key"

# Gemini
export GEMINI_API_KEY="your-api-key"
```

## Run

```bash
# Single file with Anthropic
python extract_invoice.py invoices/clean.txt

# Single file with OpenAI
python extract_invoice.py --provider openai invoices/clean.txt

# Single file with Gemini
python extract_invoice.py --provider gemini invoices/clean.txt

# Whole directory
python extract_invoice.py invoices/
```

The script writes one JSON file per invoice to `output/{provider}/` and prints a summary table at the end.

## Expected routing behavior

- `clean.txt`: all fields should be high confidence, with `needs_review: false`.
- `noisy.txt`: OCR corrections should produce multiple `modified: true` flags and at least some non-high confidence fields.
- `missing_fields.txt`: missing `invoice_number`, `date`, and `currency` should come back as `null` with low confidence, which triggers review.
- `ambiguous.txt`: the total and/or date should surface ambiguity, which should also trigger review instead of guessing.

**Cross-provider observation:** You'll notice that different providers handle edge cases differently given the exact same prompt. Some are more conservative (returning `null` with low confidence for ambiguous fields), while others confidently guess an answer. This is expected — it's the same probability engine principle from Chapter 1 playing out across different models. Your application-side routing logic (the `needs_review` flag and confidence checks) exists precisely to catch these differences. The prompt constrains; the routing verifies.

## Notes

- The script reads `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, or `GEMINI_API_KEY` directly from the environment, depending on `--provider`. It does not use a `.env` file.
- Default models are `claude-sonnet-4-6`, `gpt-4.1-mini`, and `gemini-2.5-flash`. Override any of them with `--model`.
- Structured output is enforced with each provider's JSON-schema-capable API, not prompt-only parsing.

## Back to Chapter 2

See [../README.md](../README.md) for the explanation behind the prompt design and routing logic.
