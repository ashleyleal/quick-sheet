"""
test_generate.py
Standalone test for generating a LaTeX cheatsheet from exam + notes JSON.
The exam JSON determines topic priority (by frequency), the notes JSON
provides the content (formulas, definitions, concepts).

Usage:
    python test_generate.py exam_result.json notes_result.json
    python test_generate.py exam_result.json notes_result.json --pages 2 --columns 4
    python test_generate.py exam_result.json notes_result.json --compile
"""

import os
import sys
import json
import argparse
import subprocess
from collections import Counter, defaultdict
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

MODEL = "openai/gpt-oss-120b"

# ── Script directory (output goes here) ──────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ── Step 1: Rank topics from exam JSON ───────────────────────────────────────

def rank_exam_topics(exam_data: dict) -> list[tuple[str, int]]:
    """Return [(topic, count), ...] sorted by frequency descending."""
    questions = exam_data.get("questions", [])
    counts = Counter(q["topic"] for q in questions if q.get("topic"))
    return counts.most_common()


# ── Step 2: Order all notes blocks by priority ───────────────────────────────

def order_blocks(notes_data: dict, exam_topic_ranking: list[tuple[str, int]]) -> list[dict]:
    """
    Return ALL blocks from notes, ordered so that exam-priority topics come
    first (highest frequency first), followed by remaining topics alphabetically.
    Within each topic: formulas first, then definitions, then concepts.
    """
    all_blocks = notes_data.get("blocks", [])

    # Build a priority score for each topic name
    exam_priority: dict[str, int] = {}
    for rank, (topic, count) in enumerate(exam_topic_ranking):
        exam_priority[topic.lower()] = count

    def topic_score(block_topic: str) -> int:
        bt = block_topic.lower()
        # Exact match
        if bt in exam_priority:
            return exam_priority[bt]
        # Substring match — use highest matching score
        best = 0
        for et, score in exam_priority.items():
            if et in bt or bt in et:
                best = max(best, score)
        return best

    TYPE_ORDER = {"formula": 0, "definition": 1, "concept": 2, "example": 3}

    def block_sort_key(block: dict):
        topic = block.get("topic", "")
        btype = block.get("type", "concept")
        return (
            -topic_score(topic),          # higher exam frequency = earlier
            topic.lower(),                 # alphabetical within same priority
            TYPE_ORDER.get(btype, 99),     # formulas before definitions before concepts
        )

    return sorted(all_blocks, key=block_sort_key)


# ── Prompt ───────────────────────────────────────────────────────────────────

LATEX_SYSTEM_PROMPT = """You are a LaTeX typesetter producing a university exam cheatsheet.

You will receive a list of CONTENT BLOCKS tagged as [Topic] (type): content.

YOUR ONLY JOB: convert every single block into compact LaTeX. Do NOT skip, merge, or omit any block.
Every block must appear in the output. If it is a formula put it in math mode. If it is a definition or concept keep it to one tight line.

DOCUMENT SETUP — use exactly this header:
\\documentclass[7pt]{{extarticle}}
\\usepackage[letterpaper,landscape,top=0.25in,bottom=0.25in,left=0.25in,right=0.25in]{{geometry}}
\\usepackage{{multicol,amsmath,amssymb}}
\\setlength{{\\columnsep}}{{0.15in}}
\\setlength{{\\parskip}}{{0pt}}
\\setlength{{\\parindent}}{{0pt}}
\\pagestyle{{empty}}
\\begin{{document}}
\\scriptsize
\\begin{{multicols}}{{{columns}}}

FORMATTING RULES:
- Group consecutive blocks sharing the same topic under one bold header: \\textbf{{Topic}}\\newline
- Do NOT repeat a topic header if consecutive blocks share it
- Formulas: always use $...$ inline math — never plain text for math symbols
- One line per block — no blank lines between blocks within a topic
- Between topic groups: \\vspace{{2pt}} before the next bold header
- Do NOT add content that was not in the input
- Do NOT skip any block no matter how minor

END the document with:
\\end{{multicols}}
\\end{{document}}

OUTPUT: raw LaTeX only — no markdown fences, no explanation, nothing before \\documentclass."""

