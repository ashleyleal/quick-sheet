"""
run_all_pipelines.py

Process all PDFs in a course directory through their respective pipelines.
Run this before test_generate.py to produce all the JSON result files.

Usage:
    python run_all_pipelines.py data/uploads/sample_uploads/aps360
    python run_all_pipelines.py data/uploads/sample_uploads/aps360 --skip-existing
    python run_all_pipelines.py data/uploads/sample_uploads/aps360 --only exam notes
"""

import os
import sys
import json
import argparse
import io
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

# ── OpenAI client (shared across all pipelines) ───────────────────────────────
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_CHUNK_SIZE = 300


# ── PDF extraction (inline, no dependency on core/) ──────────────────────────

OCR_DPI      = 300   # render resolution for OCR
OCR_LANG     = "eng" # tesseract language — change for other languages
MIN_TEXT_CHARS = 50  # pages with fewer chars trigger OCR fallback


def _ocr_page_image(pix) -> str:
    """Run tesseract OCR on a PyMuPDF Pixmap. Returns extracted text or empty string."""
    try:
        import pytesseract
        from PIL import Image

        mode = "RGBA" if pix.alpha else "RGB"
        img  = Image.frombytes(mode, (pix.width, pix.height), pix.samples)
        if img.mode == "RGBA":
            img = img.convert("RGB")
        return pytesseract.image_to_string(img, lang=OCR_LANG)
    except ImportError:
        return ""  # pytesseract/Pillow not installed — skip OCR silently


def extract_pages(pdf_bytes: bytes) -> dict[int, str]:
    """
    Extract text from every page of a PDF.

    Strategy:
      1. PyMuPDF direct text extraction — fast, works for digital PDFs.
      2. Per-page OCR fallback via pytesseract — fires when direct extraction
         returns fewer than MIN_TEXT_CHARS (catches scanned/image pages).
      3. pdfplumber — last resort if PyMuPDF is not installed (no OCR).

    OCR requirements:
        pip install pytesseract Pillow
        Tesseract binary: https://github.com/UB-Mannheim/tesseract/wiki (Windows)
    """
    try:
        import fitz  # PyMuPDF

        doc   = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = {}

        for i, page in enumerate(doc, start=1):
            text = page.get_text("text")

            # Page looks empty or scanned — attempt OCR
            if len(text.strip()) < MIN_TEXT_CHARS:
                try:
                    mat      = fitz.Matrix(OCR_DPI / 72, OCR_DPI / 72)
                    pix      = page.get_pixmap(matrix=mat, colorspace=fitz.csRGB)
                    ocr_text = _ocr_page_image(pix)
                    if len(ocr_text.strip()) > len(text.strip()):
                        text = ocr_text
                        print(f"    [ocr] page {i}: OCR used ({len(text.strip())} chars)")
                    else:
                        print(f"    [ocr] page {i}: OCR yielded no improvement")
                except Exception as e:
                    print(f"    [ocr] page {i}: OCR failed — {e}")

            pages[i] = text

        doc.close()
        return pages

    except ImportError:
        pass

    # Fallback: pdfplumber (no OCR)
    try:
        import pdfplumber
        pages = {}
        with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                pages[i] = page.extract_text() or ""
        print("  [warn] PyMuPDF not installed — OCR unavailable, using pdfplumber")
        return pages
    except ImportError:
        print("  ERROR: install PyMuPDF: pip install PyMuPDF")
        sys.exit(1)


def pages_to_chunks(pages: dict[int, str], chunk_size: int) -> list[str]:
    chunks, current, count = [], [], 0
    for page_num in sorted(pages):
        for word in pages[page_num].split():
            current.append(word)
            count += 1
            if count >= chunk_size:
                chunks.append(" ".join(current))
                current, count = [], 0
    if current:
        chunks.append(" ".join(current))
    return chunks


# ── Per-folder prompts ────────────────────────────────────────────────────────

PROMPTS = {
    # ── Content Emphasis (output: {"questions": [...]}) ───────────────────────
    "exam": """You are a teaching assistant extracting ALL questions from an exam paper.

RULES:
- Extract EVERY question and sub-question
- topic: short concept label (e.g. "Backpropagation", "CNN Output Shape")
- question_summary: describe the concept being tested, NOT the answer choices
  - GOOD: "Calculate the number of parameters in a conv layer"
  - BAD: "Choose from the provided options"
- For multi-part questions, list each part separately

Return ONLY valid JSON:
{ "questions": [ { "topic": "label", "question_summary": "what is tested" } ] }

Text:
""",

    "assignment": """You are analyzing a university assignment to identify practiced skills.

For each problem or sub-problem:
- topic: short concept label
- question_summary: what concept or method is being practiced (not "solve problem X")

Return ONLY valid JSON:
{
  "questions": [ { "topic": "label", "question_summary": "skill being practiced" } ],
  "patterns": [ { "topic": "label", "pattern": "solution method", "key_formula": "" } ]
}

Text:
""",

    "syllabus": """You are extracting topic coverage from a course syllabus.

For EVERY topic mentioned (weekly schedule, learning objectives, exam sections):
- Create one entry per mention (same topic in multiple sections → multiple entries)
- question_summary: where/how this topic was mentioned

Return ONLY valid JSON:
{
  "questions": [ { "topic": "label", "question_summary": "context (e.g. Week 3, final exam topic)" } ],
  "weights": [ { "topic": "label", "weight_hint": "emphasis description", "coverage_weeks": 0 } ]
}

Text:
""",

    # ── Content (output: {"topics": [...], "blocks": [...]}) ──────────────────
    "notes": """You are extracting structured content from academic notes.

Extract ALL formulas, definitions, and key concepts. Do not skip any.

Return ONLY valid JSON:
{
  "topics": ["topic1", "topic2"],
  "blocks": [ { "topic": "name", "type": "formula|definition|concept", "content": "content" } ]
}

Text:
""",

    "slide_deck": """You are extracting structured content from lecture/tutorial slides.

Extract ALL formulas, definitions, key concepts, and diagram descriptions.

Return ONLY valid JSON:
{
  "topics": ["topic1"],
  "blocks": [ { "topic": "name", "type": "formula|definition|concept|diagram_hint", "content": "content" } ]
}

Text:
""",

    # ── Both (has questions AND topics/blocks) ────────────────────────────────
    "misc": """You are processing miscellaneous course material.

Extract BOTH:
1. Topics being emphasized → "questions"
2. Content to study (formulas, definitions) → "blocks"

Return ONLY valid JSON:
{
  "questions": [ { "topic": "label", "question_summary": "why emphasized" } ],
  "topics": ["topic1"],
  "blocks": [ { "topic": "name", "type": "formula|definition|concept", "content": "content" } ]
}

Text:
""",
}

