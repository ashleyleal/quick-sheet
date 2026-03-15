"""
test_parsing.py
Standalone test for PDF extraction + LLM call.
Usage:
    python test_parsing.py path/to/file.pdf
    python test_parsing.py path/to/file.pdf --type exam
    python test_parsing.py path/to/file.pdf --type notes
    python test_parsing.py --text-only   # skip PDF, just test the LLM connection
"""

import os
import sys
import json
import argparse
import io
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

# ── Prompts (one per pipeline type) ──────────────────────────────────────────

PROMPTS = {
    "exam": """You are a teaching assistant extracting ALL questions from an exam paper for study analysis.

RULES:
- Extract EVERY question and sub-question — do not skip any, even if they seem minor
- topic: short concept label only (e.g. "Backpropagation", "CNN Architecture", "Softmax") — NOT a description of the question
- question_summary: one sentence describing the concept or skill being tested, written as if answer choices do not exist
  - GOOD: "Calculate the number of parameters in a fully connected layer"
  - GOOD: "Explain the role of the bottleneck layer in an autoencoder"
  - GOOD: "Derive the gradient of the loss with respect to model weights"
  - BAD: "Select the correct answer from the options"
  - BAD: "Choose from the provided list"
  - BAD: "Identify which of the given statements is correct"
  - BAD: "From the provided results, calculate..."
  - NEVER mention answer choices, options, lists, or "provided" data — describe only the underlying concept or computation
  - For multi-part questions, list each part separately with the same topic

Return ONLY valid JSON (no markdown, no backticks):
{
  "questions": [
    { "topic": "short topic label", "question_summary": "what concept or skill is being tested" }
  ]
}

Text:
""",
    "notes": """You are extracting structured info from academic notes or slides.
Extract formulas, definitions, and key concepts.
Return ONLY valid JSON (no markdown, no backticks):
{
  "topics": ["topic1", "topic2"],
  "blocks": [
    { "topic": "topic name", "type": "formula|definition|concept", "content": "content here" }
  ]
}
Text:
""",
    "assignment": """You are analyzing a university assignment.
For each problem, identify the topic, solution pattern, and any key formula.
Return ONLY valid JSON (no markdown, no backticks):
{
  "problems": [
    { "topic": "topic name", "pattern": "solution method", "key_formula": "formula or empty string" }
  ]
}
Text:
""",
}

# ── PDF extraction ────────────────────────────────────────────────────────────

def extract_pdf_text(path: str) -> dict[int, str]:
    """Returns {page_num: text} using PyMuPDF, falls back to pdfplumber."""
    raw_bytes = open(path, "rb").read()
    pages = {}

    try:
        import fitz
        doc = fitz.open(stream=raw_bytes, filetype="pdf")
        for i, page in enumerate(doc, start=1):
            pages[i] = page.get_text("text")
        doc.close()
        print(f"  [pymupdf] Extracted {len(pages)} pages")
        return pages
    except ImportError:
        print("  [pymupdf] Not available, trying pdfplumber...")

    try:
        import pdfplumber
        with pdfplumber.open(io.BytesIO(raw_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages[i] = page.extract_text() or ""
        print(f"  [pdfplumber] Extracted {len(pages)} pages")
        return pages
    except ImportError:
        print("  ERROR: Neither PyMuPDF nor pdfplumber is installed.")
        print("  Run: pip install PyMuPDF")
        sys.exit(1)


def pages_to_chunks(pages: dict[int, str], chunk_size: int = 300) -> list[tuple[str, int, int]]:
    """
    Split all pages into a list of (text, page_start, page_end) chunks,
    each capped at chunk_size words. Covers the entire document.
    """
    chunks = []
    current_words = []
    current_start = None
    last_page = 1

    for page_num in sorted(pages.keys()):
        text = pages[page_num].strip()
        if not text:
            continue

        last_page = page_num
        if current_start is None:
            current_start = page_num

        current_words.extend(text.split())

        while len(current_words) >= chunk_size:
            chunk_text = " ".join(current_words[:chunk_size])
            chunks.append((chunk_text, current_start, page_num))
            current_words = current_words[chunk_size:]
            current_start = page_num

    # Flush remainder
    if current_words and current_start is not None:
        chunks.append((" ".join(current_words), current_start, last_page))

    return chunks


# ── LLM call ─────────────────────────────────────────────────────────────────

def call_llm(prompt: str, text: str, model: str, chunk_label: str = "") -> dict | None:
    """Send one chunk to the LLM and return parsed JSON, or None on failure."""
    full_prompt = prompt + text
    word_count = len(full_prompt.split())

    print(f"  [llm]{' ' + chunk_label if chunk_label else ''} sending {word_count} words...", end=" ", flush=True)

    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full_prompt}],
        max_tokens=2048,
        temperature=0.1,
    )

    content = response.choices[0].message.content
    finish = response.choices[0].finish_reason

    if content is None:
        print(f"EMPTY (finish_reason: {finish})")
        return None

    raw = content.strip().replace("```json", "").replace("```", "").strip()
    print(f"{len(raw)} chars (finish: {finish})")

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"    WARNING: JSON parse failed — {e}")
        print(f"    Raw: {raw[:200]}")
        return None


