import streamlit as st
import pandas as pd
from datetime import datetime
import json
import os

from color_palette import palette_selector_ui, generate_css
from config import ConfigManager, settings_sidebar
# from processing import CheatsheetProcessor


config_manager = ConfigManager()
# processor = CheatsheetProcessor()

selected_palette = palette_selector_ui()
css = generate_css(selected_palette)

# Page configuration
st.set_page_config(
    page_title="AI Cheatsheet Generator",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)



# Custom CSS for better styling
# st.markdown("""
# <style>
#     .main-header {
#         font-size: 2.5rem;
#         color: #1E3A8A;
#         text-align: center;
#         margin-bottom: 1rem;
#     }
#     .sub-header {
#         font-size: 1.5rem;
#         color: #374151;
#         margin-top: 2rem;
#         margin-bottom: 1rem;
#         border-bottom: 2px solid #E5E7EB;
#         padding-bottom: 0.5rem;
#     }
#     .section-box {
#         background-color: #F9FAFB;
#         padding: 1.5rem;
#         border-radius: 10px;
#         border: 1px solid #E5E7EB;
#         margin-bottom: 1.5rem;
#     }
#     .file-type-tag {
#         display: inline-block;
#         padding: 0.25rem 0.75rem;
#         border-radius: 15px;
#         font-size: 0.85rem;
#         font-weight: 600;
#         margin-right: 0.5rem;
#         margin-bottom: 0.5rem;
#     }
#     .exam-tag { background-color: #FEF3C7; color: #92400E; }
#     .assignment-tag { background-color: #D1FAE5; color: #065F46; }
#     .notes-tag { background-color: #DBEAFE; color: #1E40AF; }
#     .slides-tag { background-color: #E0E7FF; color: #3730A3; }
#     .instructions-tag { background-color: #FCE7F3; color: #9D174D; }
#     .other-tag { background-color: #F3F4F6; color: #4B5563; }
# </style>
# """, unsafe_allow_html=True)


st.markdown(css, unsafe_allow_html=True)
# Main title
st.markdown('<h1 class="main-header">📚 QuickSheet.AI Cheatsheet Generator</h1>', unsafe_allow_html=True)
st.markdown("Transform your course materials into a comprehensive, exam-ready cheatsheet powered by QuickSheet.AI.")


# Get settings from sidebar
config_data = settings_sidebar(config_manager)


# # Sidebar for project settings
# with st.sidebar:
#     st.markdown("### 🛠️ Project Settings")
    
#     # Course info
#     course_name = st.text_input("Course Name", placeholder="e.g., Signals and Systems")
#     course_code = st.text_input("Course Code", placeholder="e.g., ECE316")
    
#     st.markdown("---")
#     st.markdown("### 📄 Cheatsheet Formatting")
    
#     # Formatting options
#     col1, col2 = st.columns(2)
#     with col1:
#         font_size = st.selectbox("Font Size", ["8pt", "9pt", "10pt", "11pt", "12pt"], index=1)
#         num_pages = st.number_input("Max Pages", min_value=1, max_value=10, value=2)
#     with col2:
#         font_family = st.selectbox("Font Family", ["Computer Modern", "Helvetica", "Times New Roman", "Arial"])
#         columns = st.selectbox("Columns", ["1", "2", "3"], index=1)
    
#     # Additional formatting
#     include_diagrams = st.checkbox("Include Diagrams", value=True)
#     include_examples = st.checkbox("Include Examples", value=True)
#     color_scheme = st.selectbox("Color Scheme", ["Monochrome", "Colorful", "Custom"])
    
#     st.markdown("---")
#     st.markdown("### 🧠 Processing Settings")
    
#     # Processing options
#     topic_threshold = st.slider("Topic Importance Threshold", 0.0, 1.0, 0.3, 0.05)
#     llm_model = st.selectbox("LLM Model", ["GPT-4", "Claude-3", "Gemini Pro", "Llama-3"])
    
#     st.markdown("---")
    
#     # Action buttons
#     if st.button("🔄 Reset All", type="secondary"):
#         st.rerun()
    
#     if st.button("🚀 Generate Cheatsheet", type="primary"):
#         st.session_state.generate_clicked = True

# Main content area
col1, col2 = st.columns([3, 2])

