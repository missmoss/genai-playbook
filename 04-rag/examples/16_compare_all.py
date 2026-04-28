from __future__ import annotations

from collections import OrderedDict
from statistics import mean

from R00_shared import EMBEDDING_MODEL, OUTPUT_DIR, approx_token_count, ensure_output_dir, estimate_cost, load_json, require_file

APPROACH_FILES = [
    ("[02] Long context baseline", "baseline_results.json"),
    ("[03+04] Naive RAG", "rag_naive_results.json"),
    ("[05+06] RAG + structural metadata", "rag_structural_results.json"),
    ("[07+08] RAG + LLM-enriched tags", "rag_enriched_results.json"),
    ("[09] Structural metadata-aware retrieval (no story index)", "rag_structural_retrieval_results.json"),
    ("[10] Enriched metadata-aware retrieval (no story index)", "rag_enriched_retrieval_results.json"),
    ("[11] Combined metadata-aware retrieval (no story index)", "rag_combined_retrieval_results.json"),
    ("[12+13] Structural metadata-aware retrieval + story index", "rag_structural_retrieval_story_index_results.json"),
    ("[12+14] Enriched metadata-aware retrieval + story index", "rag_enriched_retrieval_story_index_results.json"),
    ("[12+15] Combined metadata-aware retrieval + story index", "rag_combined_retrieval_story_index_results.json"),
]


