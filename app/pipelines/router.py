"""
pipelines/router.py

Maps course folder structure to pipelines and output formats.

Folder layout expected:
    <course>/
        exam/          → exam_pipeline        (content emphasis)
        assignment/    → assignment_pipeline   (content emphasis)
        notes/         → notes_pipeline        (content)
        slide_deck/    → slide_deck_pipeline   (content)
        syllabus/      → syllabus_pipeline     (content emphasis)
        misc/          → misc_pipeline         (both)

Output format classification:
    CONTENT_EMPHASIS  → has "questions" key  → feeds importance scorer
    CONTENT           → has "topics"/"blocks" → feeds cheatsheet content builder
"""

from enum import Enum
from pathlib import Path


class OutputFormat(str, Enum):
    CONTENT_EMPHASIS = "content_emphasis"   # like exam: {"questions": [...]}
    CONTENT          = "content"            # like notes: {"topics": [...], "blocks": [...]}
    BOTH             = "both"               # misc: has both


# Maps subfolder name → (pipeline_module, output_format, result_suffix)
FOLDER_PIPELINE_MAP: dict[str, tuple[str, OutputFormat, str]] = {
    "exam":        ("pipelines.exam_pipeline",       OutputFormat.CONTENT_EMPHASIS, "exam_result"),
    "assignment":  ("pipelines.assignment_pipeline", OutputFormat.CONTENT_EMPHASIS, "assignment_result"),
    "syllabus":    ("pipelines.syllabus_pipeline",   OutputFormat.CONTENT_EMPHASIS, "syllabus_result"),
    "notes":       ("pipelines.notes_pipeline",      OutputFormat.CONTENT,          "notes_result"),
    "slide_deck":  ("pipelines.slide_deck_pipeline", OutputFormat.CONTENT,          "slides_result"),
    "misc":        ("pipelines.misc_pipeline",       OutputFormat.BOTH,             "misc_result"),
}


def get_pipeline_for_folder(folder_name: str) -> tuple[str, OutputFormat, str] | None:
    """Return (module_path, output_format, result_suffix) for a folder name, or None."""
    return FOLDER_PIPELINE_MAP.get(folder_name.lower())


def discover_course_inputs(course_dir: str | Path) -> dict[str, list[Path]]:
    """
    Scan a course directory and return a dict mapping folder names to PDF paths.
    Only returns folders that have known pipelines and contain at least one PDF.

    Example return:
        {
            "exam":       [Path("course/exam/2023_exam.pdf")],
            "notes":      [Path("course/notes/week1.pdf"), Path("course/notes/week2.pdf")],
            "syllabus":   [Path("course/syllabus/syllabus.pdf")],
        }
    """
    course_path = Path(course_dir)
    result: dict[str, list[Path]] = {}

    for folder_name in FOLDER_PIPELINE_MAP:
        folder = course_path / folder_name
        if folder.is_dir():
            pdfs = sorted(folder.glob("*.pdf"))
            if pdfs:
                result[folder_name] = pdfs

    return result


def load_existing_results(course_dir: str | Path) -> dict[str, dict]:
    """
    Load any already-processed JSON result files from the course folder.
    Returns dict mapping folder_name → parsed JSON.
    Useful for re-running only the generation step without re-parsing.
    """
    import json
    course_path = Path(course_dir)
    results: dict[str, dict] = {}

    for folder_name, (_, _, suffix) in FOLDER_PIPELINE_MAP.items():
        folder = course_path / folder_name
        if folder.is_dir():
            json_files = list(folder.glob(f"*_{suffix}.json"))
            if json_files:
                with open(json_files[0], encoding="utf-8") as f:
                    results[folder_name] = json.load(f)

    return results
