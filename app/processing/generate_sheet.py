"""
generate_sheet.py
Generate a LaTeX cheatsheet from all parsed JSONs in a course folder.

Reads from:  <course>/parsed/*.json   (produced by run_all_pipelines.py)
Writes to:   <course>/generated/<course>_cheatsheet.tex

Usage:
    python generate_sheet.py <course_dir>
    python generate_sheet.py <course_dir> --pages 2 --columns 4
    python generate_sheet.py <course_dir> --no-color
    python generate_sheet.py <course_dir> --compile
    python generate_sheet.py <course_dir> --pages 2 --columns 4 --no-color --compile
"""

import os
import sys
import json
import argparse
import subprocess
import re
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://vjioo4r1vyvcozuj.us-east-2.aws.endpoints.huggingface.cloud/v1",
)

MODEL = "openai/gpt-oss-120b"

# ── Content priority within a topic (lower number = higher priority) ──────────
# Order: formulas → definitions → diagrams → examples → concepts
TYPE_PRIORITY = {
    "formula":      1,
    "definition":   2,
    "diagram_hint": 3,
    "example":      4,
    "concept":      5,
}

# ── Color tags per type (used when --no-color is NOT set) ────────────────────
TYPE_TAGS = {
    "formula":      r"\ftag",
    "definition":   r"\dtag",
    "diagram_hint": r"\xtag",
    "example":      r"\etag",
    "concept":      r"\ctag",
}

# ── Which parsed JSON suffixes are emphasis vs content ───────────────────────
EMPHASIS_SUFFIXES = {"exam_result", "assignment_result", "syllabus_result", "misc_result"}
CONTENT_SUFFIXES  = {"notes_result", "slides_result", "misc_result"}

# Chars of LaTeX body per page per column at scriptsize landscape letter
# Used to estimate how many blocks fit within the page budget
CHARS_PER_PAGE_PER_COL = 3800


# ════════════════════════════════════════════════════════════════════════════
# Step 1 — Load all parsed JSONs from <course>/parsed/
# ════════════════════════════════════════════════════════════════════════════

def load_parsed_jsons(course_dir: Path) -> dict[str, dict]:
    """
    Load every JSON from <course>/parsed/.
    Returns {type_suffix: data}, e.g. {"exam_result": {...}, "notes_result": {...}}.
    Filename format: <course>_<type>_result.json -> suffix = <type>_result
    Falls back to scanning type subfolders if parsed/ doesn't exist.
    """
    parsed_dir = course_dir / "parsed"

    if parsed_dir.is_dir():
        jsons = sorted(parsed_dir.glob("*.json"))
        if jsons:
            loaded: dict[str, dict] = {}
            for path in jsons:
                # aps360_exam_result.json -> exam_result
                parts  = path.stem.split("_", 1)
                suffix = parts[1] if len(parts) > 1 else path.stem
                with open(path, encoding="utf-8") as f:
                    loaded[suffix] = json.load(f)
                print(f"  Loaded [{suffix}]: {path.name}")
            return loaded

    # Fallback: scan type subfolders directly
    print("  WARNING: no parsed/ folder — falling back to subfolder scan")
    suffix_map = {
        "exam":       "exam_result",
        "assignment": "assignment_result",
        "notes":      "notes_result",
        "slide_deck": "slides_result",
        "syllabus":   "syllabus_result",
        "misc":       "misc_result",
    }
    loaded = {}
    for folder, suffix in suffix_map.items():
        folder_path = course_dir / folder
        if folder_path.is_dir():
            jsons = sorted(folder_path.glob("*.json"))
            if jsons:
                with open(jsons[0], encoding="utf-8") as f:
                    loaded[suffix] = json.load(f)
                print(f"  Loaded [{suffix}] (fallback): {jsons[0].name}")

    if not loaded:
        print(f"  ERROR: no JSON files found in {course_dir}")
        sys.exit(1)

    return loaded


# ════════════════════════════════════════════════════════════════════════════
# Step 2 — Build topic ranking from all emphasis sources
# ════════════════════════════════════════════════════════════════════════════