# ── Step 3: Build LLM prompt ──────────────────────────────────────────────────

# Prompt for converting a batch of blocks into LaTeX column content
CHUNK_PROMPT = r"""\
Convert the content blocks below into raw LaTeX lines for a dense cheatsheet column.
Output ONLY LaTeX — no markdown fences, no explanation, nothing else.

STRICT RULES:
- Include EVERY block — do not skip any
- Topic headers: \vspace{2pt}\textbf{Topic Name}\\
- Do NOT repeat a topic header if consecutive blocks share the same topic
- Formulas: use $...$ inline math — all math symbols must be inside $...$
- Plain text must NOT contain unescaped special chars:
  - Underscores outside math: \_{}  e.g. self\_conv1
  - Curly braces outside math: \{ and \}
  - Percent: \%   Ampersand: \&   Hash: \#
  - Caret outside math: \^{}   Tilde: \textasciitilde{}
- Code/identifiers: wrap in \texttt{...}, escape underscores inside
- Each block ends with \\
- No \section, \begin, \end, \documentclass — raw column content only

Blocks:
{blocks}
"""

# Document wrapper
LATEX_HEADER = """\\documentclass[8pt]{{extarticle}}
\\usepackage[paper=letterpaper,landscape,top=0.3in,bottom=0.3in,left=0.3in,right=0.3in]{{geometry}}
\\usepackage{{multicol}}
\\usepackage{{amsmath,amssymb}}
\\setlength{{\\columnsep}}{{0.15in}}
\\setlength{{\\parindent}}{{0pt}}
\\begin{{document}}
\\scriptsize
\\begin{{multicols}}{{{columns}}}
"""

LATEX_FOOTER = """\\end{{multicols}}
\\end{{document}}
"""

def sanitize_for_latex(text: str) -> str:
    """
    Escape characters that break LaTeX when appearing in plain text context.
    Math content (detected by $ delimiters) is left untouched.
    """
    # Split on $ to alternate between text and math regions
    parts = text.split("$")
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            # Inside math — leave untouched, just wrap back in $
            result.append("$" + part + "$")
        else:
            # Plain text — escape LaTeX special chars
            part = part.replace("\\", "\\textbackslash{}")  # must be first
            part = part.replace("%",  "\\%")
            part = part.replace("&",  "\\&")
            part = part.replace("#",  "\\#")
            part = part.replace("^",  "\\^{}")
            part = part.replace("~",  "\\textasciitilde{}")
            # Curly braces only if not already LaTeX commands
            # Replace lone { and } that aren't part of \cmd{
            import re
            part = re.sub(r'(?<!\\)\{', '\\{', part)
            part = re.sub(r'(?<!\\)\}', '\\}', part)
            # Underscore outside math
            part = re.sub(r'(?<!\\)_', '\\_{}', part)
            result.append(part)
    return "".join(result)


def blocks_to_lines(ordered_blocks: list) -> list[str]:
    """Convert all blocks to flat text lines ready for LLM conversion."""
    lines = []
    current_topic = None
    for b in ordered_blocks:
        topic = b.get("topic", "")
        btype = b.get("type", "concept")
        text  = b.get("content", "").strip()
        if not text or len(text) > 600:  # skip empty or pathologically long
            continue
        # Sanitize plain-text content
        text = sanitize_for_latex(text)
        # Emit topic header when topic changes
        if topic != current_topic:
            lines.append(f"TOPIC: {topic}")
            current_topic = topic
        lines.append(f"  ({btype}) {text}")
    return lines


def chunk_lines(lines: list[str], chunk_words: int = 600) -> list[list[str]]:
    """Split lines into chunks of ~chunk_words words each."""
    chunks, current, count = [], [], 0
    for line in lines:
        w = len(line.split())
        if count + w > chunk_words and current:
            chunks.append(current)
            current, count = [], 0
        current.append(line)
        count += w
    if current:
        chunks.append(current)
    return chunks


# ── Step 4: Call LLM ──────────────────────────────────────────────────────────

