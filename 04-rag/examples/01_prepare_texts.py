from __future__ import annotations

import re

from R00_shared import OUTPUT_DIR, TEXT_DIR, ensure_output_dir, read_text, slugify, write_json

ADVENTURES_TITLES = [
    "A Scandal in Bohemia",
    "The Red-Headed League",
    "A Case of Identity",
    "The Boscombe Valley Mystery",
    "The Five Orange Pips",
    "The Man with the Twisted Lip",
    "The Adventure of the Blue Carbuncle",
    "The Adventure of the Speckled Band",
    "The Adventure of the Engineer's Thumb",
    "The Adventure of the Noble Bachelor",
    "The Adventure of the Beryl Coronet",
    "The Adventure of the Copper Beeches",
]

ADVENTURES_HEADERS = [
    "I. A SCANDAL IN BOHEMIA",
    "II. THE RED-HEADED LEAGUE",
    "III. A CASE OF IDENTITY",
    "IV. THE BOSCOMBE VALLEY MYSTERY",
    "V. THE FIVE ORANGE PIPS",
    "VI. THE MAN WITH THE TWISTED LIP",
    "VII. THE ADVENTURE OF THE BLUE CARBUNCLE",
    "VIII. THE ADVENTURE OF THE SPECKLED BAND",
    "IX. THE ADVENTURE OF THE ENGINEER’S THUMB",
    "X. THE ADVENTURE OF THE NOBLE BACHELOR",
    "XI. THE ADVENTURE OF THE BERYL CORONET",
    "XII. THE ADVENTURE OF THE COPPER BEECHES",
]


def find_ordered_matches(text: str, headers: list[str]) -> list[re.Match[str]]:
    matches: list[re.Match[str]] = []
    cursor = 0
    for header in headers:
        pattern = re.compile(rf"(?m)^{re.escape(header)}\s*$")
        match = pattern.search(text, cursor)
        if match is None:
            raise ValueError(f"Could not find header: {header}")
        matches.append(match)
        cursor = match.end()
    return matches


def parse_texts() -> list[dict[str, object]]:
    adventures_text = read_text(TEXT_DIR / "the-adventures-of-sherlock-holmes.txt")
    matches = find_ordered_matches(adventures_text, ADVENTURES_HEADERS)
    stories: list[dict[str, object]] = []
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(adventures_text)
        title = ADVENTURES_TITLES[index]
        story_text = adventures_text[start:end].strip()
        stories.append(
            {
                "id": f"adventures-{index + 1:02d}-{slugify(title)}",
                "title": title,
                "book": "The Adventures of Sherlock Holmes",
                "story_index": index + 1,
                "text": story_text,
            }
        )
    return stories


def main() -> None:
    ensure_output_dir()
    stories = parse_texts()
    stories_path = OUTPUT_DIR / "stories.json"
    write_json(stories_path, stories)
    print(f"Wrote {len(stories)} stories to {stories_path}")


if __name__ == "__main__":
    main()