with col1:
    # st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">📤 Upload Course Materials</h2>', unsafe_allow_html=True)
    
    # File type definitions
    file_types = {
        "exam": {"name": "Past Exams", "desc": "Extract topics & question frequency", "color": "exam-tag"},
        "assignment": {"name": "Assignments", "desc": "Identify problem patterns & methods", "color": "assignment-tag"},
        "notes": {"name": "Lecture Notes", "desc": "Extract formulas, definitions, concepts", "color": "notes-tag"},
        "slides": {"name": "Slide Decks", "desc": "Extract key concepts & diagrams", "color": "slides-tag"},
        "instructions": {"name": "Instructions/Hints", "desc": "Professor emphasis & hints", "color": "instructions-tag"},
        "other": {"name": "Other Materials", "desc": "Additional resources", "color": "other-tag"}
    }
    
    # Create upload sections for each file type
    uploaded_files = {}
    
    for file_type, info in file_types.items():
        st.markdown(f"#### {info['name']}")
        st.markdown(f"<span class='file-type-tag {info['color']}'>{info['desc']}</span>", unsafe_allow_html=True)
        
        uploaded = st.file_uploader(
            f"Upload {info['name']} (PDF only)",
            type="pdf",
            key=f"{file_type}_uploader",
            accept_multiple_files=True,
            help=f"Upload one or more PDF files for {info['name'].lower()}"
        )
        
        if uploaded:
            uploaded_files[file_type] = uploaded
            os.makedirs(f"data/uploads/{course_code}/{file_type}", exist_ok=True)
            for file in uploaded:
                file_path = f"data/uploads/{course_code}/{file_type}/{file.name}"
                with open(file_path, "wb") as f:
                    f.write(file.getbuffer())
            st.success(f"✓ Uploaded {len(uploaded)} {info['name'].lower()} file(s)")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Additional instructions section
    # st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">✏️ Additional Instructions & Emphasis</h2>', unsafe_allow_html=True)
    
    professor_hints = st.text_area(
        "Professor Hints & Emphasis",
        placeholder="Enter any additional instructions, topics to emphasize, or specific requirements mentioned by the professor...",
        height=150
    )
    
    # Priority topics
    priority_topics = st.text_input(
        "Priority Topics (comma-separated)",
        placeholder="e.g., Laplace Transform, Bode Plots, Nyquist Stability"
    )
    
    # Exam date (for urgency calculation)
    exam_date = st.date_input("Exam Date", value=None)
    
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # File processing status dashboard
    # st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">📊 Processing Dashboard</h2>', unsafe_allow_html=True)
    
    # File summary
    total_files = sum(len(files) for files in uploaded_files.values() if files)
    st.metric("Total Files Uploaded", total_files)
    
    # File breakdown
    if uploaded_files:
        st.markdown("#### File Breakdown by Type")
        breakdown_data = []
        for file_type, files in uploaded_files.items():
            if files:
                breakdown_data.append({
                    "Type": file_types[file_type]["name"],
                    "Count": len(files),
                    "Processing": "Pending"
                })
        
        if breakdown_data:
            st.dataframe(pd.DataFrame(breakdown_data), width=True)
    else:
        st.info("No files uploaded yet. Use the upload sections on the left.")
    
    # Processing pipeline visualization
    st.markdown("#### Processing Pipeline")
    pipeline_steps = [
        "📥 File Upload",
        "📄 PDF Extraction",
        "🔪 Document Chunking",
        "🧠 LLM Analysis",
        "📊 Topic Scoring",
        "📝 LaTeX Generation",
        "📄 PDF Compilation"
    ]
    
    for i, step in enumerate(pipeline_steps):
        col_a, col_b = st.columns([1, 4])
        with col_a:
            st.write(f"**{i+1}.**")
        with col_b:
            st.write(step)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Preview section
    # st.markdown('<div class="section-box">', unsafe_allow_html=True)
    st.markdown('<h2 class="sub-header">👁️ Preview</h2>', unsafe_allow_html=True)
    
    # Topic importance preview
    if st.checkbox("Show Topic Importance Preview", value=False):
        st.markdown("#### Estimated Topic Importance")
        
        # Example data (would be replaced with actual AI output)
        example_topics = {
            "Laplace Transform": {"frequency": 9, "score": 0.95},
            "Bode Plot": {"frequency": 7, "score": 0.82},
            "Nyquist Stability": {"frequency": 4, "score": 0.68},
            "Transfer Function": {"frequency": 12, "score": 0.91},
            "Partial Fraction Decomposition": {"frequency": 5, "score": 0.73}
        }
        
        for topic, data in example_topics.items():
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.write(f"**{topic}**")
            with col2:
                st.write(f"📊 {data['frequency']}")
            with col3:
                st.progress(data["score"])
    
    # Quick actions
    st.markdown("#### Quick Actions")
    if st.button("🔍 Test PDF Processing", type="secondary"):
        st.info("Testing PDF extraction... (placeholder)")
    
    if st.button("📋 Generate Sample Output", type="secondary"):
        st.info("Generating sample cheatsheet... (placeholder)")
    
    st.markdown('</div>', unsafe_allow_html=True)

