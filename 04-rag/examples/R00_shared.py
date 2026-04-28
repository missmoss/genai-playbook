from __future__ import annotations

import json
import math
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
TEXT_DIR = BASE_DIR / "texts"
OUTPUT_DIR = BASE_DIR / "output"

EMBEDDING_MODEL = "text-embedding-3-small"
GENERATION_MODEL = "claude-sonnet-4-20250514"
ENRICHMENT_MODEL = "claude-haiku-4-5-20251001"
GEMINI_GENERATION_MODEL = "gemini-2.5-flash"
GEMINI_ENRICHMENT_MODEL = "gemini-2.5-flash"
QUERY_ANALYSIS_MODEL = "gemini-2.5-flash"

QUERIES = [
    "Who was the client in The Red-Headed League, and what was the scheme about?",
    "In which stories does Holmes use a disguise, and what does he disguise himself as?",
    "What was the murder weapon in The Boscombe Valley Mystery?",
    "How did Irene Adler outsmart Holmes in A Scandal in Bohemia?",
    "Describe the scene where Holmes fights Moriarty at Reichenbach Falls.",
    "Compare how Holmes treats Watson in the first story versus the last story of the collection.",
]

MODEL_PRICING_PER_MILLION = {
    EMBEDDING_MODEL: {"input": 0.02, "output": 0.0},
    GENERATION_MODEL: {"input": 3.00, "output": 15.00},
    ENRICHMENT_MODEL: {"input": 1.00, "output": 5.00},
    GEMINI_GENERATION_MODEL: {"input": 0.30, "output": 2.50},
    GEMINI_ENRICHMENT_MODEL: {"input": 0.30, "output": 2.50},
    QUERY_ANALYSIS_MODEL: {"input": 0.30, "output": 2.50},
}

QUERY_ANALYSIS_PROMPT_TEMPLATE = """Here are the available stories in our collection:

{story_catalog}

---

Given the question below, output a JSON object with any of these fields that are relevant. Omit fields that aren't relevant.

- target_stories: array of story titles from the list above that the question is about (if any). Only use exact titles from the list.
- target_characters: array of character names from the list above that the question is about (if any)
- target_position: which part of a story is most likely to contain the answer - one of ["opening", "middle", "resolution", "any"]
- target_scene_types: array of scene types likely to contain the answer - from ["crime_discovery", "client_meeting", "investigation", "deduction_reveal", "chase_action", "domestic_scene", "backstory", "other"]

Return only valid JSON, no explanation."""

QUERY_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "target_stories": {
            "type": "array",
            "items": {"type": "string"},
        },
        "target_characters": {
            "type": "array",
            "items": {"type": "string"},
        },
        "target_position": {
            "type": "string",
            "enum": ["opening", "middle", "resolution", "any"],
        },
        "target_scene_types": {
            "type": "array",
            "items": {
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
        },
    },
}


def ensure_output_dir() -> Path:
    OUTPUT_DIR.mkdir(exist_ok=True)
    return OUTPUT_DIR


def read_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.lstrip("\ufeff")


