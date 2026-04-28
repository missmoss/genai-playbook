from __future__ import annotations

from R00_shared import (
    EMBEDDING_MODEL,
    OUTPUT_DIR,
    QUERIES,
    call_text_model,
    cosine_search,
    embed_query,
    ensure_output_dir,
    get_env_model,
    load_json,
    require_file,
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


def main() -> None:
    ensure_output_dir()
    chunks = load_json(require_file(OUTPUT_DIR / "index_enriched.json", "Run python 07_index_enriched.py first."))
    model = get_env_model("RAG_GENERATION_MODEL", "gemini-2.5-flash")
    results = []

    for index, query in enumerate(QUERIES, start=1):
        print(f"Running enriched RAG query {index}/{len(QUERIES)}...")
        query_embedding = embed_query(query, model=EMBEDDING_MODEL)
        retrieved = cosine_search(query_embedding, chunks, top_k=10)
        response = call_text_model(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(retrieved, query),
            model=model,
            max_tokens=700,
        )
        result = {
            "query": query,
            "retrieved_chunks": [chunk["chunk_id"] for chunk in retrieved],
            "answer": response["text"],
            "model": model,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "latency_ms": response["latency_ms"],
        }
        results.append(result)
        print(f"\nQuery: {query}\nRetrieved: {', '.join(result['retrieved_chunks'])}\nAnswer: {response['text']}\n")

    output_path = OUTPUT_DIR / "rag_enriched_results.json"
    write_json(output_path, results)
    print(f"Saved enriched RAG results to {output_path}")


if __name__ == "__main__":
    main()