def build_topic_ranking(all_data: dict[str, dict]) -> list[tuple[str, int]]:
    """
    Merge all emphasis JSONs (exam, assignment, syllabus, misc) into a single
    topic frequency counter. Returns [(topic, count), ...] sorted descending.

    Each source contributes its "questions" list. Topics that appear across
    multiple sources (e.g., on both exams and assignments) accumulate counts.
    """
    counter: Counter = Counter()
    for suffix, data in all_data.items():
        if not any(suffix.startswith(e.split("_")[0]) for e in EMPHASIS_SUFFIXES):
            continue
        for q in data.get("questions", []):
            topic = q.get("topic", "").strip()
            if topic:
                counter[topic] += 1
    return counter.most_common()


# ════════════════════════════════════════════════════════════════════════════
# Step 3 — Build ordered block list from all content sources
# ════════════════════════════════════════════════════════════════════════════

def build_ordered_blocks(
    all_data: dict[str, dict],
    topic_ranking: list[tuple[str, int]],
) -> list[dict]:
    """
    Collect ALL blocks from content sources (notes, slides, misc) and order by:

    Primary:   Topic importance score (exam frequency, descending)
               — high-frequency exam topics always appear first
    Secondary: Content type within a topic:
               formula(1) → definition(2) → diagram(3) → example(4) → concept(5)
    Tertiary:  Alphabetical topic name for ties
    """
    exam_scores: dict[str, int] = {t.lower(): c for t, c in topic_ranking}

    def topic_score(topic: str) -> int:
        tl = topic.lower()
        if tl in exam_scores:
            return exam_scores[tl]
        return max(
            (score for key, score in exam_scores.items() if key in tl or tl in key),
            default=0,
        )

    all_blocks: list[dict] = []
    for suffix, data in all_data.items():
        if not any(suffix.startswith(c.split("_")[0]) for c in CONTENT_SUFFIXES):
            continue
        for block in data.get("blocks", []):
            all_blocks.append(block)

    def sort_key(block: dict) -> tuple:
        topic = block.get("topic", "")
        btype = block.get("type", "concept")
        return (
            -topic_score(topic),              # 1. high exam frequency first
            TYPE_PRIORITY.get(btype, 99),     # 2. formula→def→diagram→example→concept
            topic.lower(),                    # 3. alphabetical for ties
        )

    return sorted(all_blocks, key=sort_key)


# ════════════════════════════════════════════════════════════════════════════
# Step 4 — Cap blocks to page budget (strict page limit)
# ════════════════════════════════════════════════════════════════════════════

def cap_blocks(
    ordered_blocks: list[dict],
    pages: int,
    columns: int,
) -> tuple[list[dict], bool]:
    """
    Estimate how many blocks fit in the page budget and truncate if needed.
    Because blocks are already priority-sorted, truncation always removes the
    lowest-priority content (concepts from non-exam topics last).

    Estimation: ~80 chars of LaTeX body per block on average.
    Budget: pages * columns * CHARS_PER_PAGE_PER_COL chars total.
    Returns (capped_blocks, was_truncated).
    """
    CHARS_PER_BLOCK = 80
    budget = pages * columns * CHARS_PER_PAGE_PER_COL
    max_blocks = budget // CHARS_PER_BLOCK

    if len(ordered_blocks) <= max_blocks:
        return ordered_blocks, False

    return ordered_blocks[:max_blocks], True


# ════════════════════════════════════════════════════════════════════════════
# LaTeX document templates
# ════════════════════════════════════════════════════════════════════════════