# ── Result merging ────────────────────────────────────────────────────────────

def merge_results(doc_type: str, results: list[dict]) -> dict:
    """Merge multiple chunk results into one combined result."""
    if doc_type == "exam":
        all_questions = []
        for r in results:
            all_questions.extend(r.get("questions", []))
        return {"questions": all_questions}

    elif doc_type == "notes":
        all_topics = []
        all_blocks = []
        seen_topics = set()
        for r in results:
            for t in r.get("topics", []):
                if t.lower() not in seen_topics:
                    all_topics.append(t)
                    seen_topics.add(t.lower())
            all_blocks.extend(r.get("blocks", []))
        return {"topics": all_topics, "blocks": all_blocks}

    elif doc_type == "assignment":
        all_problems = []
        for r in results:
            all_problems.extend(r.get("problems", []))
        return {"problems": all_problems}

    return {}


# ── Pretty print results ──────────────────────────────────────────────────────

def print_results(doc_type: str, data: dict):
    print("\n" + "═" * 60)
    print(f"  RESULTS  ({doc_type.upper()} pipeline)")
    print("═" * 60)

    if "raw_response" in data:
        print("  (raw — JSON parse failed)")
        print(data["raw_response"])
        return

    if doc_type == "exam":
        questions = data.get("questions", [])
        from collections import Counter
        topic_counts = Counter(q["topic"] for q in questions)
        print(f"  Found {len(questions)} questions across {len(topic_counts)} topics\n")
        for topic, count in topic_counts.most_common():
            print(f"  {topic:<40} {count}x")

    elif doc_type == "notes":
        topics = data.get("topics", [])
        blocks = data.get("blocks", [])
        print(f"  Topics:  {', '.join(topics) or 'none'}")
        print(f"  Blocks:  {len(blocks)}\n")
        for b in blocks[:10]:
            print(f"  [{b.get('type','?'):12}] {b.get('topic','?')}")
            print(f"             {b.get('content','')[:80]}")

    elif doc_type == "assignment":
        problems = data.get("problems", [])
        print(f"  Found {len(problems)} problem(s)\n")
        for p in problems[:10]:
            print(f"  Topic:   {p.get('topic','?')}")
            print(f"  Pattern: {p.get('pattern','?')}")
            if p.get("key_formula"):
                print(f"  Formula: {p.get('key_formula')}")
            print()

    print("═" * 60)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Test PDF extraction + LLM pipeline")
    parser.add_argument("pdf", nargs="?", help="Path to PDF file")
    parser.add_argument("--type", choices=["exam", "notes", "assignment"], default="notes",
                        help="Pipeline type (default: notes)")
    parser.add_argument("--model", default="openai/gpt-oss-120b",
                        help="Model name to pass to the endpoint (default: openai/gpt-oss-120b)")
    parser.add_argument("--chunk-size", type=int, default=300,
                        help="Words per chunk sent to LLM (default: 300)")
    parser.add_argument("--text-only", action="store_true",
                        help="Skip PDF, just test LLM with a hardcoded sample")
    args = parser.parse_args()

    print("\n📋 Cheatsheet Generator — Pipeline Test")
    print("─" * 60)

    # ── Step 1: Get text ──────────────────────────────────────────────────────
    if args.text_only or not args.pdf:
        print("\n[1] Using hardcoded sample text (--text-only mode)\n")
        sample_texts = {
            "exam": """
Q1. (10 pts) Find the Laplace transform of f(t) = e^(-2t)u(t).
Q2. (15 pts) Sketch the Bode plot magnitude for H(s) = 10/(s+10).
Q3. (10 pts) Apply the Nyquist stability criterion to determine if the
             closed-loop system is stable given the open-loop transfer function.
Q4. (20 pts) Design a PID controller for a second-order plant.
Q5. (10 pts) Find the inverse Laplace transform using partial fractions.
Q6. (15 pts) Draw the Nyquist diagram for G(s) = 1/(s(s+1)).
""",
            "notes": """
Transfer Functions
Definition: A transfer function H(s) is the ratio of the Laplace transform
of the output to the Laplace transform of the input, assuming zero initial conditions.
Formula: H(s) = Y(s) / X(s)

Poles and Zeros
The poles of H(s) are the values of s where the denominator is zero.
The zeros are where the numerator is zero. Pole locations determine stability.

Bode Plots
A Bode plot shows the frequency response of a system.
Magnitude plot: 20*log10|H(jw)| in dB vs log(w)
Phase plot: angle(H(jw)) in degrees vs log(w)
""",
            "assignment": """
Problem 1: Given G(s) = 5/(s^2 + 3s + 2), find the step response.
Use partial fraction decomposition to find the inverse Laplace transform.

Problem 2: For the system with H(s) = K/(s(s+2)(s+5)), find the value
of K for marginal stability using the Routh-Hurwitz criterion.

Problem 3: Sketch the root locus for the open-loop transfer function
G(s)H(s) = K(s+1)/(s(s+3)(s+5)).
""",
        }
        text = sample_texts.get(args.type, sample_texts["notes"])
        chunks = [(text, 1, 1)]

    else:
        if not os.path.exists(args.pdf):
            print(f"ERROR: File not found: {args.pdf}")
            sys.exit(1)

        print(f"\n[1] Extracting text from: {args.pdf}\n")
        pages = extract_pdf_text(args.pdf)

        total_words = sum(len(t.split()) for t in pages.values())
        for pnum, ptext in sorted(pages.items()):
            chars = len(ptext.strip())
            status = "✓" if chars > 100 else "⚠ thin"
            print(f"  Page {pnum:3d}: {chars:5d} chars  {status}")

        chunks = pages_to_chunks(pages, chunk_size=args.chunk_size)
        print(f"\n  [chunker] {total_words} total words → {len(chunks)} chunk(s) of ~{args.chunk_size} words each")

    # ── Step 2: Call LLM for each chunk ──────────────────────────────────────
    print(f"\n[2] Running '{args.type}' pipeline — {len(chunks)} API call(s)...\n")
    prompt = PROMPTS[args.type]
    chunk_results = []

    for i, (chunk_text, page_start, page_end) in enumerate(chunks, start=1):
        label = f"chunk {i}/{len(chunks)} (p{page_start}-{page_end})"
        try:
            result = call_llm(prompt, chunk_text, model=args.model, chunk_label=label)
            if result:
                chunk_results.append(result)
        except Exception as e:
            print(f"  ERROR on {label}: {e}")

    if not chunk_results:
        print("\nERROR: All chunks failed, no results to show.")
        sys.exit(1)

    # ── Step 3: Merge + print ─────────────────────────────────────────────────
    merged = merge_results(args.type, chunk_results)
    print(f"\n  [merge] Combined {len(chunk_results)} successful chunk(s)")
    print_results(args.type, merged)

    # ── Dump full JSON ───────────────────────────────────────────────────────
    if args.pdf:
        base = os.path.splitext(args.pdf)[0]
    else:
        base = "test_output"
    out_path = f"{base}_{args.type}_result.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(merged, f, indent=2)
    print(f"\n  [dump] Saved to {out_path}")


if __name__ == "__main__":
    main()