RESULT_SUFFIXES = {
    "exam":       "exam_result",
    "assignment": "assignment_result",
    "syllabus":   "syllabus_result",
    "notes":      "notes_result",
    "slide_deck": "slides_result",
    "misc":       "misc_result",
}

MERGE_KEYS = {
    "exam":       ["questions"],
    "assignment": ["questions", "patterns"],
    "syllabus":   ["questions", "weights"],
    "notes":      ["topics", "blocks"],
    "slide_deck": ["topics", "blocks"],
    "misc":       ["questions", "topics", "blocks"],
}


# ── LLM call ─────────────────────────────────────────────────────────────────

def call_llm(prompt: str, text: str, model: str) -> dict | None:
    full = prompt + text
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": full}],
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


# ── Merge chunk results ───────────────────────────────────────────────────────

def merge(folder_type: str, results: list[dict]) -> dict:
    merged: dict[str, list] = {}
    for key in MERGE_KEYS[folder_type]:
        merged[key] = []

    for r in results:
        for key in MERGE_KEYS[folder_type]:
            items = r.get(key, [])
            if key == "topics":
                # Deduplicate topics
                seen = {t.lower() for t in merged["topics"]}
                for t in items:
                    if t.lower() not in seen:
                        merged["topics"].append(t)
                        seen.add(t.lower())
            else:
                merged[key].extend(items)

    return merged


# ── Process one PDF ───────────────────────────────────────────────────────────

def process_pdf(pdf_path: Path, folder_type: str, model: str,
                chunk_size: int) -> dict:
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    pages = extract_pages(pdf_bytes)
    chunks = pages_to_chunks(pages, chunk_size)

    prompt = PROMPTS[folder_type]
    results = []
    for i, chunk in enumerate(chunks, start=1):
        print(f"    chunk {i}/{len(chunks)}...", end=" ", flush=True)
        result = call_llm(prompt, chunk, model)
        if result:
            results.append(result)
            print("ok")
        else:
            print("failed")

    return merge(folder_type, results)


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Run all pipelines for a course folder")
    parser.add_argument("course_dir", help="Course directory (contains exam/, notes/, etc.)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    parser.add_argument("--skip-existing", action="store_true",
                        help="Skip folders that already have a result JSON")
    parser.add_argument("--only", nargs="+", choices=list(PROMPTS.keys()),
                        help="Only process these folder types")
    args = parser.parse_args()

    course = Path(args.course_dir)
    if not course.is_dir():
        print(f"ERROR: {course} is not a directory")
        sys.exit(1)

    print(f"\n📋 Processing course: {course.name}")
    print(f"   Model:      {args.model}")
    print(f"   Chunk size: {args.chunk_size} words")
    print("─" * 60)

    folder_types = args.only or list(PROMPTS.keys())
    processed = 0

    parsed_dir = course / "parsed"

    for folder_type in folder_types:
        folder = course / folder_type
        if not folder.is_dir():
            continue

        pdfs = sorted(folder.glob("*.pdf"))
        if not pdfs:
            continue

        suffix = RESULT_SUFFIXES[folder_type]

        # Skip if result already exists in parsed/
        parsed_dir = course / "parsed"
        if args.skip_existing and (parsed_dir / f"{course.name}_{suffix}.json").exists():
            print(f"\n  [{folder_type}] Skipping — already parsed: {course.name}_{suffix}.json")
            continue

        print(f"\n  [{folder_type}] {len(pdfs)} PDF(s)")

        all_results = []
        for pdf_path in pdfs:
            print(f"  → {pdf_path.name}")
            result = process_pdf(pdf_path, folder_type, args.model, args.chunk_size)
            all_results.append(result)

        # Merge results from all PDFs in this folder
        combined = merge(folder_type, all_results)

        # Save to course/parsed/
        parsed_dir.mkdir(exist_ok=True)
        out_name = f"{course.name}_{suffix}.json"
        out_path = parsed_dir / out_name

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(combined, f, indent=2)
        # Print summary
        if "questions" in combined:
            print(f"    → {len(combined['questions'])} questions/topics extracted")
        if "blocks" in combined:
            print(f"    → {len(combined['blocks'])} content blocks extracted")
        print(f"    → Saved: {out_path}")
        processed += 1

    print(f"\n{'─' * 60}")
    print(f"  Done. Processed {processed} folder(s).")
    print(f"  Run test_generate.py next:")
    print(f"    python tests/test_generate.py {args.course_dir}")


if __name__ == "__main__":
    main()