# Color variant — includes xcolor package and \ftag/\dtag/etc. commands
LATEX_HEADER_COLOR = r"""\documentclass[8pt]{extarticle}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[paper=letterpaper,landscape,top=0.3in,bottom=0.3in,left=0.3in,right=0.3in]{geometry}
\usepackage{multicol}
\usepackage{amsmath,amssymb,textcomp}
\usepackage[dvipsnames]{xcolor}
\definecolor{formulacolor}{RGB}{0,100,180}
\definecolor{definitioncolor}{RGB}{180,70,0}
\definecolor{conceptcolor}{RGB}{20,120,50}
\definecolor{examplecolor}{RGB}{120,0,140}
\definecolor{diagramcolor}{RGB}{90,90,90}
\newcommand{\ftag}{\textcolor{formulacolor}{\tiny\textbf{F}}\;}
\newcommand{\dtag}{\textcolor{definitioncolor}{\tiny\textbf{D}}\;}
\newcommand{\ctag}{\textcolor{conceptcolor}{\tiny\textbf{C}}\;}
\newcommand{\etag}{\textcolor{examplecolor}{\tiny\textbf{E}}\;}
\newcommand{\xtag}{\textcolor{diagramcolor}{\tiny\textbf{X}}\;}
\DeclareUnicodeCharacter{03D5}{$\phi$}
\DeclareUnicodeCharacter{03C6}{$\phi$}
\DeclareUnicodeCharacter{03B1}{$\alpha$}
\DeclareUnicodeCharacter{03B2}{$\beta$}
\DeclareUnicodeCharacter{03B3}{$\gamma$}
\DeclareUnicodeCharacter{03B4}{$\delta$}
\DeclareUnicodeCharacter{03B5}{$\epsilon$}
\DeclareUnicodeCharacter{03B7}{$\eta$}
\DeclareUnicodeCharacter{03B8}{$\theta$}
\DeclareUnicodeCharacter{03BB}{$\lambda$}
\DeclareUnicodeCharacter{03BC}{$\mu$}
\DeclareUnicodeCharacter{03C1}{$\rho$}
\DeclareUnicodeCharacter{03C3}{$\sigma$}
\DeclareUnicodeCharacter{03C8}{$\psi$}
\DeclareUnicodeCharacter{03C9}{$\omega$}
\DeclareUnicodeCharacter{03A3}{$\Sigma$}
\DeclareUnicodeCharacter{03A0}{$\Pi$}
\setlength{\columnsep}{0.15in}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\raggedright
\begin{document}
\scriptsize
"""

# No-color variant — same but without xcolor and type-tag commands
LATEX_HEADER_NOCOLOR = r"""\documentclass[8pt]{extarticle}
\usepackage[T1]{fontenc}
\usepackage[utf8]{inputenc}
\usepackage[paper=letterpaper,landscape,top=0.3in,bottom=0.3in,left=0.3in,right=0.3in]{geometry}
\usepackage{multicol}
\usepackage{amsmath,amssymb,textcomp}
\DeclareUnicodeCharacter{03D5}{$\phi$}
\DeclareUnicodeCharacter{03C6}{$\phi$}
\DeclareUnicodeCharacter{03B1}{$\alpha$}
\DeclareUnicodeCharacter{03B2}{$\beta$}
\DeclareUnicodeCharacter{03B3}{$\gamma$}
\DeclareUnicodeCharacter{03B4}{$\delta$}
\DeclareUnicodeCharacter{03B5}{$\epsilon$}
\DeclareUnicodeCharacter{03B7}{$\eta$}
\DeclareUnicodeCharacter{03B8}{$\theta$}
\DeclareUnicodeCharacter{03BB}{$\lambda$}
\DeclareUnicodeCharacter{03BC}{$\mu$}
\DeclareUnicodeCharacter{03C1}{$\rho$}
\DeclareUnicodeCharacter{03C3}{$\sigma$}
\DeclareUnicodeCharacter{03C8}{$\psi$}
\DeclareUnicodeCharacter{03C9}{$\omega$}
\DeclareUnicodeCharacter{03A3}{$\Sigma$}
\DeclareUnicodeCharacter{03A0}{$\Pi$}
\setlength{\columnsep}{0.15in}
\setlength{\parindent}{0pt}
\setlength{\parskip}{0pt}
\raggedright
\begin{document}
\scriptsize
"""

LATEX_FOOTER = r"""
\end{multicols}
\end{document}
"""

