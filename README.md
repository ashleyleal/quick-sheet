# QuickSheet.AI 📚

> **Turn your course materials into an exam-ready cheatsheet in minutes.**

QuickSheet.AI analyzes your past exams, lecture notes, slides, and assignments to automatically generate a dense, prioritized cheatsheet as a LaTeX PDF. Topics that appear most frequently on past exams always come first. You set the page limit — it fills it optimally.

---

## How it works

```
Upload PDFs (exams, notes, slides, assignments)
         ↓
   Extract text + images
         ↓
   LLM analyzes each file type
         ↓
   Topics ranked by exam frequency
         ↓
   Content ordered by importance
         ↓
   LaTeX generated + compiled to PDF
```

Each file type has its own pipeline:
- **Past exams** → extract question topics and count frequency
- **Lecture notes / slides** → extract formulas, definitions, key concepts
- **Assignments** → identify solution patterns and methods
- **Syllabus** → extract topic weights and assessment emphasis
- **Prof hints** → boost importance of explicitly flagged topics

All signals are merged into a single importance score per topic. High-frequency exam topics always appear first, with formulas before definitions before concepts within each topic.

---

## Features

- 🎯 **Exam-frequency ordering** — the most tested topics always appear first
- 📄 **Strict page limits** — content is truncated to fit exactly N pages
- 🎨 **Color-coded type tags** — instantly distinguish formulas, definitions, concepts, examples, diagrams
- 🔍 **OCR support** — scanned PDFs and handwritten notes handled via Tesseract
- 🖼️ **Diagram extraction** — embedded images from slides are pulled into the cheatsheet
- ✏️ **Editable output** — get both the compiled PDF and the raw `.tex` source
- ⚙️ **Config-driven** — save settings per course, override with CLI flags anytime

---

## Setup

### Prerequisites

- Python 3.10+
- An OpenAI-compatible API key
- (Optional) Tesseract for OCR on scanned PDFs
- (Optional) pdflatex for compiling the `.tex` output

### Install

```bash
git clone https://github.com/your-username/quick-sheet.git
cd quick-sheet

python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
```

### Environment

Create a `.env` file in the project root:

```
OPENAI_API_KEY=your_key_here
```

### Optional: OCR (for scanned PDFs)

```bash
pip install pytesseract Pillow
```

Download the Tesseract binary:
- **Windows:** [github.com/UB-Mannheim/tesseract/wiki](https://github.com/UB-Mannheim/tesseract/wiki)
- **macOS:** `brew install tesseract`
- **Linux:** `sudo apt install tesseract-ocr`

### Optional: PDF compilation

- **Windows:** [MiKTeX](https://miktex.org/) or [TeX Live](https://tug.org/texlive/)
- **macOS:** `brew install --cask mactex`
- **Linux:** `sudo apt install texlive-full`

Without pdflatex the `.tex` file is still generated and can be compiled manually or via [Overleaf](https://overleaf.com).

---

## Running

### Web UI

```bash
python -m streamlit run ui/streamlit_app.py
```

1. Enter your course code in the sidebar
2. Upload PDFs into the appropriate type slots
3. Adjust page limit, columns, and color settings
4. Click **Generate Final Cheatsheet**
5. Download the PDF and/or `.tex` source

### Command line

```bash
# Step 1 — parse all PDFs in a course folder
python app/processing/run_all_pipelines.py data/uploads/ECE342

# Step 2 — generate the cheatsheet
python app/processing/generate_sheet.py data/uploads/ECE342 --pages 2 --columns 4 --compile
```

Run either script with `--help` for all options.

---

## Project structure

```
quick-sheet/
├── ui/
│   └── streamlit_app.py          # Streamlit frontend
├── app/
│   ├── main.py                   # Pipeline orchestrator (called by UI)
│   └── processing/
│       ├── run_all_pipelines.py  # PDF parsing → JSON
│       └── generate_sheet.py    # JSON → LaTeX → PDF
├── data/
│   ├── uploads/
│   │   └── <course_code>/
│   │       ├── exam/             # Past exam PDFs
│   │       ├── notes/            # Lecture note PDFs
│   │       ├── slide_deck/       # Slide PDFs
│   │       ├── assignment/       # Assignment PDFs
│   │       ├── syllabus/         # Syllabus PDFs
│   │       ├── misc/             # Prof hints, other
│   │       ├── parsed/           # Auto-generated JSON results
│   │       └── generated/        # Output .tex and .pdf files
│   └── configs/
│       └── <course_code>.json    # Per-course settings
├── .env                          # API key (not committed)
└── requirements.txt
```

---

## Content priority

Within the page budget, blocks are ordered:

| Priority | Type |
|---|---|
| 1 | High-frequency exam topics |
| 2 | Formulas |
| 3 | Definitions |
| 4 | Diagrams |
| 5 | Examples |
| 6 | Concepts |

When the page limit is hit, the lowest-priority content is dropped first — so you always get the most important content.

---

## Color tags

When color mode is on, each block gets a small colored label:

| Tag | Color | Meaning |
|---|---|---|
| **F** | Blue | Formula |
| **D** | Orange | Definition |
| **C** | Green | Concept |
| **E** | Purple | Example |
| **X** | Grey | Diagram |

---

## Tech stack

| Component | Technology |
|---|---|
| Frontend | Streamlit |
| PDF extraction | PyMuPDF (fitz) |
| OCR fallback | Tesseract + pytesseract |
| Image processing | Pillow |
| LLM | OpenAI-compatible API |
| Output format | LaTeX (pdflatex / TeX Live) |
| Language | Python 3.10+ |

---
