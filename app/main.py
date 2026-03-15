"""
app/processing/main.py

Pure Python orchestrator — no Streamlit.
Called by ui/streamlit_app.py when the user clicks Generate.

Entry point:
    result = run_pipeline(course_code, config_path)

Returns a dict with keys:
    success      bool
    tex_path     str | None
    pdf_path     str | None
    topic_ranking  list[tuple[str, int]]
    block_counts   dict[str, int]
    log          list[str]
    error        str | None
"""

import os
import sys
import json
from pathlib import Path

# ── Resolve paths relative to this file so imports work regardless of cwd ────
THIS_DIR   = Path(__file__).resolve().parent          # app/
PROCESSING = THIS_DIR / "processing"                  # app/processing/
ROOT       = THIS_DIR.parent                          # project root
UPLOADS    = ROOT / "data" / "uploads"
CONFIG_DIR = ROOT / "data" / "configs"

# Add both app/ and app/processing/ so all imports resolve
sys.path.insert(0, str(THIS_DIR))
sys.path.insert(0, str(PROCESSING))

from run_all_pipelines import (
    extract_pages,
    pages_to_chunks,
    call_llm,
    merge,
    PROMPTS,
    RESULT_SUFFIXES,
    MERGE_KEYS,
    DEFAULT_MODEL,
    DEFAULT_CHUNK_SIZE,
)
from generate_sheet import (
    load_parsed_jsons,
    build_topic_ranking,
    build_ordered_blocks,
    cap_blocks,
    blocks_to_lines,
    chunk_lines,
    call_llm_chunk,
    clean_llm_latex,
    compile_latex,
    LATEX_HEADER_COLOR,
    LATEX_HEADER_NOCOLOR,
    LATEX_FOOTER,
)


# ════════════════════════════════════════════════════════════════════════════
# Config loader
# ════════════════════════════════════════════════════════════════════════════

def load_config(course_code: str) -> dict:
    """
    Load settings from data/configs/<course_code>*.json.
    Falls back to most-recent config if no course-specific one exists.
    Returns a flat settings dict with safe defaults.
    """
    raw = {}

    if CONFIG_DIR.is_dir():
        candidates = sorted(CONFIG_DIR.glob("*.json"),
                            key=lambda p: p.stat().st_mtime, reverse=True)
        matched = next((p for p in candidates
                        if course_code.lower() in p.stem.lower()), None)
        chosen  = matched or (candidates[0] if candidates else None)

        if chosen:
            with open(chosen, encoding="utf-8") as f:
                raw = json.load(f)

    settings   = raw.get("settings", {})
    formatting = settings.get("formatting", {})
    color_scheme = formatting.get("color_scheme", "Colorful")

    return {
        "course_name":      settings.get("course_name", ""),
        "course_code":      settings.get("course_code", course_code),
        "pages":            int(formatting.get("num_pages", 2)),
        "columns":          int(formatting.get("columns", 3)),
        "color":            color_scheme.lower() != "monochrome",
        "include_diagrams": formatting.get("include_diagrams", True),
        "include_examples": formatting.get("include_examples", True),
    }


# ════════════════════════════════════════════════════════════════════════════
# Pipeline runner
# ════════════════════════════════════════════════════════════════════════════