# ── Chunk prompt (with color tags variant) ────────────────────────────────────
CHUNK_PROMPT_COLOR = r"""Convert the content blocks below into raw LaTeX lines for a dense cheatsheet column.
Output ONLY LaTeX — no markdown fences, no explanation, nothing else.

STRICT RULES:
1. Include EVERY block — do not skip any.
2. Each block line has format:  (type) TAG:\cmd content
   You MUST output \cmd at the very start of each block (before the content).
   Example input:  (formula) TAG:\ftag $H(s) = Y(s)/X(s)$
   Example output: \ftag $H(s) = Y(s)/X(s)$\\
3. Topic headers: \vspace{{2pt}}\textbf{{Topic Name}}\\
   Do NOT repeat a topic header for consecutive blocks with the same topic.
4. Each block MUST end with \\ on the same line — no exceptions.
5. CRITICAL — math/text boundary: after a closing $ there MUST be a space before any word.
   Correct: $formula$ word here\\   Wrong: $formula$Word or $formula$\Word
6. Formulas: use $...$ inline math — all math symbols must be inside $...$
7. Plain text must NOT contain unescaped: _ % & # ^ ~
   Underscore outside math: \_   Percent: \%   Ampersand: \&   Hash: \#
8. Code/identifiers: wrap in \texttt{{...}}
9. No \section, \begin, \end, \documentclass — raw column content only.
10. Braces must be balanced — every \textbf{{ must have a matching }}.

Blocks:
{blocks}
"""

# ── Chunk prompt (no color tags variant) ─────────────────────────────────────
CHUNK_PROMPT_NOCOLOR = r"""Convert the content blocks below into raw LaTeX lines for a dense cheatsheet column.
Output ONLY LaTeX — no markdown fences, no explanation, nothing else.

STRICT RULES:
1. Include EVERY block — do not skip any.
2. Topic headers: \vspace{{2pt}}\textbf{{Topic Name}}\\
   Do NOT repeat a topic header for consecutive blocks with the same topic.
3. Each block MUST end with \\ on the same line — no exceptions.
4. CRITICAL — math/text boundary: after a closing $ there MUST be a space before any word.
   Correct: $formula$ word here\\   Wrong: $formula$Word or $formula$\Word
5. Formulas: use $...$ inline math — all math symbols must be inside $...$
6. Plain text must NOT contain unescaped: _ % & # ^ ~
   Underscore outside math: \_   Percent: \%   Ampersand: \&   Hash: \#
7. Code/identifiers: wrap in \texttt{{...}}
8. No \section, \begin, \end, \documentclass — raw column content only.
9. Braces must be balanced — every \textbf{{ must have a matching }}.

Blocks:
{blocks}
"""


# ════════════════════════════════════════════════════════════════════════════
# LaTeX sanitization (DO NOT MODIFY — working correctly)
# ════════════════════════════════════════════════════════════════════════════

