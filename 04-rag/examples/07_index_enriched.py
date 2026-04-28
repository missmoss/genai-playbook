from __future__ import annotations

from typing import Any

from R00_shared import (
    OUTPUT_DIR,
    call_text_model,
    chunk_text,
    embed_texts,
    estimate_cost,
    ensure_output_dir,
    get_env_model,
    load_json,
    parse_json_response,
    require_file,
    write_json,
)

SYSTEM_PROMPT = """Analyze this passage from a Sherlock Holmes story and output a JSON object with these fields:

- characters: array of character names that appear or are mentioned in this passage
- scene_type: one of ["crime_discovery", "client_meeting", "investigation", "deduction_reveal", "chase_action", "domestic_scene", "backstory", "other"]
- key_events: one-sentence summary of what happens in this passage
- has_clue: boolean - does this passage contain a clue or piece of evidence relevant to the case?

Return only valid JSON, no explanation."""

ENRICHMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "characters": {
            "type": "array",
            "items": {"type": "string"},
        },
        "scene_type": {
            "type": "string",
            "enum": [
                "crime_discovery",
                "client_meeting",
                "investigation",
                "deduction_reveal",
                "chase_action",
                "domestic_scene",
                "backstory",
                "other",
            ],
        },
        "key_events": {"type": "string"},
        "has_clue": {"type": "boolean"},
    },
    "required": ["characters", "scene_type", "key_events", "has_clue"],
}


def get_position(index: int, total: int) -> str:
    if total <= 1:
        return "opening"
    progress = (index + 0.5) / total
    if progress < 1 / 3:
        return "opening"
    if progress < 2 / 3:
        return "middle"
    return "resolution"


def enrich_chunk(chunk: dict[str, Any], current: int, total: int, model: str) -> dict[str, Any]:
    print(f"Enriching chunk {current}/{total}: {chunk['chunk_id']}")
    last_error: Exception | None = None
    for _attempt in range(3):
        try:
            response = call_text_model(
                system_prompt=SYSTEM_PROMPT,
                user_prompt=f"Passage:\n\n{chunk['text']}",
                model=model,
                max_tokens=250,
                response_mime_type="application/json",
                response_json_schema=ENRICHMENT_SCHEMA,
            )
            payload = parse_json_response(response["text"])
            return {
                "characters": payload.get("characters", []),
                "scene_type": payload.get("scene_type", "other"),
                "key_events": payload.get("key_events", ""),
                "has_clue": bool(payload.get("has_clue", False)),
                "enrichment_model": model,
                "enrichment_input_tokens": response["input_tokens"],
                "enrichment_output_tokens": response["output_tokens"],
                "enrichment_latency_ms": response["latency_ms"],
            }
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to enrich {chunk['chunk_id']} after 3 attempts") from last_error


def main() -> None:
    ensure_output_dir()
    stories = load_json(require_file(OUTPUT_DIR / "stories.json", "Run python 01_prepare_texts.py first."))
    enrichment_model = get_env_model("RAG_ENRICHMENT_MODEL", "gemini-2.5-flash")
    partial_path = OUTPUT_DIR / "index_enriched.partial.json"
    chunks: list[dict[str, object]] = []

    for story_index, story in enumerate(stories, start=1):
        print(f"Chunking story {story_index}/{len(stories)}: {story['title']}")
        story_chunks = chunk_text(story["text"], chunk_size=500, overlap=100)
        total_story_chunks = len(story_chunks)
        for chunk_index, chunk in enumerate(story_chunks):
            chunks.append(
                {
                    "chunk_id": f"{story['id']}-chunk-{chunk_index:03d}",
                    "story_id": story["id"],
                    "story_title": story["title"],
                    "book": story["book"],
                    "position": get_position(chunk_index, total_story_chunks),
                    "text": chunk,
                }
            )

    embeddings, total_tokens, estimated_embedding_cost = embed_texts(
        [chunk["text"] for chunk in chunks],
        progress_label="Embedding enriched chunks",
    )
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    completed_by_id: dict[str, dict[str, Any]] = {}
    if partial_path.exists():
        partial_chunks = load_json(partial_path)
        completed_by_id = {chunk["chunk_id"]: chunk for chunk in partial_chunks}
        print(f"Resuming from partial checkpoint: {len(completed_by_id)} chunks already enriched")
        for chunk in chunks:
            existing = completed_by_id.get(chunk["chunk_id"])
            if existing:
                chunk.update(existing)

    enrichment_input_tokens = 0
    enrichment_output_tokens = 0
    total_enrichment_latency = 0
    for index, chunk in enumerate(chunks, start=1):
        if "characters" in chunk and "scene_type" in chunk and "key_events" in chunk and "has_clue" in chunk:
            enrichment_input_tokens += int(chunk.get("enrichment_input_tokens", 0))
            enrichment_output_tokens += int(chunk.get("enrichment_output_tokens", 0))
            total_enrichment_latency += int(chunk.get("enrichment_latency_ms", 0))
            continue
        enrichment = enrich_chunk(chunk, index, len(chunks), enrichment_model)
        enrichment_input_tokens += enrichment["enrichment_input_tokens"]
        enrichment_output_tokens += enrichment["enrichment_output_tokens"]
        total_enrichment_latency += enrichment["enrichment_latency_ms"]
        chunk.update(enrichment)
        write_json(partial_path, chunks)

    output_path = OUTPUT_DIR / "index_enriched.json"
    write_json(output_path, chunks)
    if partial_path.exists():
        partial_path.unlink()
    print(f"Saved {len(chunks)} chunks to {output_path}")
    print(f"Total tokens embedded: {total_tokens}")
    print(f"Estimated embedding cost: ${estimated_embedding_cost:.6f}")
    print(f"Total enrichment calls: {len(chunks)}")
    print(f"Estimated enrichment cost: ${estimate_cost(enrichment_model, enrichment_input_tokens, enrichment_output_tokens):.6f}")
    print(f"Enrichment model: {enrichment_model}")
    print(f"Total enrichment time: {total_enrichment_latency} ms")


if __name__ == "__main__":
    main()