def call_llm(system_prompt: str, user_prompt: str) -> str:
    word_count = len(user_prompt.split())
    print(f"  [llm] Sending {word_count} words...")

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    full_content = ""
    for attempt in range(3):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=8192,
            temperature=0.2,
        )

        chunk = response.choices[0].message.content or ""
        finish = response.choices[0].finish_reason
        full_content += chunk
        print(f"  [llm] attempt {attempt+1}: {len(chunk)} chars (finish: {finish})")

        if not full_content.strip():
            print("  [llm] ERROR: empty response")
            sys.exit(1)

        # Check if LaTeX is complete
        if "\\end{document}" in full_content:
            print(f"  [llm] LaTeX complete ({len(full_content)} chars total)")
            break

        if finish == "stop":
            # Model stopped but no \end{document} — likely a formatting issue, not truncation
            print("  [llm] WARNING: finished without \\\\end{document} — appending closing tags")
            full_content += "\n\\end{multicols}\n\\end{document}\n"
            break

        # finish == "length" — truly truncated, ask model to continue
        print(f"  [llm] Truncated — requesting continuation...")
        messages.append({"role": "assistant", "content": chunk})
        messages.append({"role": "user", "content": "Continue the LaTeX exactly where you left off. Do not repeat any previous content."})

    return full_content.strip()


# ── Step 5: Clean LaTeX output ────────────────────────────────────────────────

def extract_latex(raw: str) -> str:
    raw = raw.replace("```latex", "").replace("```tex", "").replace("```", "").strip()
    idx = raw.find("\\documentclass")
    if idx > 0:
        raw = raw[idx:]
    return raw


# ── Step 6: Optional PDF compile ─────────────────────────────────────────────