def sanitize_for_latex(text: str) -> str:
    """Normalize Unicode and escape LaTeX special chars in plain text regions."""
    replacements = [
        ("\u202f", " "),
        ("\u00a0", " "),
        ("\u2013", "--"),
        ("\u2014", "---"),
        ("\u2011", "-"),
        ("\u2010", "-"),
        ("\u2018", "`"),
        ("\u2019", "'"),
        ("\u201c", "``"),
        ("\u201d", "''"),
        ("\u2022", r"\textbullet{}"),
        ("\u2026", r"\ldots{}"),
        ("\u2192", r"$\rightarrow$"),
        ("\u2190", r"$\leftarrow$"),
        ("\u21d2", r"$\Rightarrow$"),
        ("\u21d0", r"$\Leftarrow$"),
        ("\u00d7", r"$\times$"),
        ("\u00f7", r"$\div$"),
        ("\u2260", r"$\neq$"),
        ("\u2264", r"$\leq$"),
        ("\u2265", r"$\geq$"),
        ("\u221e", r"$\infty$"),
        ("\u2208", r"$\in$"),
        ("\u2209", r"$\notin$"),
        ("\u2207", r"$\nabla$"),
        ("\u2211", r"$\sum$"),
        ("\u220f", r"$\prod$"),
        ("\u03b1", r"$\alpha$"),
        ("\u03b2", r"$\beta$"),
        ("\u03b3", r"$\gamma$"),
        ("\u03b4", r"$\delta$"),
        ("\u03b5", r"$\epsilon$"),
        ("\u03b7", r"$\eta$"),
        ("\u03b8", r"$\theta$"),
        ("\u03bb", r"$\lambda$"),
        ("\u03bc", r"$\mu$"),
        ("\u03c1", r"$\rho$"),
        ("\u03c3", r"$\sigma$"),
        ("\u03c6", r"$\phi$"),
        ("\u03d5", r"$\phi$"),
        ("\u03c8", r"$\psi$"),
        ("\u03c9", r"$\omega$"),
        ("\u03a3", r"$\Sigma$"),
        ("\u03a0", r"$\Pi$"),
    ]
    for uni, latex in replacements:
        text = text.replace(uni, latex)

    dollar_count = text.count("$")
    if dollar_count % 2 != 0:
        text = text.replace("%", r"\%")
        return text

    parts = text.split("$")
    result = []
    for i, part in enumerate(parts):
        if i % 2 == 1:
            result.append("$" + part + "$")
        else:
            part = part.replace("%",  r"\%")
            part = part.replace("&",  r"\&")
            part = part.replace("#",  r"\#")
            part = part.replace("^",  r"\textasciicircum{}")
            part = part.replace("~",  r"\textasciitilde{}")
            part = part.replace("_",  r"\_")
            result.append(part)
    return "".join(result)


def clean_llm_latex(text: str) -> str:
    r"""Fix common LLM output mistakes that cause pdflatex errors."""
    text = re.sub(r'\$([^$\n]+\$)(\\)([A-Z][a-zA-Z]*)', r'$\1 \3', text)
    text = re.sub(r'(\$[^$\n]+\$)([A-Za-z])', r'\1 \2', text)
    text = re.sub(r'\$\s*\\\\\s*\n\s*([a-zA-Z])', r'$\\\1', text)

    def fix_math_escapes(m):
        inner = m.group(1)
        inner = re.sub(r'\\\\([a-zA-Z])', r'\\\1', inner)
        return '$' + inner + '$'
    text = re.sub(r'\$([^$\n]+)\$', fix_math_escapes, text)

    text = re.sub(r'\\(begin|end)\{\{(\w+)\}\}', r'\\\1{\2}', text)
    text = re.sub(r'^\s*\\\\\s*$', '', text, flags=re.MULTILINE)
    text = re.sub(r'(\\textbf\{[^}\\]*)(\\\\)', r'\1}\2', text)
    text = re.sub(r'\\textbf\{\{([^}]*)\}\}', r'\\textbf{\1}', text)
    return text


# ════════════════════════════════════════════════════════════════════════════
# Block → text line conversion
# ════════════════════════════════════════════════════════════════════════════

def blocks_to_lines(ordered_blocks: list[dict], color: bool) -> list[str]:
    """
    Convert ordered blocks to flat text lines for LLM consumption.
    With color=True, prefixes each block with TAG:\\cmd so the LLM emits
    the colored type marker in its output.
    """
    lines = []
    current_topic = None
    for b in ordered_blocks:
        topic = b.get("topic", "")
        btype = b.get("type", "concept")
        text  = b.get("content", "").strip()
        if not text or len(text) > 600:
            continue
        text = sanitize_for_latex(text)
        if topic != current_topic:
            lines.append(f"TOPIC: {topic}")
            current_topic = topic
        if color:
            tag = TYPE_TAGS.get(btype, r"\ctag")
            lines.append(f"  ({btype}) TAG:{tag} {text}")
        else:
            lines.append(f"  ({btype}) {text}")
    return lines


def chunk_lines(lines: list[str], chunk_words: int = 500) -> list[list[str]]:
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


# ════════════════════════════════════════════════════════════════════════════
# LLM call
# ════════════════════════════════════════════════════════════════════════════

