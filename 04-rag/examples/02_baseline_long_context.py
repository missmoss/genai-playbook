from __future__ import annotations

from R00_shared import (
    OUTPUT_DIR,
    QUERIES,
    call_text_model,
    ensure_output_dir,
    get_env_model,
    load_json,
    require_file,
    write_json,
)

SYSTEM_PROMPT = """You are a Sherlock Holmes expert. Answer questions based only on the provided stories.
If the answer cannot be determined from the provided text, say so explicitly.
When referencing events, name the specific story."""


def build_user_prompt(stories: list[dict[str, object]], question: str) -> str:
    story_sections = []
    for story in stories:
        story_sections.append(f"=== {story['title']} ===\n{story['text']}")
    return "Here are 12 Sherlock Holmes stories:\n\n" + "\n\n".join(story_sections) + f"\n\nQuestion: {question}"


def main() -> None:
    ensure_output_dir()
    stories = load_json(require_file(OUTPUT_DIR / "stories.json", "Run python 01_prepare_texts.py first."))
    model = get_env_model("RAG_GENERATION_MODEL", "gemini-2.5-flash")
    results = []
    for index, query in enumerate(QUERIES, start=1):
        print(f"Running baseline query {index}/{len(QUERIES)}...")
        response = call_text_model(
            system_prompt=SYSTEM_PROMPT,
            user_prompt=build_user_prompt(stories, query),
            model=model,
            max_tokens=700,
        )
        result = {
            "query": query,
            "answer": response["text"],
            "model": model,
            "input_tokens": response["input_tokens"],
            "output_tokens": response["output_tokens"],
            "latency_ms": response["latency_ms"],
        }
        results.append(result)
        print(f"\nQuery: {query}\nAnswer: {response['text']}\n")

    output_path = OUTPUT_DIR / "baseline_results.json"
    write_json(output_path, results)
    print(f"Saved baseline results to {output_path}")


if __name__ == "__main__":
    main()