def truncate(text: str, limit: int = 200) -> str:
    compact = " ".join(text.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def load_results() -> dict[str, list[dict[str, object]]]:
    result_sets = {}
    for label, filename in APPROACH_FILES:
        path = require_file(OUTPUT_DIR / filename, f"Run the script that produces {filename} first.")
        result_sets[label] = load_json(path)
    return result_sets


def indexing_cost(filename: str) -> float:
    chunks = load_json(require_file(OUTPUT_DIR / filename, f"Run the script that produces {filename} first."))
    embedding_cost = estimate_cost(EMBEDDING_MODEL, sum(approx_token_count(chunk["text"]) for chunk in chunks))
    if filename != "index_enriched.json":
        return embedding_cost
    enrichment_cost = sum(
        estimate_cost(
            str(chunk.get("enrichment_model", chunk.get("analysis_model", "gemini-2.5-flash"))),
            int(chunk.get("enrichment_input_tokens", 0)),
            int(chunk.get("enrichment_output_tokens", 0)),
        )
        for chunk in chunks
    )
    return embedding_cost + enrichment_cost


def story_index_cost() -> float:
    story_index = load_json(require_file(OUTPUT_DIR / "story_index.json", "Run the script that produces story_index.json first."))
    if story_index and all("summary_input_tokens" in story and "summary_output_tokens" in story for story in story_index):
        return sum(
            estimate_cost(
                str(story.get("summary_model", "gemini-2.5-flash")),
                int(story.get("summary_input_tokens", 0)),
                int(story.get("summary_output_tokens", 0)),
            )
            for story in story_index
        )

    # Fallback for older story_index.json files created before token metadata was stored.
    chunks = load_json(require_file(OUTPUT_DIR / "index_enriched.json", "Run the script that produces index_enriched.json first."))
    grouped_events: OrderedDict[str, list[str]] = OrderedDict()
    for chunk in chunks:
        story_id = str(chunk["story_id"])
        grouped_events.setdefault(story_id, [])
        key_event = str(chunk.get("key_events", "")).strip()
        if key_event:
            grouped_events[story_id].append(key_event)
    summaries_by_id = {str(story["story_id"]): str(story.get("summary", "")) for story in story_index}
    total_input_tokens = 0
    total_output_tokens = 0
    for story_id, events in grouped_events.items():
        key_events = "\n".join(f"- {event}" for event in events)
        prompt = (
            "Here are the key events from a Sherlock Holmes story, in order:\n\n"
            f"{key_events}\n\n"
            "Write a 2-3 sentence summary of this story's plot. Focus on the central crime or mystery and how it is resolved."
        )
        total_input_tokens += approx_token_count(prompt) + approx_token_count("Write the summary.")
        total_output_tokens += approx_token_count(summaries_by_id.get(story_id, ""))
    return estimate_cost("gemini-2.5-flash", total_input_tokens, total_output_tokens)


def query_cost(result: dict[str, object], include_query_embedding: bool = False, include_query_analysis: bool = False) -> float:
    total = estimate_cost(
        str(result.get("model", "gemini-2.5-flash")),
        int(result["input_tokens"]),
        int(result["output_tokens"]),
    )
    if include_query_embedding:
        total += estimate_cost(EMBEDDING_MODEL, approx_token_count(str(result["query"])))
    if include_query_analysis:
        total += estimate_cost(
            str(result.get("analysis_model", "gemini-2.5-flash")),
            int(result.get("analysis_input_tokens", 0)),
            int(result.get("analysis_output_tokens", 0)),
        )
    return total


def average_query_cost(results: list[dict[str, object]], include_query_embedding: bool = False, include_query_analysis: bool = False) -> float:
    return mean(
        query_cost(
            result,
            include_query_embedding=include_query_embedding,
            include_query_analysis=include_query_analysis,
        )
        for result in results
    )


def total_query_cost(results: list[dict[str, object]], include_query_embedding: bool = False, include_query_analysis: bool = False) -> float:
    return sum(
        query_cost(
            result,
            include_query_embedding=include_query_embedding,
            include_query_analysis=include_query_analysis,
        )
        for result in results
    )


def average_input_tokens(results: list[dict[str, object]]) -> float:
    return mean(int(result["input_tokens"]) for result in results)


def average_output_tokens(results: list[dict[str, object]]) -> float:
    return mean(int(result["output_tokens"]) for result in results)


def main() -> None:
    ensure_output_dir()
    result_sets = load_results()
    markdown_lines = ["# RAG Demo: Results Comparison", ""]
    queries = [result["query"] for result in result_sets["[02] Long context baseline"]]

    for query in queries:
        markdown_lines.append(f'## Query: "{query}"')
        markdown_lines.append("")
        markdown_lines.append("| Approach | Answer (truncated to 200 chars) | Input tokens | Output tokens | Latency (ms) |")
        markdown_lines.append("|----------|----------------------------------|--------------|---------------|--------------|")
        for label, _filename in APPROACH_FILES:
            result = next(item for item in result_sets[label] if item["query"] == query)
            markdown_lines.append(
                f"| {label} | {truncate(str(result['answer']))} | {result['input_tokens']} | {result['output_tokens']} | {result['latency_ms']} |"
            )
        markdown_lines.append("")

    naive_indexing_cost = indexing_cost("index_naive.json")
    structural_indexing_cost = indexing_cost("index_structural.json")
    enriched_indexing_cost = indexing_cost("index_enriched.json")
    story_summary_cost = story_index_cost()
    cost_rows = [
        (
            "[02] Long context baseline",
            0.0,
            average_input_tokens(result_sets["[02] Long context baseline"]),
            average_output_tokens(result_sets["[02] Long context baseline"]),
            average_query_cost(result_sets["[02] Long context baseline"]),
            total_query_cost(result_sets["[02] Long context baseline"]),
        ),
        (
            "[03+04] Naive RAG",
            naive_indexing_cost,
            average_input_tokens(result_sets["[03+04] Naive RAG"]),
            average_output_tokens(result_sets["[03+04] Naive RAG"]),
            average_query_cost(result_sets["[03+04] Naive RAG"], include_query_embedding=True),
            naive_indexing_cost + total_query_cost(result_sets["[03+04] Naive RAG"], include_query_embedding=True),
        ),
        (
            "[05+06] RAG + structural",
            structural_indexing_cost,
            average_input_tokens(result_sets["[05+06] RAG + structural metadata"]),
            average_output_tokens(result_sets["[05+06] RAG + structural metadata"]),
            average_query_cost(result_sets["[05+06] RAG + structural metadata"], include_query_embedding=True),
            structural_indexing_cost + total_query_cost(result_sets["[05+06] RAG + structural metadata"], include_query_embedding=True),
        ),
        (
            "[07+08] RAG + enriched",
            enriched_indexing_cost,
            average_input_tokens(result_sets["[07+08] RAG + LLM-enriched tags"]),
            average_output_tokens(result_sets["[07+08] RAG + LLM-enriched tags"]),
            average_query_cost(result_sets["[07+08] RAG + LLM-enriched tags"], include_query_embedding=True),
            enriched_indexing_cost + total_query_cost(result_sets["[07+08] RAG + LLM-enriched tags"], include_query_embedding=True),
        ),
        (
            "[09] Structural metadata-aware retrieval (no story index)",
            structural_indexing_cost,
            average_input_tokens(result_sets["[09] Structural metadata-aware retrieval (no story index)"]),
            average_output_tokens(result_sets["[09] Structural metadata-aware retrieval (no story index)"]),
            average_query_cost(
                result_sets["[09] Structural metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            structural_indexing_cost
            + total_query_cost(
                result_sets["[09] Structural metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
        (
            "[10] Enriched metadata-aware retrieval (no story index)",
            enriched_indexing_cost,
            average_input_tokens(result_sets["[10] Enriched metadata-aware retrieval (no story index)"]),
            average_output_tokens(result_sets["[10] Enriched metadata-aware retrieval (no story index)"]),
            average_query_cost(
                result_sets["[10] Enriched metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            enriched_indexing_cost
            + total_query_cost(
                result_sets["[10] Enriched metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
        (
            "[11] Combined metadata-aware retrieval (no story index)",
            enriched_indexing_cost,
            average_input_tokens(result_sets["[11] Combined metadata-aware retrieval (no story index)"]),
            average_output_tokens(result_sets["[11] Combined metadata-aware retrieval (no story index)"]),
            average_query_cost(
                result_sets["[11] Combined metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            enriched_indexing_cost
            + total_query_cost(
                result_sets["[11] Combined metadata-aware retrieval (no story index)"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
        (
            "[12+13] Structural metadata-aware retrieval + story index",
            structural_indexing_cost + enriched_indexing_cost + story_summary_cost,
            average_input_tokens(result_sets["[12+13] Structural metadata-aware retrieval + story index"]),
            average_output_tokens(result_sets["[12+13] Structural metadata-aware retrieval + story index"]),
            average_query_cost(
                result_sets["[12+13] Structural metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            structural_indexing_cost
            + enriched_indexing_cost
            + story_summary_cost
            + total_query_cost(
                result_sets["[12+13] Structural metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
        (
            "[12+14] Enriched metadata-aware retrieval + story index",
            enriched_indexing_cost + story_summary_cost,
            average_input_tokens(result_sets["[12+14] Enriched metadata-aware retrieval + story index"]),
            average_output_tokens(result_sets["[12+14] Enriched metadata-aware retrieval + story index"]),
            average_query_cost(
                result_sets["[12+14] Enriched metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            enriched_indexing_cost
            + story_summary_cost
            + total_query_cost(
                result_sets["[12+14] Enriched metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
        (
            "[12+15] Combined metadata-aware retrieval + story index",
            enriched_indexing_cost + story_summary_cost,
            average_input_tokens(result_sets["[12+15] Combined metadata-aware retrieval + story index"]),
            average_output_tokens(result_sets["[12+15] Combined metadata-aware retrieval + story index"]),
            average_query_cost(
                result_sets["[12+15] Combined metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
            enriched_indexing_cost
            + story_summary_cost
            + total_query_cost(
                result_sets["[12+15] Combined metadata-aware retrieval + story index"],
                include_query_embedding=True,
                include_query_analysis=True,
            ),
        ),
    ]

    markdown_lines.append("## Cost Summary")
    markdown_lines.append("")
    markdown_lines.append("| Approach | Avg input tokens | Avg output tokens | Indexing cost | Query cost (avg) | Total setup + 6 queries |")
    markdown_lines.append("|----------|------------------|-------------------|---------------|------------------|-------------------------|")
    for label, current_indexing_cost, avg_input_tokens, avg_output_tokens, avg_query_cost, total_cost in cost_rows:
        markdown_lines.append(
            f"| {label} | {avg_input_tokens:.0f} | {avg_output_tokens:.0f} | ${current_indexing_cost:.6f} | ${avg_query_cost:.6f} | ${total_cost:.6f} |"
        )

    markdown = "\n".join(markdown_lines) + "\n"
    output_path = OUTPUT_DIR / "comparison_all.md"
    output_path.write_text(markdown, encoding="utf-8")
    print(markdown)
    print(f"Saved comparison to {output_path}")


if __name__ == "__main__":
    main()