def call_llm_chunk(block_text: str, color: bool) -> str:
    """Send one chunk of blocks to the LLM, return raw LaTeX string."""
    prompt = CHUNK_PROMPT_COLOR if color else CHUNK_PROMPT_NOCOLOR
    user_msg = prompt.format(blocks=block_text)

    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": user_msg}],
        max_tokens=4096,
        temperature=0.1,
    )
    raw = response.choices[0].message.content or ""
    finish = response.choices[0].finish_reason
    raw = raw.replace("```latex", "").replace("```tex", "").replace("```", "").strip()
    return raw, finish



# ════════════════════════════════════════════════════════════════════════════
# PDF compile
# ════════════════════════════════════════════════════════════════════════════

def compile_latex(tex_path: str) -> str | None:
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode",
             "-output-directory", os.path.dirname(tex_path), tex_path],
            capture_output=True, text=True, timeout=60
        )
        pdf_path = tex_path.replace(".tex", ".pdf")
        if os.path.exists(pdf_path):
            return pdf_path
        print("  [pdflatex] Compilation failed. Log tail:")
        print(result.stdout[-1000:])
        return None
    except FileNotFoundError:
        print("  [pdflatex] Not found — install TeX Live or MiKTeX to compile.")
        return None
    except subprocess.TimeoutExpired:
        print("  [pdflatex] Timed out.")
        return None


