from __future__ import annotations

from R00_shared import OUTPUT_DIR, chunk_text, embed_texts, ensure_output_dir, load_json, require_file, write_json


def get_position(index: int, total: int) -> str:
    if total <= 1:
        return "opening"
    progress = (index + 0.5) / total
    if progress < 1 / 3:
        return "opening"
    if progress < 2 / 3:
        return "middle"
    return "resolution"


def main() -> None:
    ensure_output_dir()
    stories = load_json(require_file(OUTPUT_DIR / "stories.json", "Run python 01_prepare_texts.py first."))
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

    embeddings, total_tokens, estimated_cost = embed_texts(
        [chunk["text"] for chunk in chunks],
        progress_label="Embedding structural chunks",
    )
    for chunk, embedding in zip(chunks, embeddings):
        chunk["embedding"] = embedding

    output_path = OUTPUT_DIR / "index_structural.json"
    write_json(output_path, chunks)
    print(f"Saved {len(chunks)} chunks to {output_path}")
    print(f"Total tokens embedded: {total_tokens}")
    print(f"Estimated embedding cost: ${estimated_cost:.6f}")


if __name__ == "__main__":
    main()