def compile_latex(tex_path: str) -> str | None:
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory", os.path.dirname(tex_path), tex_path],
            capture_output=True, text=True, timeout=30
        )
        pdf_path = tex_path.replace(".tex", ".pdf")
        if os.path.exists(pdf_path):
            return pdf_path
        print("  [pdflatex] Compilation failed. Log tail:")
        print(result.stdout[-800:])
        return None
    except FileNotFoundError:
        print("  [pdflatex] Not found — install TeX Live or MiKTeX to compile.")
        return None
    except subprocess.TimeoutExpired:
        print("  [pdflatex] Timed out.")
        return None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate a LaTeX cheatsheet from exam + notes JSON")
    parser.add_argument("course_dir", help="Path to course directory (must contain exam/ and notes/ subdirs with JSON results)")
    parser.add_argument("--out", default=None, help="Output .tex filename (saved next to this script)")
    parser.add_argument("--pages", type=int, default=1, help="Number of pages (default: 1 = front+back)")
    parser.add_argument("--columns", type=int, default=3, help="Number of columns (default: 3)")
    parser.add_argument("--compile", action="store_true", help="Attempt to compile to PDF with pdflatex")
    args = parser.parse_args()

    print("\n📋 Cheatsheet Generator — LaTeX Generation")
    print("─" * 60)

    # ── Load inputs ───────────────────────────────────────────────────────────
    print(f"\n[1] Finding JSON files in: {args.course_dir}")

    def find_json(subdir: str) -> str:
        folder = os.path.join(args.course_dir, subdir)
        if not os.path.isdir(folder):
            print(f"  ERROR: folder not found: {folder}")
            sys.exit(1)
        jsons = [f for f in os.listdir(folder) if f.endswith(".json")]
        if not jsons:
            print(f"  ERROR: no JSON files found in {folder}")
            sys.exit(1)
        if len(jsons) > 1:
            print(f"  WARNING: multiple JSONs in {folder}, using: {jsons[0]}")
        return os.path.join(folder, jsons[0])

    exam_json_path  = find_json("exam")
    notes_json_path = find_json("notes")
    print(f"  Exam:  {exam_json_path}")
    print(f"  Notes: {notes_json_path}")

    with open(exam_json_path, "r", encoding="utf-8") as f:
        exam_data = json.load(f)
    with open(notes_json_path, "r", encoding="utf-8") as f:
        notes_data = json.load(f)

    total_questions = len(exam_data.get("questions", []))
    total_blocks    = len(notes_data.get("blocks", []))
    print(f"  {total_questions} questions, {total_blocks} content blocks ({len(notes_data.get('topics', []))} topics)")

    if total_blocks == 0:
        print("\n  ERROR: notes JSON has no content blocks. Check the file.")
        sys.exit(1)

    # ── Rank exam topics ──────────────────────────────────────────────────────
    print(f"\n[2] Ranking topics by exam frequency...")
    ranked = rank_exam_topics(exam_data)
    if ranked:
        print(f"  Top exam topics:")
        for topic, count in ranked[:10]:
            print(f"    {topic:<45} {count}x")
        if len(ranked) > 10:
            print(f"    ... and {len(ranked) - 10} more")
    else:
        print("  No exam questions found — all notes content will be included without priority ordering.")

    # ── Order all blocks ──────────────────────────────────────────────────────
    print(f"\n[3] Ordering all {total_blocks} blocks (exam topics first)...")
    ordered_blocks = order_blocks(notes_data, ranked)
    exam_matched = sum(1 for b in ordered_blocks if any(
        t.lower() in b.get("topic", "").lower() or b.get("topic", "").lower() in t.lower()
        for t, _ in ranked
    ))
    print(f"  {exam_matched} blocks match exam topics → appear first")
    print(f"  {total_blocks - exam_matched} remaining blocks → appended after")

    # ── Generate LaTeX (chunked: one API call per batch of blocks) ──────────────
    print(f"\n[4] Generating LaTeX ({args.pages} page(s) back+front, {args.columns} columns)...")

    all_lines = blocks_to_lines(ordered_blocks)
    chunks    = chunk_lines(all_lines, chunk_words=500)
    print(f"  {len(all_lines)} input lines → {len(chunks)} chunk(s)")

    system_prompt = CHUNK_PROMPT.format(columns=args.columns) if "{columns}" in CHUNK_PROMPT else CHUNK_PROMPT
    body_parts = []

    for i, chunk in enumerate(chunks, start=1):
        block_text = "\n".join(chunk)
        user_msg   = CHUNK_PROMPT.replace("{blocks}", block_text).replace("{columns}", str(args.columns))
        word_count = len(user_msg.split())
        print(f"  chunk {i}/{len(chunks)}: {len(chunk)} lines, {word_count} words...", end=" ", flush=True)

        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": user_msg}],
            max_tokens=4096,
            temperature=0.1,
        )
        raw_chunk = response.choices[0].message.content or ""
        finish    = response.choices[0].finish_reason
        # Strip any accidental fences
        raw_chunk = raw_chunk.replace("```latex", "").replace("```tex", "").replace("```", "").strip()
        body_parts.append(raw_chunk)
        print(f"{len(raw_chunk)} chars (finish: {finish})")

    # Assemble final document
    header = LATEX_HEADER.format(columns=args.columns)
    body   = "\n\n".join(body_parts)
    latex  = header + "\n" + body + "\n" + LATEX_FOOTER
    print(f"  Total LaTeX: {len(latex)} chars across {len(body_parts)} chunk(s)")

    # ── Save to COURSE_DIR/generated/ ────────────────────────────────────────
    generated_dir = os.path.join(args.course_dir, "generated")
    os.makedirs(generated_dir, exist_ok=True)

    if args.out:
        out_name = args.out if args.out.endswith(".tex") else args.out + ".tex"
    else:
        stem = os.path.basename(os.path.normpath(args.course_dir))
        out_name = f"{stem}_cheatsheet.tex"

    out_path = os.path.join(generated_dir, out_name)

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"\n  [saved] {out_path}")

    # ── Optional compile ──────────────────────────────────────────────────────
    if args.compile:
        print("\n[5] Compiling to PDF...")
        pdf = compile_latex(out_path)
        if pdf:
            print(f"  [pdf]   {pdf}")

    print("\n" + "═" * 60)
    print(f"  Done.")
    if not args.compile:
        print(f"  Compile with: pdflatex \"{out_path}\"")
    print("═" * 60)

if __name__ == "__main__":
    main()