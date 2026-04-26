# OK, It's a Probability Engine. So What?

---

If you accept the premise from the previous chapter — AI is not a conversation, it's a probability engine operating within the space you define — then the operating logic is clear.

Your job is not to "ask better questions." It's to narrow the space until AI can only give you something useful.

This chapter covers how. If it had a one-line summary, it would be: **AI application design starts with I/O design** — control what goes in, specify what comes out. Everything below is a specific instance of this idea.

We'll start with principles you can test in chat, then apply them to an API use case. The reason both work the same way is that chat and the API are the same thing — chat is just a UI that your model provider built on top of the API.

---

## Chat is a UI. The API is what's underneath.

Every element of the chat experience has a direct counterpart in the API:

| What you see in chat | What it is in the API |
|---|---|
| The invisible instructions that shape AI's behavior (ChatGPT's "Custom Instructions," Claude's "System Prompt" setting) | `system` message — sent before every conversation, sets the AI's role and constraints |
| Your first message | `user` message — the input the model responds to |
| AI's reply | `assistant` message — the model's generated output |
| The conversation history above your current message | An array of previous `user` and `assistant` messages, sent with every request |
| "Reply in JSON" or structured output toggles | `response_format` — a schema that constrains the output structure |
| Adjusting "creativity" or "temperature" sliders | `temperature` parameter — controls how much randomness the model uses when sampling |

Why does this matter? Because when you learn to use AI effectively in chat — giving clear instructions, structuring your input, specifying your output format — you're already learning API design. The only difference is that in chat, you do it manually every time. In the API, you write it once and it runs automatically.

This is the bridge from "I can use AI" to "I can build with AI." Every principle in this chapter works in both contexts. We'll start in chat because it's faster to experiment, then show the same ideas as code.

---

## Your first message sets the direction

Human conversation can unfold slowly. You chat for a bit, the other person asks some questions, you gradually align, and eventually get to the point.

AI can't do this.

The reason is straightforward: AI's context window is finite, and the longer the conversation gets, the more likely early content is to be compressed or lost. If you save important context for turn five or turn eight, AI may have already been running in the wrong direction for several turns, and the conditions you set early on are starting to fade.

Front-load everything. When AI starts from the right space in turn one, every subsequent output is better. Not because the first message has some magical weight bonus, but because when the direction is right, you don't waste turns correcting course.

---

## SPEC: a checklist before you hit send

Before typing anything, spend one minute thinking about four things:

**Goal — What outcome do you want?**

Not "help me write a proposal," but "I need the reader of this proposal to approve the budget for this project, not just think 'looks good' and forget about it." The first is what you want AI to do. The second is what you want to achieve — and AI's output will be completely different. The more specific, the more controllable the output. A vague goal gets a vague answer — not because AI is lazy, but because it picked the statistically safest direction in too large a space.

**Reference — What materials does AI need?**

Your domain knowledge, relevant documents, existing standards, things you've built before. Give all of it in the first message. Don't expect AI to know what industry you're in, what standards your company uses, or who your audience is. Its "knowledge" is the statistical result of training data, not an understanding of your situation.

**Output — What should the output look like?**

Format, length, structure — specify all of it. "Give me bullet points, each no more than two sentences" produces something completely different from "give me a full analysis report." If you don't specify, AI defaults to its statistically most common output format — usually a long, balanced, says-everything-but-nothing-deeply kind of text.

**Checkpoints — How do you verify?**

The previous chapter covered this: AI's answers always sound confident. You can't rely on "does it read well" to judge quality, because it always reads well.

Set the rules upfront: "Every conclusion must include its basis. Every analysis must list its assumptions and show the reasoning chain."