def write_json(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def require_file(path: Path, hint: str) -> Path:
    if not path.exists():
        raise FileNotFoundError(f"Missing {path}. {hint}")
    return path


def approx_token_count(text: str) -> int:
    return len(text.split())


def estimate_cost(model: str, input_tokens: int, output_tokens: int = 0) -> float:
    pricing = MODEL_PRICING_PER_MILLION.get(model)
    if pricing is None:
        return 0.0
    return (
        (input_tokens / 1_000_000) * pricing["input"]
        + (output_tokens / 1_000_000) * pricing["output"]
    )


def slugify(text: str) -> str:
    lowered = text.lower().replace("&", "and")
    cleaned = re.sub(r"[^a-z0-9]+", "-", lowered)
    return cleaned.strip("-")


def last_n_tokens(text: str, token_count: int) -> str:
    tokens = text.split()
    if not tokens:
        return ""
    return " ".join(tokens[-token_count:])


def _recursive_split(text: str, max_tokens: int, separators: list[str] | None = None) -> list[str]:
    separators = separators or ["\n\n", "\n", ". ", " "]
    stripped = text.strip()
    if not stripped:
        return []
    if approx_token_count(stripped) <= max_tokens:
        return [stripped]
    if not separators:
        words = stripped.split()
        return [" ".join(words[i : i + max_tokens]) for i in range(0, len(words), max_tokens)]

    separator = separators[0]
    parts = stripped.split(separator)
    if len(parts) == 1:
        return _recursive_split(stripped, max_tokens, separators[1:])

    pieces: list[str] = []
    current = ""
    for part in parts:
        candidate = part if not current else current + separator + part
        if approx_token_count(candidate) <= max_tokens:
            current = candidate
            continue
        if current:
            pieces.extend(_recursive_split(current, max_tokens, separators[1:]))
        current = part

    if current:
        pieces.extend(_recursive_split(current, max_tokens, separators[1:]))
    return pieces


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 100) -> list[str]:
    units = _recursive_split(text, chunk_size)
    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = unit if not current else current + "\n\n" + unit
        if approx_token_count(candidate) <= chunk_size:
            current = candidate
            continue
        if current:
            chunks.append(current.strip())
            overlap_text = last_n_tokens(current, overlap)
            current = (overlap_text + "\n\n" + unit).strip() if overlap_text else unit
        else:
            current = unit

        if approx_token_count(current) > chunk_size:
            chunks.extend(_recursive_split(current, chunk_size))
            current = ""

    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def get_env_model(env_var: str, default: str) -> str:
    value = os.environ.get(env_var, "").strip()
    return value or default


def embed_texts(
    texts: list[str],
    model: str = EMBEDDING_MODEL,
    batch_size: int = 20,
    progress_label: str = "Embedding",
) -> tuple[list[list[float]], int, float]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in the environment.")
    embeddings: list[list[float]] = []
    total_tokens = sum(approx_token_count(text) for text in texts)
    total_batches = math.ceil(len(texts) / batch_size) if texts else 0

    for batch_index, start in enumerate(range(0, len(texts), batch_size), start=1):
        end = min(start + batch_size, len(texts))
        print(f"{progress_label} batch {batch_index}/{total_batches} ({start + 1}-{end}/{len(texts)})...")
        response = post_json(
            url="https://api.openai.com/v1/embeddings",
            headers={
                "content-type": "application/json",
                "authorization": f"Bearer {api_key}",
            },
            payload={"model": model, "input": texts[start:end]},
        )
        embeddings.extend(item["embedding"] for item in response.get("data", []))

    return embeddings, total_tokens, estimate_cost(model, total_tokens)


def embed_query(text: str, model: str = EMBEDDING_MODEL) -> list[float]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in the environment.")
    response = post_json(
        url="https://api.openai.com/v1/embeddings",
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        payload={"model": model, "input": [text]},
    )
    data = response.get("data", [])
    if not data:
        raise RuntimeError("No embedding returned by OpenAI.")
    return data[0]["embedding"]


def cosine_search(query_embedding: list[float], chunks: list[dict[str, Any]], top_k: int = 10) -> list[dict[str, Any]]:
    try:
        import numpy as np
    except ImportError as exc:
        raise RuntimeError("Missing dependency: numpy") from exc

    if not chunks:
        return []

    matrix = np.array([chunk["embedding"] for chunk in chunks], dtype=float)
    query = np.array(query_embedding, dtype=float)
    query_norm = np.linalg.norm(query)
    matrix_norms = np.linalg.norm(matrix, axis=1)
    safe_denominator = np.where(matrix_norms == 0, 1e-12, matrix_norms) * max(query_norm, 1e-12)
    scores = matrix @ query / safe_denominator
    best_indexes = np.argsort(scores)[::-1][:top_k]

    results: list[dict[str, Any]] = []
    for index in best_indexes:
        item = dict(chunks[int(index)])
        item["score"] = float(scores[int(index)])
        results.append(item)
    return results


