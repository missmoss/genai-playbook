from __future__ import annotations

from collections import OrderedDict

from R00_shared import OUTPUT_DIR, call_text_model, ensure_output_dir, get_env_model, load_json, require_file, write_json

SYSTEM_PROMPT = """Here are the key events from a Sherlock Holmes story, in order:

{key_events}

Write a 2-3 sentence summary of this story's plot. Focus on the central crime or mystery and how it is resolved."""


def build_story_groups(chunks: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: OrderedDict[str, dict[str, object]] = OrderedDict()
    for chunk in chunks:
        story_id = str(chunk["story_id"])
        if story_id not in grouped:
            grouped[story_id] = {
                "story_id": story_id,
                "story_title": chunk["story_title"],
                "book": chunk["book"],
                "characters": set(),
                "key_events": [],
            }
        record = grouped[story_id]
        record["characters"].update(str(item) for item in chunk.get("characters", []))
        key_event = str(chunk.get("key_events", "")).strip()
        if key_event:
            record["key_events"].append(key_event)
    return list(grouped.values())


def summarize_story(story: dict[str, object], model: str) -> dict[str, object]:
    key_events = "\n".join(f"- {event}" for event in story["key_events"])
    response = call_text_model(
        system_prompt=SYSTEM_PROMPT.format(key_events=key_events),
        user_prompt="Write the summary.",
        model=model,
        max_tokens=220,
    )
    return {
        "summary": response["text"].strip(),
        "summary_model": model,
        "summary_input_tokens": response["input_tokens"],
        "summary_output_tokens": response["output_tokens"],
        "summary_latency_ms": response["latency_ms"],
    }


def main() -> None:
    ensure_output_dir()
    model = get_env_model("RAG_STORY_SUMMARY_MODEL", "gemini-2.5-flash")
    chunks = load_json(require_file(OUTPUT_DIR / "index_enriched.json", "Run python 07_index_enriched.py first."))
    stories = build_story_groups(chunks)
    output = []

    for index, story in enumerate(stories, start=1):
        print(f"Summarizing story {index}/{len(stories)}: {story['story_title']}")
        summary_payload = summarize_story(story, model)
        output.append(
            {
                "story_id": story["story_id"],
                "story_title": story["story_title"],
                "book": story["book"],
                "characters": sorted(story["characters"]),
                "summary": summary_payload["summary"],
                "summary_model": summary_payload["summary_model"],
                "summary_input_tokens": summary_payload["summary_input_tokens"],
                "summary_output_tokens": summary_payload["summary_output_tokens"],
                "summary_latency_ms": summary_payload["summary_latency_ms"],
            }
        )

    output_path = OUTPUT_DIR / "story_index.json"
    write_json(output_path, output)
    print(f"Saved story index to {output_path}")


if __name__ == "__main__":
    main()