def run_pipelines(
    course_dir:  Path,
    config:      dict,
    log:         list[str],
    progress_cb  = None,
) -> dict[str, dict]:
    """
    Run the appropriate pipeline for every type subfolder under course_dir.
    Saves results to course_dir/parsed/<course>_<type>_result.json.
    Returns {suffix: data}.
    """
    parsed_dir  = course_dir / "parsed"
    parsed_dir.mkdir(exist_ok=True)
    course_name = course_dir.name

    folders = [f for f in PROMPTS if (course_dir / f).is_dir()
               and list((course_dir / f).glob("*.pdf"))]
    all_parsed: dict[str, dict] = {}

    for idx, folder_type in enumerate(folders):
        folder = course_dir / folder_type
        suffix = RESULT_SUFFIXES[folder_type]
        pdfs   = sorted(folder.glob("*.pdf"))

        msg = f"[{idx+1}/{len(folders)}] {folder_type} — {len(pdfs)} PDF(s)"
        log.append(msg)
        if progress_cb:
            progress_cb(idx / len(folders), msg)

        all_results = []
        for pdf_path in pdfs:
            log.append(f"  → {pdf_path.name}")
            pdf_bytes = pdf_path.read_bytes()
            pages  = extract_pages(pdf_bytes)
            chunks = pages_to_chunks(pages, DEFAULT_CHUNK_SIZE)
            prompt = PROMPTS[folder_type]

            chunk_results = []
            for i, chunk in enumerate(chunks, 1):
                result = call_llm(prompt, chunk, DEFAULT_MODEL)
                status = "ok" if result else "failed"
                log.append(f"    chunk {i}/{len(chunks)}: {status}")
                if result:
                    chunk_results.append(result)

            if chunk_results:
                all_results.append(merge(folder_type, chunk_results))

        if all_results:
            combined = merge(folder_type, all_results)
            out_path = parsed_dir / f"{course_name}_{suffix}.json"
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(combined, f, indent=2)
            all_parsed[suffix] = combined

            n_q = len(combined.get("questions", []))
            n_b = len(combined.get("blocks", []))
            log.append(f"  Saved: {n_q} questions, {n_b} blocks → {out_path.name}")

    if progress_cb:
        progress_cb(1.0, "Parsing complete")

    return all_parsed


def generate_cheatsheet(
    course_dir:   Path,
    parsed_data:  dict[str, dict],
    config:       dict,
    log:          list[str],
    progress_cb   = None,
) -> tuple[str, Path | None]:
    """
    Build the LaTeX cheatsheet from parsed JSONs using config settings.
    Returns (latex_str, tex_path).
    """
    pages   = config["pages"]
    columns = config["columns"]
    color   = config["color"]

    if progress_cb:
        progress_cb(0.05, "Building topic ranking...")

    topic_ranking  = build_topic_ranking(parsed_data)
    ordered_blocks = build_ordered_blocks(parsed_data, topic_ranking)

    # Apply content type filters from config
    if not config.get("include_diagrams", True):
        ordered_blocks = [b for b in ordered_blocks if b.get("type") != "diagram_hint"]
    if not config.get("include_examples", True):
        ordered_blocks = [b for b in ordered_blocks if b.get("type") != "example"]

    capped, truncated = cap_blocks(ordered_blocks, pages, columns)
    log.append(f"  {len(capped)}/{len(ordered_blocks)} blocks after page cap")
    if truncated:
        log.append(f"  ⚠ {len(ordered_blocks) - len(capped)} low-priority blocks dropped")

    if progress_cb:
        progress_cb(0.15, "Converting blocks to LaTeX...")

    all_lines = blocks_to_lines(capped, color=color)
    chunks    = chunk_lines(all_lines)
    log.append(f"  {len(all_lines)} lines → {len(chunks)} LLM chunks")

    body_parts = []
    for i, chunk in enumerate(chunks, 1):
        if progress_cb:
            progress_cb(0.15 + (i / len(chunks)) * 0.75,
                        f"Generating chunk {i}/{len(chunks)}...")
        raw, finish = call_llm_chunk("\n".join(chunk), color=color)
        raw = clean_llm_latex(raw)
        body_parts.append(raw)
        log.append(f"  chunk {i}/{len(chunks)}: {len(raw)} chars (finish: {finish})")

    header         = LATEX_HEADER_COLOR if color else LATEX_HEADER_NOCOLOR
    multicols_open = f"\\begin{{multicols}}{{{columns}}}\n"
    body           = "\n\n".join(body_parts)
    latex          = header + multicols_open + "\n" + body + "\n" + LATEX_FOOTER

    generated_dir = course_dir / "generated"
    generated_dir.mkdir(exist_ok=True)

    color_tag = "" if color else "_nocolor"
    out_name  = f"{course_dir.name}_p{pages}c{columns}{color_tag}_cheatsheet.tex"
    tex_path  = generated_dir / out_name
    tex_path.write_text(latex, encoding="utf-8")
    log.append(f"  Saved: {tex_path}")

    if progress_cb:
        progress_cb(1.0, "LaTeX ready")

    return latex, tex_path