# Bottom section - Output configuration
st.markdown("---")
# st.markdown('<div class="section-box">', unsafe_allow_html=True)
st.markdown('<h2 class="sub-header">🎯 Output Configuration</h2>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### 📈 Content Weighting")
    exam_weight = st.slider("Exam Frequency Weight", 0.0, 1.0, 0.4, 0.05)
    hint_weight = st.slider("Professor Hints Weight", 0.0, 1.0, 0.3, 0.05)
    assignment_weight = st.slider("Assignment Patterns Weight", 0.0, 1.0, 0.3, 0.05)
    
    # Calculate total (should equal 1.0)
    total_weight = exam_weight + hint_weight + assignment_weight
    if total_weight != 1.0:
        st.warning(f"Weights sum to {total_weight:.2f}. Adjust to total 1.0 for balanced scoring.")

with col2:
    st.markdown("#### 🧩 Content Sections")
    include_definitions = st.checkbox("Definitions", value=True)
    include_formulas = st.checkbox("Formulas & Equations", value=True)
    include_diagrams = st.checkbox("Diagrams & Figures", value=True)
    include_examples = st.checkbox("Worked Examples", value=True)
    include_proofs = st.checkbox("Proof Sketches", value=False)
    include_mnemonics = st.checkbox("Mnemonics", value=False)

with col3:
    st.markdown("#### 📤 Export Options")
    output_format = st.selectbox("Output Format", ["LaTeX PDF", "Markdown", "HTML", "Word Document"])
    
    if output_format == "LaTeX PDF":
        latex_options = st.multiselect(
            "LaTeX Packages",
            ["amsmath", "amssymb", "geometry", "graphicx", "tabularx", "xcolor", "hyperref"],
            default=["amsmath", "geometry", "graphicx"]
        )
    
    include_source = st.checkbox("Include LaTeX Source", value=True)
    editable_pdf = st.checkbox("Make PDF Editable", value=True)

st.markdown('</div>', unsafe_allow_html=True)

# Final generate button
col1, col2, col3 = st.columns([1, 2, 1])
with col2:
    if st.button("🚀 **Generate Final Cheatsheet**", type="primary", width=True):
        if total_files == 0:
            st.error("Please upload at least one file to generate a cheatsheet.")
        else:
            # Show processing status
            with st.spinner("🤖 Processing your materials with AI..."):
                # Simulate processing steps
                progress_bar = st.progress(0)
                
                processing_steps = [
                    "Extracting text from PDFs",
                    "Chunking documents",
                    "Analyzing with LLM",
                    "Calculating topic importance",
                    "Generating LaTeX content",
                    "Compiling PDF"
                ]
                
                for i, step in enumerate(processing_steps):
                    st.write(f"**Step {i+1}/{len(processing_steps)}:** {step}")
                    progress_bar.progress((i + 1) / len(processing_steps))
                    # Simulate processing time
                    import time
                    time.sleep(1)
            
            # Success message
            st.success("✅ Cheatsheet generated successfully!")
            
            # Show download button (placeholder)
            st.download_button(
                label="📥 Download Cheatsheet (PDF)",
                data="This would be the actual PDF data",
                file_name=f"cheatsheet_{course_code}_{datetime.now().strftime('%Y%m%d')}.pdf",
                mime="application/pdf"
            )
            
            # Show preview of what was generated
            with st.expander("📋 View Generated Content Summary"):
                st.markdown("""
                **Topics Included (by importance):**
                1. Laplace Transform (Score: 0.95)
                2. Transfer Function (Score: 0.91)
                3. Bode Plot (Score: 0.82)
                4. Partial Fraction Decomposition (Score: 0.73)
                5. Nyquist Stability (Score: 0.68)
                
                **Content Statistics:**
                - 12 formulas
                - 8 definitions
                - 5 diagrams
                - 3 worked examples
                - 2 pages total
                """)

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #6B7280; font-size: 0.9rem;">
    <p>AI Cheatsheet Generator v1.0 • Powered by Streamlit & LLMs</p>
    <p>Each file type has its own processing pipeline for optimal topic extraction</p>
</div>
""", unsafe_allow_html=True)

# Session state initialization
if 'generate_clicked' not in st.session_state:
    st.session_state.generate_clicked = False