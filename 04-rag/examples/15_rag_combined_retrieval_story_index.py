from __future__ import annotations

from R00_shared import (
    EMBEDDING_MODEL,
    OUTPUT_DIR,
    QUERIES,
    analyze_query,
    call_text_model,
    cosine_search,
    embed_query,
    ensure_output_dir,
    get_env_model,
    load_json,
    require_file,
    rerank_chunks,
    write_json,
)

SYSTEM_PROMPT = """You are a Sherlock Holmes expert. Answer questions based only on the provided context passages.
Each passage is labeled with a source ID. Cite your sources using [source_id] format.
If the provided passages do not contain enough information to answer, say so explicitly."""


def build_user_prompt(chunks: list[dict[str, object]], question: str) -> str:
    passages = []
    for chunk in chunks:
        characters = ", ".join(chunk.get("characters", [])) or "None"
        passages.append(
            f"[{chunk['chunk_id']}]\n"
            f"Story: {chunk['story_title']}\n"
            f"Position: {chunk['position']}\n"
            f"Characters: {characters}\n"
            f"Scene type: {chunk.get('scene_type', 'other')}\n"
            f"Key events: {chunk.get('key_events', '')}\n"
            "---\n"
            f"{chunk['text']}"
        )
    return "Context passages:\n\n" + "\n\n".join(passages) + f"\n\nQuestion: {question}"


def rerank_score(chunk: dict[str, object], hints: dict[str, object]) -> float:
    score = float(chunk["score"])
    chunk_characters = {str(name) for name in chunk.get("characters", [])}
    target_characters = set(hints["target_characters"])
    score += len(chunk_characters & target_characters) * 0.10
    if chunk.get("scene_type") in hints["target_scene_types"]:
        score += 0.10
    if chunk["story_title"] in hints["target_stories"]:
        score += 0.15
    if hints["target_position"] != "any" and chunk["position"] == hints["target_position"]:
        score += 0.05
    return score


def apply_story_prefilter(candidates: list[dict[str, object]], target_stories: list[str]) -> tuple[list[dict[str, object]], bool]:
    if not target_stories:
        return candidates, False
    filtered = [chunk for chunk in candidates if chunk["story_title"] in target_stories]
    if len(filtered) >= 10:
        return filtered, True
    return candidates, False


def main() -> None:
    ensure_output_dir()
    chunks = load_json(require_file(OUTPUT_DIR / "index_enriched.json", "Run python 07_index_enriched.py first."))
    model = get_env_model("RAG_GENERATION_MODEL", "gemini-2.5-flash")
    analysis_model = get_env_model("RAG_QUERY_ANALYSIS_MODEL", "gemini-2.5-flash")
    results = []
    story_index = load_json(require_file(OUTPUT_DIR / "story_index.json", "Run python 12_build_story_index.py first."))

    for index, query in enumerate(QUERIES, start=1):
        print(f"Running combined metadata-aware query {index}/{len(QUERIES)}...")
        query_embedding = embed_query(query, model=EMBEDDING_MODEL)
        candidates = cosine_search(query_embedding, chunks, top_k=30)
        analysis = analyze_query(query, model=analysis_model, story_index=story_index)
        hints = analysis["query_hints"]
        print(f"Query hints: {hints}")
        candidate_pool, story_filter_applied = apply_story_prefilter(candidates, hints["target_stories"])
        retrieved = rerank_chunks(candidate_pool, lambda chunk: rerank_score(chunk, hints), top_k=10)
        response = call_text_model(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(retrieved, query),
            model=model,
            max_tokens=700,
        )
        result = {
            "query": query,
            "query_hints": hints,
            "story_filter_applied": story_filter_applied,
            "retrieved_chunks": [chunk["chunk_id"] for chunk in retrieved],
            "answer": response["text"],
            "model": model,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "latency_ms": response["latency_ms"],
            "analysis_model": analysis["analysis_model"],
            "analysis_input_tokens": analysis["analysis_input_tokens"],
            "analysis_output_tokens": analysis["analysis_output_tokens"],
            "analysis_latency_ms": analysis["analysis_latency_ms"],
            "story_index_used": True,
        }
        results.append(result)
        print(
            f"\nQuery: {query}\nStory filter applied: {story_filter_applied}\nRetrieved: {', '.join(result['retrieved_chunks'])}\n"
            f"Answer: {response['text']}\n"
        )

    output_path = OUTPUT_DIR / "rag_combined_retrieval_story_index_results.json"
    write_json(output_path, results)
    print(f"Saved combined metadata-aware results to {output_path}")


if __name__ == "__main__":
    main()
