# GenAI Playbook

### A practical engineering guide to building AI applications — from first principles to production.

---

Most engineers know that AI is probabilistic. Almost none of them design software that way.

This guide starts from one fact — **AI is a probability engine, not a conversation partner** — and derives the engineering principles, mental models, and design patterns that follow.

Each chapter pairs a core idea with runnable examples: prompt comparisons, code you can clone, and before/after breakdowns.

This is not an awesome-list. Not an API tutorial. Not a prompt template collection.

## Who this is for

Engineers who are building (or about to build) applications that use AI. You don't need ML background. You do need to be comfortable reading code.

## Chapters

| # | Title | Status |
|---|-------|--------|
| 01 | [You're Not Talking to AI. You're Configuring a Probability Engine.](01-not-a-conversation/) | 🚧 Draft |
| 02 | [OK, It's a Probability Engine. So What?](02-how-to-operate/) | 🚧 Draft |
| 03 | Context Ownership | 🔜 Coming |
| 04 | RAG: Retrieval | 🔜 Coming |
| 05 | RAG: Generation | 🔜 Coming |
| 06 | Evaluation | 🔜 Coming |
| 07 | Cost & Latency | 🔜 Coming |
| 08 | Orchestration & Agents | 🔜 Coming |
| 09 | Guardrails & Safety | 🔜 Coming |

## Core ideas

**AI is probabilistic, not deterministic.** Every design decision flows from this. Error handling, output validation, prompt structure, evaluation — all of it changes when you stop treating AI output as reliable and start treating it as a distribution you need to constrain.

**Control the input space, control the output quality.** AI doesn't have judgment. It has statistics. The less freedom you give it, the better the output. Freedom is not a feature — it's where quality collapses.

**Chat is a prototype, not a production interface.** Use chat to validate ideas. Then extract the workflow, fix the structure, and automate it. Staying in chat is O(n) on your time.

## How to read this

Start with Chapter 01. It reframes how you think about AI. Then Chapter 02 gives you the operating principles. Everything after that is application of these two ideas to specific engineering problems.

Each chapter is a folder with a `README.md` containing the essay, examples, and prompts you can study and use. Later chapters may include runnable code.

## License

[MIT](LICENSE)
