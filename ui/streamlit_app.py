import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os
import sys
from pathlib import Path

from color_palette import palette_selector_ui, generate_css
from config import ConfigManager, settings_sidebar

# ── Hook into backend ─────────────────────────────────────────────────────────
ROOT = Path(__file__).parent.parent                    # quick-sheet/
sys.path.insert(0, str(ROOT / "app"))                  # for main.py
sys.path.insert(0, str(ROOT / "app" / "processing"))   # for run_all_pipelines, generate_sheet
from main import run_pipeline

config_manager = ConfigManager()

selected_palette = palette_selector_ui()
css = generate_css(selected_palette)

# Page configuration
st.set_page_config(
    page_title="AI Cheatsheet Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown(css, unsafe_allow_html=True)

# Main title
st.markdown('<h1 class="main-header">📚 QuickSheet.AI Cheatsheet Generator</h1>', unsafe_allow_html=True)
st.markdown("Transform your course materials into a comprehensive, exam-ready cheatsheet powered by QuickSheet.AI.")

# Get settings from sidebar — returns dict with course_code, course_name, formatting etc.
config_data = settings_sidebar(config_manager)
course_code = config_data.get("course_code", "") if config_data else ""

# Main content area
col1, col2 = st.columns([3, 2])

with col1:
    st.markdown('<h2 class="sub-header">📤 Upload Course Materials</h2>', unsafe_allow_html=True)

    file_types = {
        "exam":         {"name": "Past Exams",          "desc": "Extract topics & question frequency",   "color": "exam-tag"},
        "assignment":   {"name": "Assignments",          "desc": "Identify problem patterns & methods",   "color": "assignment-tag"},
        "notes":        {"name": "Lecture Notes",        "desc": "Extract formulas, definitions, concepts","color": "notes-tag"},
        "slides":       {"name": "Slide Decks",          "desc": "Extract key concepts & diagrams",       "color": "slides-tag"},
        "instructions": {"name": "Instructions/Hints",   "desc": "Professor emphasis & hints",            "color": "instructions-tag"},
        "other":        {"name": "Other Materials",      "desc": "Additional resources",                  "color": "other-tag"},
    }

    uploaded_files = {}

    for file_type, info in file_types.items():
        st.markdown(f"#### {info['name']}")
        st.markdown(f"<span class='file-type-tag {info['color']}'>{info['desc']}</span>",
                    unsafe_allow_html=True)

        uploaded = st.file_uploader(
            f"Upload {info['name']} (PDF only)",
            type="pdf",
            key=f"{file_type}_uploader",
            accept_multiple_files=True,
            help=f"Upload one or more PDF files for {info['name'].lower()}",
        )

        if uploaded:
            uploaded_files[file_type] = uploaded
            if course_code:
                save_dir = Path(f"data/uploads/{course_code}/{file_type}")
                save_dir.mkdir(parents=True, exist_ok=True)
                for file in uploaded:
                    (save_dir / file.name).write_bytes(file.getbuffer())
                st.success(f"✓ {len(uploaded)} file(s) saved to {save_dir}")
            else:
                st.warning("Set a Course Code in the sidebar before uploading so files are saved correctly.")

    st.markdown('<h2 class="sub-header">✏️ Additional Instructions & Emphasis</h2>', unsafe_allow_html=True)

    professor_hints = st.text_area(
        "Professor Hints & Emphasis",
        placeholder="Enter any additional instructions, topics to emphasize, or specific requirements...",
        height=150,
    )

    # Save hints as a misc text file so the pipeline can pick it up
    if professor_hints.strip() and course_code:
        hints_dir = Path(f"data/uploads/{course_code}/misc")
        hints_dir.mkdir(parents=True, exist_ok=True)
        (hints_dir / "professor_hints.txt").write_text(professor_hints, encoding="utf-8")

    priority_topics = st.text_input(
        "Priority Topics (comma-separated)",
        placeholder="e.g., Laplace Transform, Bode Plots, Nyquist Stability",
    )

    exam_date = st.date_input("Exam Date", value=None)

with col2:
    st.markdown('<h2 class="sub-header">📊 Processing Dashboard</h2>', unsafe_allow_html=True)

    total_files = sum(len(files) for files in uploaded_files.values() if files)
    st.metric("Total Files Uploaded", total_files)

    if uploaded_files:
        st.markdown("#### File Breakdown by Type")
        breakdown_data = [
            {"Type": file_types[ft]["name"], "Count": len(files), "Status": "Ready"}
            for ft, files in uploaded_files.items() if files
        ]
        st.dataframe(pd.DataFrame(breakdown_data), use_container_width=True)
    else:
        st.info("No files uploaded yet.")

    st.markdown("#### Processing Pipeline")
    for i, step in enumerate([
        "📥 File Upload", "📄 PDF Extraction", "🔪 Document Chunking",
        "🧠 LLM Analysis", "📊 Topic Scoring", "📝 LaTeX Generation", "📄 PDF Compilation",
    ]):
        ca, cb = st.columns([1, 4])
        ca.write(f"**{i+1}.**")
        cb.write(step)

    st.markdown('<h2 class="sub-header">👁️ Preview</h2>', unsafe_allow_html=True)

    if st.checkbox("Show Topic Importance Preview", value=False):
        st.markdown("#### Estimated Topic Importance")
        example_topics = {
            "Laplace Transform": {"frequency": 9, "score": 0.95},
            "Bode Plot": {"frequency": 7, "score": 0.82},
            "Nyquist Stability": {"frequency": 4, "score": 0.68},
            "Transfer Function": {"frequency": 12, "score": 0.91},
            "Partial Fraction Decomposition": {"frequency": 5, "score": 0.73},
        }
        for topic, data in example_topics.items():
            c1, c2, c3 = st.columns([3, 1, 1])
            c1.write(f"**{topic}**")
            c2.write(f"📊 {data['frequency']}")
            c3.progress(data["score"])

    st.markdown("#### Quick Actions")
    if st.button("🔍 Test PDF Processing", type="secondary"):
        st.info("Testing PDF extraction... (placeholder)")
    if st.button("📋 Generate Sample Output", type="secondary"):
        st.info("Generating sample cheatsheet... (placeholder)")

# ── Output configuration ──────────────────────────────────────────────────────
st.markdown("---")
st.markdown('<h2 class="sub-header">🎯 Output Configuration</h2>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📈 Content Weighting")
    exam_weight       = st.slider("Exam Frequency Weight",       0.0, 1.0, 0.4, 0.05)
    hint_weight       = st.slider("Professor Hints Weight",      0.0, 1.0, 0.3, 0.05)
    assignment_weight = st.slider("Assignment Patterns Weight",  0.0, 1.0, 0.3, 0.05)
    total_weight = exam_weight + hint_weight + assignment_weight
    if abs(total_weight - 1.0) > 0.01:
        st.warning(f"Weights sum to {total_weight:.2f}. Adjust to total 1.0.")

with col2:
    st.markdown("#### 🧩 Content Sections")
    include_definitions = st.checkbox("Definitions",          value=True)
    include_formulas    = st.checkbox("Formulas & Equations", value=True)
    include_diagrams    = st.checkbox("Diagrams & Figures",   value=True)
    include_examples    = st.checkbox("Worked Examples",      value=True)
    include_proofs      = st.checkbox("Proof Sketches",       value=False)
    include_mnemonics   = st.checkbox("Mnemonics",            value=False)

with col3:
    st.markdown("#### 📤 Export Options")
    output_format = st.selectbox("Output Format", ["LaTeX PDF", "Markdown", "HTML", "Word Document"])
    if output_format == "LaTeX PDF":
        st.multiselect("LaTeX Packages",
                       ["amsmath", "amssymb", "geometry", "graphicx", "tabularx", "xcolor", "hyperref"],
                       default=["amsmath", "geometry", "graphicx"])
    include_source = st.checkbox("Include LaTeX Source", value=True)
    compile_pdf    = st.checkbox("Compile to PDF",        value=True,
                                 help="Requires pdflatex installed on the server")

# ── Generate button ───────────────────────────────────────────────────────────
st.markdown("---")
_, center, _ = st.columns([1, 2, 1])
with center:
    generate_clicked = st.button(
        "🚀 Generate Final Cheatsheet",
        type="primary",
        use_container_width=True,
        disabled=(total_files == 0 and not professor_hints.strip()),
    )

if generate_clicked:
    if not course_code:
        st.error("Set a Course Code in the sidebar before generating.")
        st.stop()

    if total_files == 0 and not professor_hints.strip():
        st.error("Upload at least one file or enter professor hints.")
        st.stop()

    # ── Wire into backend via main.py ─────────────────────────────────────────
    progress_bar = st.progress(0.0)
    status_text  = st.empty()

    def progress_cb(fraction: float, message: str):
        progress_bar.progress(min(float(fraction), 1.0))
        status_text.write(f"_{message}_")

    with st.spinner("🤖 Running pipeline..."):
        result = run_pipeline(
            course_code=course_code,
            compile_pdf=compile_pdf,
            progress_cb=progress_cb,
        )

    progress_bar.empty()
    status_text.empty()

    if not result["success"]:
        st.error(f"Pipeline failed: {result['error']}")
        with st.expander("📋 Full log"):
            st.text("\n".join(result["log"]))
        st.stop()

    st.success("✅ Cheatsheet generated!")
    if compile_pdf and result["pdf_path"]:
        st.balloons()

    # ── Downloads ─────────────────────────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    with dl1:
        if result.get("latex"):
            st.download_button(
                "📄 Download LaTeX (.tex)",
                data=result["latex"].encode("utf-8"),
                file_name=f"cheatsheet_{course_code}_{datetime.now().strftime('%Y%m%d')}.tex",
                mime="text/plain",
                use_container_width=True,
            )
    with dl2:
        if result.get("pdf_path") and Path(result["pdf_path"]).exists():
            st.download_button(
                "📥 Download PDF",
                data=Path(result["pdf_path"]).read_bytes(),
                file_name=f"cheatsheet_{course_code}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        elif compile_pdf:
            st.warning("⚠️ PDF compilation failed — download the .tex and compile locally.")

    # ── Results summary ───────────────────────────────────────────────────────
    if result.get("topic_ranking"):
        st.markdown("#### 📊 Topic Ranking (by exam frequency)")
        for topic, count in result["topic_ranking"][:15]:
            c1, c2 = st.columns([5, 1])
            c1.write(topic)
            c2.write(f"**{count}x**")

    if result.get("block_counts"):
        with st.expander("📋 Content Summary"):
            for btype, count in result["block_counts"].items():
                st.write(f"  **{btype}:** {count}")

    with st.expander("📋 Processing Log"):
        st.text("\n".join(result["log"]))

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center;color:#6B7280;font-size:0.9rem;">
    <p>QuickSheet.AI v1.0 • Powered by Streamlit & LLMs</p>
    <p>Each file type has its own processing pipeline for optimal topic extraction</p>
</div>
""", unsafe_allow_html=True)

if "generate_clicked" not in st.session_state:
    st.session_state.generate_clicked = False