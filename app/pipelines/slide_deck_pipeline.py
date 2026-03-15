"""
pipelines/slide_deck_pipeline.py

PURPOSE (Content):
    Extract formulas, definitions, and key concepts from lecture/tutorial slides.
    Functionally identical to the notes pipeline but tuned for slide deck structure
    (shorter text blocks, more bullet points, more diagrams described in text).

OUTPUT FORMAT (content — same as notes):
    {
      "topics": ["topic1", "topic2"],
      "blocks": [
        { "topic": "topic name", "type": "formula|definition|concept|diagram_hint", "content": "..." }
      ]
    }

"diagram_hint" is an extra type used for slide descriptions of diagrams/figures
that should be recreated in the cheatsheet (e.g. architecture diagrams).
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """You are extracting structured content from university lecture or tutorial slides.

Slides use short bullet points and dense notation. Extract ALL of the following:
- Formulas: any mathematical expressions or equations
- Definitions: formal definitions of terms or concepts
- Concepts: key ideas, theorems, methods, properties worth knowing for an exam
- Diagram hints: brief descriptions of any figures, diagrams, or architecture charts shown
  (describe what the diagram shows so it could be sketched on a cheatsheet)

Return ONLY valid JSON (no markdown, no backticks):
{
  "topics": ["topic1", "topic2"],
  "blocks": [
    { "topic": "topic name", "type": "formula|definition|concept|diagram_hint", "content": "extracted content" }
  ]
}

Rules:
- Keep content concise — one fact per block
- For formulas, include the full expression
- For diagram hints, describe the key elements (e.g. "Encoder-Decoder architecture: input → encoder → bottleneck → decoder → output")
- Do NOT skip bullet points — every slide bullet should become a block

Text:
"""


# ── Core processing ───────────────────────────────────────────────────────────

def process_chunk(text: str, client: OpenAI, model: str) -> dict | None:
    full_prompt = PROMPT + text
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        max_tokens=2048,
        temperature=0.1,
    )
    content = response.choices[0].message.content
    if not content:
        return None
    raw = content.strip().replace("```json", "").replace("```", "").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def process_pages(pages: dict[int, str], client: OpenAI, model: str,
                  chunk_size: int = 300) -> dict:
    from core.chunker import chunk_pages
    chunks = chunk_pages(pages, max_words=chunk_size)

    all_topics: list[str] = []
    all_blocks: list[dict] = []
    seen_topics: set[str] = set()

    for chunk in chunks:
        result = process_chunk(chunk.text, client, model)
        if result:
            for t in result.get("topics", []):
                if t.lower() not in seen_topics:
                    all_topics.append(t)
                    seen_topics.add(t.lower())
            all_blocks.extend(result.get("blocks", []))

    return {"topics": all_topics, "blocks": all_blocks}


# ── Standalone test entry point ───────────────────────────────────────────────

def main():
    import argparse
    from core.pdf_extract import extract_pages

    parser = argparse.ArgumentParser(description="Slide deck pipeline")
    parser.add_argument("pdf", help="Path to slide deck PDF")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--chunk-size", type=int, default=300)
    args = parser.parse_args()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )

    print(f"\n📋 Slide Deck Pipeline — {args.pdf}")

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages(pdf_bytes)
    print(f"  Pages: {len(pages)}")

    result = process_pages(pages, client, args.model, args.chunk_size)

    blocks = result["blocks"]
    print(f"\n  Topics: {len(result['topics'])}")
    print(f"  Blocks: {len(blocks)}")
    by_type = {}
    for b in blocks:
        by_type.setdefault(b.get("type", "?"), 0)
        by_type[b["type"]] += 1
    for btype, count in sorted(by_type.items()):
        print(f"    {btype:<15} {count}")

    base = os.path.splitext(args.pdf)[0]
    out = f"{base}_slides_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