A note on this: there's an active debate about whether asking AI to "show its reasoning" (chain-of-thought) actually improves the quality of its output. Research suggests the reasoning AI displays isn't always faithful to how it actually arrived at the answer. That debate matters for AI researchers, but it's beside the point here. The reason you ask for reasoning isn't because you trust AI's chain of thought — it's because having the reasoning laid out lets *you* think through it yourself. You're not outsourcing judgment. You're using AI's output as a scaffold to run your own verification: does this logic hold? Are the assumptions stated? Is there a gap between step 2 and step 3? If you spot jumps or unsupported leaps, the conclusion is usually wrong.

When you need maximum rigor, go further: require AI to cite its sources explicitly — which document, which section, which line. If it can't point to where it got the information, it's probably generating rather than retrieving. This is especially important when you've loaded reference materials and expect AI to work from them, not from its training data.

---

## Persist the output

This sounds minor, but it might be the most important operating principle in this chapter.

The core idea: AI's output should be durable and reusable, not trapped in a conversation that's about to forget it.

In chat, this means: don't let AI respond in the chat window — have it write the result to a file. In an API context, this is already the default — you get structured data back and store it. But the principle is the same either way: treat AI output as an artifact you keep, not a message you read once.

Why this matters:

**Context window is a finite resource.** AI's response itself takes up context window space. In chat, a long response permanently consumes your limited space. Output to a file, and the conversation history only retains "I've written the result to the file." In an API pipeline, the same logic applies — if you stuff previous outputs back into the next prompt without summarizing or selecting, you're burning context on stale data.

**Length limits.** AI has a maximum output length per response. When your needs are complex — a full analysis report, a technical document — it will omit details and compress arguments to fit. Writing to a file (or requesting structured output via API) relaxes this constraint.

**Portability.** Chat logs are hard to reuse. API responses in memory disappear when the process ends. But persisted artifacts — files, database records, structured outputs — can be loaded into the next conversation, the next pipeline step, or a completely different system. Context is never truly lost — it just changes carriers.

This is why designing your response schema matters. In an API pipeline, you decide what gets saved, in what structure, and what gets carried forward to the next step. This is your "memory" — not the AI's. If you let AI decide what's worth remembering, you're back to the same problem from Chapter 1: an opaque system making decisions you can't see or control. Design your persistence deliberately.

---

## Case 1: Writing documents with AI (SPEC in action)

Let's start with a chat example to see SPEC in action before we move to application design.

You need to write a document — a technical design doc, a project proposal, a client report.

**What you give in the first message:**
- All reference documents
- Who the reader is (engineers? executives? clients?)
- What reaction you want from the reader after reading. This has two dimensions. First, what stage is the document at:
  - "I have a rough idea, I want feedback on whether it's worth pursuing"
  - "This is a high-level design, I need a gut check on the approach"
  - "This is a complete HLD, I want the team to stress-test risks"
  - "This is a detailed LLD, I want the team to discuss implementation specifics"

  Second, what's your intent — are you genuinely seeking feedback, or driving alignment toward a specific direction? Same document stage, very different tone and structure. Tell AI which one, and the output changes accordingly.