def extract_text_from_message(message: Any) -> str:
    parts: list[str] = []
    for block in message.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "".join(parts).strip()


def provider_for_model(model: str) -> str:
    normalized = model.lower()
    if normalized.startswith("claude"):
        return "anthropic"
    if normalized.startswith("gemini"):
        return "gemini"
    if normalized.startswith(("gpt", "o1", "o3", "o4")):
        return "openai"
    raise RuntimeError(f"Unsupported model/provider mapping for model: {model}")


def post_json(url: str, headers: dict[str, str], payload: dict[str, Any]) -> dict[str, Any]:
    command = [
        "curl",
        "--silent",
        "--show-error",
        "--fail-with-body",
        "--request",
        "POST",
        url,
        "--data-binary",
        "@-",
    ]
    for key, value in headers.items():
        command.extend(["--header", f"{key}: {value}"])

    completed = subprocess.run(
        command,
        input=json.dumps(payload).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        detail = stdout or stderr or f"curl exited with code {completed.returncode}"
        raise RuntimeError(f"Request to {url} failed: {detail}")
    try:
        return json.loads(completed.stdout.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            f"Non-JSON response from {url}: {completed.stdout.decode('utf-8', errors='replace')}"
        ) from exc


def call_anthropic(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 700,
    temperature: float = 0.0,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError("Missing ANTHROPIC_API_KEY in the environment.")
    started = time.perf_counter()
    response = post_json(
        url="https://api.anthropic.com/v1/messages",
        headers={
            "content-type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        payload={
            "model": model,
            "system": system_prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": user_prompt}],
        },
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    text = "".join(
        block.get("text", "")
        for block in response.get("content", [])
        if block.get("type") == "text"
    ).strip()
    if not text:
        raise RuntimeError("No text payload returned by Anthropic.")
    usage = response.get("usage") or {}
    input_tokens = int(usage.get("input_tokens", 0) or 0)
    output_tokens = int(usage.get("output_tokens", 0) or 0)
    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "cost_usd": estimate_cost(model, input_tokens, output_tokens),
    }


def call_gemini(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 700,
    temperature: float = 0.0,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY in the environment.")

    payload = {
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"parts": [{"text": user_prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens,
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    if response_mime_type:
        payload["generationConfig"]["responseMimeType"] = response_mime_type
    if response_json_schema:
        payload["generationConfig"]["responseJsonSchema"] = response_json_schema
    started = time.perf_counter()
    response = post_json(
        url=f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={
            "content-type": "application/json",
            "x-goog-api-key": api_key,
        },
        payload=payload,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    candidates = response.get("candidates", [])
    if not candidates:
        raise RuntimeError("No candidates returned by Gemini.")
    finish_reason = candidates[0].get("finishReason")
    if finish_reason and finish_reason not in {"STOP", "MAX_TOKENS"}:
        raise RuntimeError(f"Gemini returned finishReason={finish_reason}")
    parts = (((candidates[0].get("content") or {}).get("parts")) or [])
    text = "".join(part.get("text", "") for part in parts if "text" in part).strip()
    if not text:
        raise RuntimeError("No text payload returned by Gemini.")
    usage = response.get("usageMetadata") or {}
    input_tokens = int(usage.get("promptTokenCount", 0) or 0)
    output_tokens = int(usage.get("candidatesTokenCount", 0) or 0)
    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "cost_usd": estimate_cost(model, input_tokens, output_tokens),
    }


def call_openai(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 700,
    temperature: float = 0.0,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY in the environment.")

    payload: dict[str, Any] = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if response_json_schema:
        payload["response_format"] = {
            "type": "json_schema",
            "json_schema": {
                "name": "response",
                "schema": response_json_schema,
            },
        }
    elif response_mime_type == "application/json":
        payload["response_format"] = {"type": "json_object"}

    started = time.perf_counter()
    response = post_json(
        url="https://api.openai.com/v1/chat/completions",
        headers={
            "content-type": "application/json",
            "authorization": f"Bearer {api_key}",
        },
        payload=payload,
    )
    latency_ms = int((time.perf_counter() - started) * 1000)
    choices = response.get("choices", [])
    if not choices:
        raise RuntimeError("No choices returned by OpenAI.")
    message = choices[0].get("message") or {}
    text = str(message.get("content", "")).strip()
    if not text:
        raise RuntimeError("No text payload returned by OpenAI.")
    usage = response.get("usage") or {}
    input_tokens = int(usage.get("prompt_tokens", 0) or 0)
    output_tokens = int(usage.get("completion_tokens", 0) or 0)
    return {
        "text": text,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "latency_ms": latency_ms,
        "cost_usd": estimate_cost(model, input_tokens, output_tokens),
    }


def call_text_model(
    *,
    system_prompt: str,
    user_prompt: str,
    model: str,
    max_tokens: int = 700,
    temperature: float = 0.0,
    response_mime_type: str | None = None,
    response_json_schema: dict[str, Any] | None = None,
) -> dict[str, Any]:
    provider = provider_for_model(model)
    if provider == "anthropic":
        return call_anthropic(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_json_schema=response_json_schema,
        )
    if provider == "gemini":
        return call_gemini(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_json_schema=response_json_schema,
        )
    if provider == "openai":
        return call_openai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            response_mime_type=response_mime_type,
            response_json_schema=response_json_schema,
        )
    raise RuntimeError(f"Unsupported provider: {provider}")


def parse_json_response(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise
        return json.loads(match.group(0))


def normalize_query_hints(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "target_stories": [str(item) for item in payload.get("target_stories", [])],
        "target_characters": [str(item) for item in payload.get("target_characters", [])],
        "target_position": str(payload.get("target_position", "any") or "any"),
        "target_scene_types": [str(item) for item in payload.get("target_scene_types", [])],
    }


def format_story_catalog(story_index: list[dict[str, Any]]) -> str:
    sections: list[str] = []
    for story in story_index:
        characters = ", ".join(str(item) for item in story.get("characters", [])) or "None"
        sections.append(
            f'- "{story["story_title"]}"\n'
            f'  Summary: {story["summary"]}\n'
            f"  Characters: {characters}"
        )
    return "\n".join(sections)


def analyze_query(
    question: str,
    model: str | None = None,
    story_index: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    analysis_model = model or get_env_model("RAG_QUERY_ANALYSIS_MODEL", QUERY_ANALYSIS_MODEL)
    story_index = story_index or []
    prompt = QUERY_ANALYSIS_PROMPT_TEMPLATE.format(
        story_catalog=format_story_catalog(story_index) if story_index else "(none provided)"
    )
    response = call_text_model(
        system_prompt=prompt,
        user_prompt=f"Question: {question}",
        model=analysis_model,
        max_tokens=200,
        response_mime_type="application/json",
        response_json_schema=QUERY_ANALYSIS_SCHEMA,
    )
    payload = parse_json_response(response["text"])
    hints = normalize_query_hints(payload)
    return {
        "query_hints": hints,
        "analysis_model": analysis_model,
        "analysis_input_tokens": response["input_tokens"],
        "analysis_output_tokens": response["output_tokens"],
        "analysis_latency_ms": response["latency_ms"],
        "analysis_cost_usd": response["cost_usd"],
    }


def rerank_chunks(
    chunks: list[dict[str, Any]],
    score_fn,
    top_k: int = 10,
) -> list[dict[str, Any]]:
    reranked: list[dict[str, Any]] = []
    for chunk in chunks:
        item = dict(chunk)
        item["reranked_score"] = float(score_fn(item))
        reranked.append(item)
    reranked.sort(key=lambda chunk: chunk["reranked_score"], reverse=True)
    return reranked[:top_k]