# ════════════════════════════════════════════════════════════════════════════
# Main
# ════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="Generate a LaTeX cheatsheet from all parsed JSONs in a course folder."
    )
    parser.add_argument("course_dir",
                        help="Course directory (contains parsed/ subfolder with JSON results)")
    parser.add_argument("--pages", type=int, default=1,
                        help="Strict page limit — content is truncated to fit (default: 1)")
    parser.add_argument("--columns", type=int, default=3,
                        help="Number of columns per page (default: 3)")
    parser.add_argument("--no-color", action="store_true",
                        help="Disable color-coded type tags (F/D/C/E/X markers)")
    parser.add_argument("--out", default=None,
                        help="Output filename stem (default: <course>_cheatsheet)")
    parser.add_argument("--compile", action="store_true",
                        help="Compile the .tex to PDF with pdflatex after generation")
    args = parser.parse_args()

    color = not args.no_color
    course_dir = Path(args.course_dir)
    course_name = course_dir.name

    print("\n📋 Cheatsheet Generator")
    print("─" * 60)
    print(f"  Course:  {course_name}")
    print(f"  Pages:   {args.pages} (strict limit)")
    print(f"  Columns: {args.columns}")
    print(f"  Color:   {'on' if color else 'off'}")
    print("─" * 60)

    # ── 1. Load all parsed JSONs ──────────────────────────────────────────────
    print(f"\n[1] Loading parsed JSONs...")
    all_data = load_parsed_jsons(course_dir)

    emphasis_loaded = [s for s in all_data if any(s.startswith(e.split("_")[0]) for e in EMPHASIS_SUFFIXES)]
    content_loaded  = [s for s in all_data if any(s.startswith(c.split("_")[0]) for c in CONTENT_SUFFIXES)]
    print(f"  Emphasis sources: {emphasis_loaded or ['none']}")
    print(f"  Content sources:  {content_loaded or ['none']}")

    if not content_loaded:
        print("\n  ERROR: no content sources found (need notes_result or slides_result).")
        sys.exit(1)

    # ── 2. Build topic ranking from emphasis sources ───────────────────────────
    print(f"\n[2] Building topic ranking from emphasis sources...")
    topic_ranking = build_topic_ranking(all_data)

    if topic_ranking:
        print(f"  {len(topic_ranking)} topics ranked. Top 10:")
        for topic, count in topic_ranking[:10]:
            print(f"    {topic:<45} {count}x")
        if len(topic_ranking) > 10:
            print(f"    ... and {len(topic_ranking) - 10} more")
    else:
        print("  No emphasis data found — content will use type-only ordering.")

    # ── 3. Build ordered block list ───────────────────────────────────────────
    print(f"\n[3] Ordering content blocks...")
    ordered_blocks = build_ordered_blocks(all_data, topic_ranking)
    total = len(ordered_blocks)

    # Show priority breakdown
    type_counts: dict[str, int] = {}
    for b in ordered_blocks:
        t = b.get("type", "concept")
        type_counts[t] = type_counts.get(t, 0) + 1
    print(f"  {total} blocks total:")
    for btype in ["formula", "definition", "diagram_hint", "example", "concept"]:
        count = type_counts.get(btype, 0)
        if count:
            print(f"    {btype:<15} {count}")

    # ── 4. Apply strict page cap ──────────────────────────────────────────────
    print(f"\n[4] Applying page budget ({args.pages} page(s), {args.columns} col)...")
    capped_blocks, was_truncated = cap_blocks(ordered_blocks, args.pages, args.columns)

    if was_truncated:
        dropped = total - len(capped_blocks)
        print(f"  ⚠ Truncated: keeping {len(capped_blocks)}/{total} blocks "
              f"({dropped} lowest-priority blocks dropped to fit {args.pages} page(s))")
    else:
        print(f"  All {total} blocks fit within {args.pages} page(s)")

    # ── 5. Convert blocks to LLM input lines ──────────────────────────────────
    all_lines = blocks_to_lines(capped_blocks, color=color)
    chunks = chunk_lines(all_lines, chunk_words=500)
    print(f"\n[5] Generating LaTeX: {len(all_lines)} lines → {len(chunks)} chunk(s)")

    # ── 6. Call LLM for each chunk ────────────────────────────────────────────
    body_parts = []
    for i, chunk in enumerate(chunks, start=1):
        block_text = "\n".join(chunk)
        print(f"  chunk {i}/{len(chunks)}: {len(chunk)} lines...", end=" ", flush=True)
        raw_chunk, finish = call_llm_chunk(block_text, color=color)
        raw_chunk = clean_llm_latex(raw_chunk)
        body_parts.append(raw_chunk)
        print(f"{len(raw_chunk)} chars (finish: {finish})")

    # ── 7. Assemble document ──────────────────────────────────────────────────
    header = LATEX_HEADER_COLOR if color else LATEX_HEADER_NOCOLOR
    multicols_open  = f"\\begin{{multicols}}{{{args.columns}}}\n"
    body = "\n\n".join(body_parts)
    latex = header + multicols_open + "\n" + body + "\n" + LATEX_FOOTER
    print(f"\n  Total LaTeX: {len(latex):,} chars")

    # ── 8. Save ───────────────────────────────────────────────────────────────
    generated_dir = course_dir / "generated"
    generated_dir.mkdir(exist_ok=True)

    stem     = args.out if args.out else f"{course_name}_cheatsheet"
    stem     = stem if not stem.endswith(".tex") else stem[:-4]
    color_tag = "" if color else "_nocolor"
    out_name  = f"{stem}_p{args.pages}c{args.columns}{color_tag}.tex"
    out_path  = generated_dir / out_name

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(latex)
    print(f"  [saved] {out_path}")

    # ── 9. Optional compile ───────────────────────────────────────────────────
    if args.compile:
        print("\n[9] Compiling to PDF...")
        pdf = compile_latex(str(out_path))
        if pdf:
            print(f"  [pdf] {pdf}")

    print("\n" + "═" * 60)
    print(f"  Done.")
    if not args.compile:
        print(f"  Compile: pdflatex \"{out_path}\"")
    print("═" * 60)


# ════════════════════════════════════════════════════════════════════════════
# Block budget helper (exported for testing)
# ════════════════════════════════════════════════════════════════════════════

def cap_blocks(
    ordered_blocks: list[dict],
    pages: int,
    columns: int,
) -> tuple[list[dict], bool]:
    CHARS_PER_BLOCK = 80
    budget = pages * columns * CHARS_PER_PAGE_PER_COL
    max_blocks = budget // CHARS_PER_BLOCK
    if len(ordered_blocks) <= max_blocks:
        return ordered_blocks, False
    return ordered_blocks[:max_blocks], True


if __name__ == "__main__":
    main()