"""
pipelines/syllabus_pipeline.py

PURPOSE (Content Emphasis):
    Extract topic coverage and weightings from a course syllabus.
    Identifies which topics the course officially covers, their relative
    weight (if stated), and any exam/assessment emphasis signals.

OUTPUT FORMAT (content emphasis — same structure as exam):
    {
      "questions": [
        {
          "topic": "Convolutional Neural Networks",
          "question_summary": "Listed as a major topic with 3 weeks of coverage"
        }
      ],
      "weights": [
        {
          "topic": "Backpropagation",
          "weight_hint": "covered in midterm and final",
          "coverage_weeks": 2
        }
      ]
    }

The "questions" list makes this compatible with the importance scorer.
Each syllabus topic becomes one entry — if a topic appears multiple times
(e.g., in week schedule AND in exam topics), it gets multiple entries,
naturally increasing its frequency count.
"""

import json
import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """You are analyzing a university course syllabus to extract topic coverage and assessment emphasis.

From the text below, extract:
1. Every topic or concept listed (from weekly schedule, learning objectives, exam topics, etc.)
2. Any assessment weight signals (e.g., "covered on midterm", "20% of final", "2 weeks")

For the "questions" list: create one entry per topic mention. If a topic appears in both the
weekly schedule AND the exam topics section, add it twice — this naturally boosts its frequency.

For "weights": note explicit weight information only when stated.

Return ONLY valid JSON (no markdown, no backticks):
{
  "questions": [
    { "topic": "short topic label", "question_summary": "context where this topic appeared (e.g. Week 3 lecture, final exam topic)" }
  ],
  "weights": [
    { "topic": "topic label", "weight_hint": "description of weight/emphasis", "coverage_weeks": 0 }
  ]
}

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

    all_questions = []
    all_weights = []

    for chunk in chunks:
        result = process_chunk(chunk.text, client, model)
        if result:
            all_questions.extend(result.get("questions", []))
            all_weights.extend(result.get("weights", []))

    return {"questions": all_questions, "weights": all_weights}


# ── Standalone test entry point ───────────────────────────────────────────────

def main():
    import argparse
    from core.pdf_extract import extract_pages

    parser = argparse.ArgumentParser(description="Syllabus pipeline")
    parser.add_argument("pdf", help="Path to syllabus PDF")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--chunk-size", type=int, default=300)
    args = parser.parse_args()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )

    print(f"\n📋 Syllabus Pipeline — {args.pdf}")

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages(pdf_bytes)
    print(f"  Pages: {len(pages)}")

    result = process_pages(pages, client, args.model, args.chunk_size)

    from collections import Counter
    counts = Counter(q["topic"] for q in result["questions"])
    print(f"\n  Topics found: {len(counts)}")
    for topic, count in counts.most_common(15):
        print(f"    {topic:<40} {count}x")

    base = os.path.splitext(args.pdf)[0]
    out = f"{base}_syllabus_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
