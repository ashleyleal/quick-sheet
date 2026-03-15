"""
pipelines/misc_pipeline.py

PURPOSE (Content — flexible):
    Catch-all pipeline for "Other" / miscellaneous course materials.
    Examples: professor hint sheets, supplementary readings, formula sheets,
    past midterm solutions, tutorial notes, etc.

    The LLM is given both extraction goals simultaneously:
    - If the document looks like emphasis/assessment material → extract topics
      as "questions" entries (content emphasis format)
    - If it looks like reference/content material → extract blocks
      (content format)
    - Most misc docs get both

OUTPUT FORMAT (merged):
    {
      "questions": [...],   # content emphasis (may be empty)
      "topics": [...],      # content topics (may be empty)
      "blocks": [...]       # content blocks (may be empty)
    }

The importance scorer reads "questions" for frequency, and the content
builder reads "topics"/"blocks" — so this handles both roles in one pass.
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """You are processing miscellaneous university course material. It may be professor hints,
supplementary notes, solutions, formula sheets, or anything else.

Do ALL of the following in one pass:

1. If you find TOPICS BEING EMPHASIZED (hints about what matters, what's on the exam, what
   to focus on) → add them to "questions" with context as the summary.

2. If you find CONTENT TO STUDY (formulas, definitions, key concepts, methods) → add them
   to "blocks".

Return ONLY valid JSON (no markdown, no backticks):
{
  "questions": [
    { "topic": "short topic label", "question_summary": "why this topic is emphasized or what context it appeared in" }
  ],
  "topics": ["topic1", "topic2"],
  "blocks": [
    { "topic": "topic name", "type": "formula|definition|concept|diagram_hint", "content": "content here" }
  ]
}

Rules:
- Include EVERYTHING — do not skip content
- It's fine if "questions" is empty (pure content doc) or "blocks" is empty (pure emphasis doc)
- For professor hints like "know X cold" or "X will be on the exam" → put X in questions

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

    all_questions: list[dict] = []
    all_topics: list[str] = []
    all_blocks: list[dict] = []
    seen_topics: set[str] = set()

    for chunk in chunks:
        result = process_chunk(chunk.text, client, model)
        if result:
            all_questions.extend(result.get("questions", []))
            for t in result.get("topics", []):
                if t.lower() not in seen_topics:
                    all_topics.append(t)
                    seen_topics.add(t.lower())
            all_blocks.extend(result.get("blocks", []))

    return {"questions": all_questions, "topics": all_topics, "blocks": all_blocks}


# ── Standalone test entry point ───────────────────────────────────────────────

def main():
    import argparse
    from core.pdf_extract import extract_pages

    parser = argparse.ArgumentParser(description="Misc/other pipeline")
    parser.add_argument("pdf", help="Path to PDF")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--chunk-size", type=int, default=300)
    args = parser.parse_args()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )

    print(f"\n📋 Misc Pipeline — {args.pdf}")

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages(pdf_bytes)
    print(f"  Pages: {len(pages)}")

    result = process_pages(pages, client, args.model, args.chunk_size)

    print(f"\n  Emphasis entries (questions): {len(result['questions'])}")
    print(f"  Content topics:               {len(result['topics'])}")
    print(f"  Content blocks:               {len(result['blocks'])}")

    base = os.path.splitext(args.pdf)[0]
    out = f"{base}_misc_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
