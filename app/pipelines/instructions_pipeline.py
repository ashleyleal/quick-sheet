"""
pipelines/instructions_pipeline.py

PURPOSE (Content Emphasis — text input, no PDF):
    Processes free-text professor hints/instructions entered directly by the user.
    These are the highest-weight signals — explicit professor guidance about what
    will be on the exam gets a strong boost in the importance scorer.

    Unlike other pipelines this takes a string, not a PDF.

OUTPUT FORMAT (content emphasis — same as exam):
    {
      "questions": [
        {
          "topic": "Nyquist Stability",
          "question_summary": "Professor explicitly stated this will be on the final exam"
        }
      ]
    }

    Each hinted topic gets multiple entries if hinted multiple times
    (e.g., mentioned in both "topics to focus on" and "exam structure" sections).
"""

import json
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


# ── Prompt ────────────────────────────────────────────────────────────────────

PROMPT = """You are reading professor hints or instructions about an upcoming exam or course.

Extract EVERY topic or concept the professor explicitly:
- Says will be on the exam
- Highlights as important
- Recommends studying or practicing
- Mentions in the context of assessment

For each hint, create a "question" entry. If the professor mentions the same topic in different
contexts (e.g., "know X" and "X is worth 20% of the final"), add it TWICE — this boosts its
importance score appropriately.

Return ONLY valid JSON (no markdown, no backticks):
{
  "questions": [
    { "topic": "short topic label", "question_summary": "what the professor said about this topic" }
  ]
}

Text:
"""


# ── Core processing ───────────────────────────────────────────────────────────

def process_text(text: str, client: OpenAI, model: str) -> dict:
    """
    Process free-text professor instructions.
    Returns normalized content-emphasis JSON.
    """
    if not text.strip():
        return {"questions": []}

    full_prompt = PROMPT + text
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": full_prompt}],
            max_tokens=1000,
            temperature=0.1,
        )
        content = response.choices[0].message.content
        if not content:
            return {"questions": []}
        raw = content.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception:
        return {"questions": []}


# ── Standalone test entry point ───────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(description="Instructions pipeline (text input)")
    parser.add_argument("--text", type=str, help="Professor instructions as a string")
    parser.add_argument("--file", type=str, help="Path to a .txt file with instructions")
    parser.add_argument("--model", default="openai/gpt-oss-120b")
    args = parser.parse_args()

    client = OpenAI(
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
    )

    if args.file:
        with open(args.file, encoding="utf-8") as f:
            text = f.read()
    elif args.text:
        text = args.text
    else:
        # Interactive mode
        print("Enter professor hints (Ctrl+D or Ctrl+Z when done):")
        import sys
        text = sys.stdin.read()

    print(f"\n📋 Instructions Pipeline")
    print(f"  Input length: {len(text)} chars")

    result = process_text(text, client, args.model)

    print(f"\n  Hinted topics: {len(result['questions'])}")
    for q in result["questions"]:
        print(f"    {q['topic']:<35} — {q['question_summary'][:60]}")

    # Save to cwd
    out = "instructions_result.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\n  [saved] {out}")


if __name__ == "__main__":
    main()
