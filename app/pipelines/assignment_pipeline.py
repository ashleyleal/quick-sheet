"""
pipelines/assignment_pipeline.py

PURPOSE (Content Emphasis):
    Extract problem structures from assignments to identify which topics
    require specific solution patterns (methods, formulas). Feeds the
    importance scorer just like the exam pipeline.

OUTPUT FORMAT (same as exam — content emphasis):
    {
      "questions": [
        {
          "topic": "Laplace Transform",
          "question_summary": "Apply partial fraction decomposition to find inverse transform"
        }
      ]
    }

Each problem/sub-problem becomes a "question" entry so the importance scorer
can count topic frequency across assignments the same way it does for exams.
Additionally, a "patterns" key carries the richer structure (solution method +
formula) for content generation downstream.

    {
      "questions": [...],
      "patterns": [
        {
          "topic": "Laplace Transform",
          "pattern": "partial fraction decomposition",
          "key_formula": "F(s) = A/(s+a) + B/(s+b)"
        }
      ]
    }
"""

import json
import sys
import io
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """You are analyzing a university assignment to identify which topics require specific solution patterns.

For each problem or sub-problem in the text below:
- Identify the main topic (short label, e.g. "Laplace Transform", "Gradient Descent")
- Write a one-sentence summary of what skill or concept is being practiced
  - Describe the underlying concept, NOT "solve problem 3b"
  - GOOD: "Apply partial fraction decomposition to find the inverse Laplace transform"
  - GOOD: "Compute the gradient of cross-entropy loss with respect to weights"
  - BAD: "Solve the given problem using the method shown"
- Identify the solution pattern/method required
- Note any key formula involved (empty string if none)

Return ONLY valid JSON (no markdown, no backticks):
{
  "questions": [
    { "topic": "short topic label", "question_summary": "what concept or skill is practiced" }
  ],
  "patterns": [
    {
      "topic": "short topic label",
      "pattern": "solution method or approach",
      "key_formula": "formula if applicable, else empty string"
    }
  ]
}

Text:
"""


# ── Core processing ───────────────────────────────────────────────────────────

def process_chunk(text: str, client: OpenAI, model: str) -> dict | None:
    """Send one text chunk to the LLM and return parsed JSON."""
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
    """
    Process all pages of an assignment PDF.
    Returns merged result in the normalized format.
    """
    from core.chunker import chunk_pages
    chunks = chunk_pages(pages, max_words=chunk_size)

    all_questions = []
    all_patterns = []

    for chunk in chunks:
        result = process_chunk(chunk.text, client, model)
        if result:
            all_questions.extend(result.get("questions", []))
            all_patterns.extend(result.get("patterns", []))

    return {"questions": all_questions, "patterns": all_patterns}


# ── Standalone test entry point ───────────────────────────────────────────────

def main():
    import os
    import argparse
    from core.pdf_extract import extract_pages

    parser = argparse.ArgumentParser(description="Assignment pipeline")
    parser.add_argument("pdf", help="Path to assignment PDF")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    parser.add_argument("--chunk-size", type=int, default=300)
    args = parser.parse_args()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )

    print(f"\n📋 Assignment Pipeline")
    print(f"  File:  {args.pdf}")

    with open(args.pdf, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages(pdf_bytes)
    print(f"  Pages: {len(pages)}")

    result = process_pages(pages, client, args.model, args.chunk_size)

    print(f"\n  Questions found: {len(result['questions'])}")
    print(f"  Patterns found:  {len(result['patterns'])}")

    # Print topic frequency (same as exam pipeline output)
    from collections import Counter
    counts = Counter(q["topic"] for q in result["questions"])
    print("\n  Topic frequency:")
    for topic, count in counts.most_common():
        print(f"    {topic:<40} {count}x")

    # Save
    base = os.path.splitext(args.pdf)[0]
    out = f"{base}_assignment_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