# ════════════════════════════════════════════════════════════════════════════
# Public entry point — called by streamlit_app.py
# ════════════════════════════════════════════════════════════════════════════

def run_pipeline(
    course_code:    str,
    compile_pdf:    bool = False,
    progress_cb     = None,
) -> dict:
    """
    Full pipeline for a course: parse PDFs → generate LaTeX → (optionally) compile PDF.

    Args:
        course_code:  e.g. "ECE342" — must match a folder under data/uploads/
        compile_pdf:  if True, run pdflatex on the generated .tex
        progress_cb:  optional callable(fraction: float, message: str)

    Returns:
        {
            "success":        bool,
            "tex_path":       str | None,
            "pdf_path":       str | None,
            "latex":          str | None,
            "topic_ranking":  list[tuple[str, int]],
            "block_counts":   dict[str, int],
            "log":            list[str],
            "error":          str | None,
        }
    """
    log: list[str] = []
    result = {
        "success":       False,
        "tex_path":      None,
        "pdf_path":      None,
        "latex":         None,
        "topic_ranking": [],
        "block_counts":  {},
        "log":           log,
        "error":         None,
    }

    try:
        # ── Locate course upload folder ───────────────────────────────────────
        course_dir = UPLOADS / course_code
        if not course_dir.is_dir():
            raise FileNotFoundError(
                f"No upload folder found for course '{course_code}'. "
                f"Expected: {course_dir}"
            )

        # ── Load config ───────────────────────────────────────────────────────
        config = load_config(course_code)
        log.append(f"Config: pages={config['pages']}, columns={config['columns']}, "
                   f"color={'on' if config['color'] else 'off'}")

        # ── Stage 1: Parse PDFs ───────────────────────────────────────────────
        log.append("\n── Stage 1: Parsing PDFs ──")
        parsed = run_pipelines(course_dir, config, log,
                               progress_cb=lambda f, m: progress_cb(f * 0.5, m) if progress_cb else None)

        if not parsed:
            raise ValueError("No content extracted. Check that PDFs were uploaded correctly.")

        # ── Stage 2: Generate LaTeX ───────────────────────────────────────────
        log.append("\n── Stage 2: Generating LaTeX ──")
        latex, tex_path = generate_cheatsheet(
            course_dir, parsed, config, log,
            progress_cb=lambda f, m: progress_cb(0.5 + f * 0.45, m) if progress_cb else None,
        )

        result["latex"]    = latex
        result["tex_path"] = str(tex_path)

        # ── Stage 3: Compile PDF (optional) ──────────────────────────────────
        if compile_pdf:
            log.append("\n── Stage 3: Compiling PDF ──")
            if progress_cb:
                progress_cb(0.95, "Compiling PDF...")
            pdf = compile_latex(str(tex_path))
            if pdf:
                result["pdf_path"] = pdf
                log.append(f"  PDF: {pdf}")
            else:
                log.append("  PDF compilation failed — LaTeX source still available")

        # ── Collect stats for UI ──────────────────────────────────────────────
        result["topic_ranking"] = build_topic_ranking(parsed)
        for data in parsed.values():
            for b in data.get("blocks", []):
                t = b.get("type", "concept")
                result["block_counts"][t] = result["block_counts"].get(t, 0) + 1

        if progress_cb:
            progress_cb(1.0, "Done!")

        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        log.append(f"\nERROR: {e}")

    return result