- Expected reading time (this directly affects AI's length and detail density)
- Your outline

**Why audience and goal matter most:**

The same project, written for engineers vs. written for executives, produces completely different documents. Engineers want technical details and trade-off analysis. Executives want business impact and timeline. If you don't specify, AI writes a document that "has a little of everything but doesn't feel right to anyone" — because it doesn't know which direction to constrain toward.

AI's first draft is always a starting point, never the final product. Iterate from there.

Notice what you just did: you defined a goal, provided reference materials, specified the output format, and set up checkpoints for verification — all before AI generated a single word. In a chat window, you do this manually every time. In an application, you bake it in once. That's the only difference.

---

## Case 2: Designing a system prompt for structured extraction

Now let's take the same SPEC thinking and bake it into a system.

You're building an API endpoint: users send unstructured text (an invoice, a support ticket, a contract clause), and AI returns structured JSON. This is the same problem from Chapter 1's invoice example — but now it's not a one-off chat interaction. It's a system that needs to work reliably, hundreds of times, without a human reviewing every output.

**The system prompt is your SPEC, baked in:**

- **Goal:** "Extract the following fields from the input text: vendor_name, date, total_amount, currency."
- **Reference:** "The input will be OCR output from scanned invoices. Expect noise: misread characters, inconsistent formatting, missing fields."
- **Output:** "Return a JSON object. If a field cannot be determined, use null. Do not invent values."
- **Checkpoints:** "For each field, include a confidence level (high / medium / low) and whether the value was modified from the original text. Your application code decides the routing logic — e.g., any low confidence or modified field triggers human review."

**What this looks like as a system prompt:**

```
You are an invoice data extraction system.

Given OCR text from a scanned invoice, extract the following fields:
- vendor_name (string)
- date (ISO 8601 format)
- total_amount (number)
- currency (string, e.g. "USD")

Rules:
- Return a JSON object with the extracted fields.
- Include the original input text in a "raw_input" field for traceability.
- If a field cannot be determined from the text, use null.
- Do not guess or invent values.
- For each field, include a confidence level: high, medium, or low.
- If you corrected an OCR error or inferred a value, mark that field as "modified": true.

Return only the JSON. No explanation, no commentary.

Example output:
{
  "raw_input": "Vendr: Acme Corp\nDte: Jannuary 3, 2026\nTotal: $1,250.00 USD",
  "vendor_name": {"value": "Acme Corp", "confidence": "high", "modified": false},
  "date": {"value": "2026-01-03", "confidence": "high", "modified": true},
  "total_amount": {"value": 1250.00, "confidence": "high", "modified": false},
  "currency": {"value": "USD", "confidence": "high", "modified": false}
}
```

**Notice what this prompt is doing:**

Every SPEC element is here — goal (extract these fields), reference (OCR text, expect noise), output (JSON schema, null for missing), checkpoints (confidence levels, human review flag). The only difference from the chat version is that you wrote it once, and it runs every time without you being in the loop.

The confidence and modified fields are the key design decisions. You can't review every output manually, so you build the verification into the prompt itself — AI flags its own uncertainty and marks when it changed the original input. Your application code then decides the routing logic: maybe any low-confidence field triggers human review, or maybe modified fields get spot-checked in a weekly audit. This is what "push P(result == expected) toward 1" looks like in production: not perfection, but a system that knows when it's not sure and when it made a judgment call.

---

## Build your first AI application

You just read the system prompt. Now run it.

The [`examples/`](examples/) folder contains a working Python script that takes this exact invoice extraction prompt, calls the API (Anthropic, OpenAI, or Gemini — your choice), enforces structured JSON output, applies routing logic based on confidence levels, and persists the results to files.

Four sample invoices are included — one clean, one with OCR noise, one with missing fields, one with ambiguous data. Run all four and watch how the same prompt produces different confidence levels across different inputs and different providers. That's the probability engine in action. That's why the routing layer isn't optional.

```bash
cd 02-how-to-operate/examples
export ANTHROPIC_API_KEY="your-key"
python extract_invoice.py invoices/
```

See [`examples/README.md`](examples/README.md) for setup details, provider options, and expected results.

---

## Back to the core

Different cases emphasize different principles, but they all draw from the same toolkit:

1. **All context in, one shot** — memory decays and you don't get a second chance to set the direction. Front-load everything.
2. **Specify the output format** — because AI has no judgment to decide what format best serves your needs
3. **Persist the output** — because the context window is a finite physical resource, and your outputs need to outlive the conversation
4. **Check the reasoning, not the conclusion** — because AI's conclusions always look reasonable; reasoning is where problems surface

This isn't "prompt engineering tips." These are operating principles derived from the fact that AI is a probability model. You're not learning how to communicate with AI. You're learning how to design the input and output conditions of a probability engine — and to bridge the gap from manual chat interactions to production systems.

Big difference.
