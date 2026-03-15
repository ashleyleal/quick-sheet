import streamlit as st
import json

# ============================================================================
# COLOR PALETTE DEFINITIONS
# ============================================================================

COLOR_PALETTES = {
    "Ocean Blue": {
        "primary": "#1E3A8A",
        "secondary": "#3B82F6",
        "accent": "#60A5FA",
        "background": "#F0F9FF",
        "surface": "#EFF6FF",
        "text": "#1F2937",
        "border": "#D1D5DB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "tag_exam": "#FEF3C7",
        "tag_exam_text": "#92400E",
        "tag_assignment": "#D1FAE5",
        "tag_assignment_text": "#065F46",
        "tag_notes": "#DBEAFE",
        "tag_notes_text": "#1E40AF",
        "tag_slides": "#E0E7FF",
        "tag_slides_text": "#3730A3",
        "tag_instructions": "#FCE7F3",
        "tag_instructions_text": "#9D174D"
    },
    "Forest Green": {
        "primary": "#065F46",
        "secondary": "#10B981",
        "accent": "#34D399",
        "background": "#F0FDF4",
        "surface": "#ECFDF5",
        "text": "#1F2937",
        "border": "#D1D5DB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "tag_exam": "#FEF3C7",
        "tag_exam_text": "#92400E",
        "tag_assignment": "#D1FAE5",
        "tag_assignment_text": "#065F46",
        "tag_notes": "#A7F3D0",
        "tag_notes_text": "#047857",
        "tag_slides": "#BBF7D0",
        "tag_slides_text": "#065F46",
        "tag_instructions": "#C7D2FE",
        "tag_instructions_text": "#3730A3"
    },
    "Sunset Purple": {
        "primary": "#7C3AED",
        "secondary": "#8B5CF6",
        "accent": "#A78BFA",
        "background": "#FAF5FF",
        "surface": "#F5F3FF",
        "text": "#1F2937",
        "border": "#D1D5DB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "tag_exam": "#FDE68A",
        "tag_exam_text": "#92400E",
        "tag_assignment": "#DDD6FE",
        "tag_assignment_text": "#5B21B6",
        "tag_notes": "#E9D5FF",
        "tag_notes_text": "#7C3AED",
        "tag_slides": "#EDE9FE",
        "tag_slides_text": "#5B21B6",
        "tag_instructions": "#FBCFE8",
        "tag_instructions_text": "#9D174D"
    },
    "Midnight Dark": {
        "primary": "#1F2937",
        "secondary": "#374151",
        "accent": "#6B7280",
        "background": "#111827",
        "surface": "#1F2937",
        "text": "#F9FAFB",
        "border": "#374151",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "tag_exam": "#FBBF24",
        "tag_exam_text": "#78350F",
        "tag_assignment": "#34D399",
        "tag_assignment_text": "#064E3B",
        "tag_notes": "#60A5FA",
        "tag_notes_text": "#1E40AF",
        "tag_slides": "#8B5CF6",
        "tag_slides_text": "#5B21B6",
        "tag_instructions": "#F87171",
        "tag_instructions_text": "#7F1D1D"
    },
    "Coral Red": {
        "primary": "#DC2626",
        "secondary": "#EF4444",
        "accent": "#F87171",
        "background": "#FEF2F2",
        "surface": "#FEE2E2",
        "text": "#1F2937",
        "border": "#D1D5DB",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#DC2626",
        "tag_exam": "#FDE68A",
        "tag_exam_text": "#92400E",
        "tag_assignment": "#FECACA",
        "tag_assignment_text": "#991B1B",
        "tag_notes": "#FED7D7",
        "tag_notes_text": "#DC2626",
        "tag_slides": "#FEE2E2",
        "tag_slides_text": "#B91C1C",
        "tag_instructions": "#FBCFE8",
        "tag_instructions_text": "#9D174D"
    }
}

# ============================================================================
# CUSTOM COLOR PICKER FUNCTION
# ============================================================================

def custom_color_picker():
    """UI for creating a custom color palette"""
    st.markdown("### 🎨 Customize Your Palette")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        primary = st.color_picker("Primary Color", "#1E3A8A")
        background = st.color_picker("Background", "#F0F9FF")
        tag_exam_bg = st.color_picker("Exam Tag BG", "#FEF3C7")
        
    with col2:
        secondary = st.color_picker("Secondary Color", "#3B82F6")
        surface = st.color_picker("Surface", "#EFF6FF")
        tag_assignment_bg = st.color_picker("Assignment Tag BG", "#D1FAE5")
        
    with col3:
        accent = st.color_picker("Accent Color", "#60A5FA")
        border = st.color_picker("Border", "#D1D5DB")
        tag_notes_bg = st.color_picker("Notes Tag BG", "#DBEAFE")
    
    col4, col5, col6 = st.columns(3)
    with col4:
        text = st.color_picker("Text Color", "#1F2937")
        tag_exam_text = st.color_picker("Exam Tag Text", "#92400E")
    with col5:
        success = st.color_picker("Success", "#10B981")
        tag_assignment_text = st.color_picker("Assignment Tag Text", "#065F46")
    with col6:
        warning = st.color_picker("Warning", "#F59E0B")
        tag_notes_text = st.color_picker("Notes Tag Text", "#1E40AF")
    
    return {
        "primary": primary,
        "secondary": secondary,
        "accent": accent,
        "background": background,
        "surface": surface,
        "text": text,
        "border": border,
        "success": success,
        "warning": warning,
        "error": "#EF4444",
        "tag_exam": tag_exam_bg,
        "tag_exam_text": tag_exam_text,
        "tag_assignment": tag_assignment_bg,
        "tag_assignment_text": tag_assignment_text,
        "tag_notes": tag_notes_bg,
        "tag_notes_text": tag_notes_text,
        "tag_slides": "#E0E7FF",
        "tag_slides_text": "#3730A3",
        "tag_instructions": "#FCE7F3",
        "tag_instructions_text": "#9D174D"
    }

# ============================================================================
# CSS GENERATOR FUNCTION
# ============================================================================

def generate_css(palette):
    """Generate CSS with the selected color palette"""
    
    # Helper function to adjust color brightness
    def adjust_color(color, factor):
        """Simple function to lighten/darken a color"""
        # This is a placeholder - in production, you'd want a proper color adjustment
        return color
    
    css = f"""
    <style>
    :root {{
        --primary-color: {palette['primary']};
        --secondary-color: {palette['secondary']};
        --accent-color: {palette['accent']};
        --background-color: {palette['background']};
        --surface-color: {palette['surface']};
        --text-color: {palette['text']};
        --border-color: {palette['border']};
        --success-color: {palette['success']};
        --warning-color: {palette['warning']};
        --error-color: {palette['error']};
        
        --exam-tag-bg: {palette['tag_exam']};
        --exam-tag-color: {palette['tag_exam_text']};
        --assignment-tag-bg: {palette['tag_assignment']};
        --assignment-tag-color: {palette['tag_assignment_text']};
        --notes-tag-bg: {palette['tag_notes']};
        --notes-tag-color: {palette['tag_notes_text']};
        --slides-tag-bg: {palette['tag_slides']};
        --slides-tag-color: {palette['tag_slides_text']};
        --instructions-tag-bg: {palette['tag_instructions']};
        --instructions-tag-color: {palette['tag_instructions_text']};
    }}
    
    /* Main Styles */
    .main {{
        background-color: var(--background-color);
        color: var(--text-color);
    }}
    
    /* Headers */
    .main-header {{
        font-size: 2.5rem;
        color: var(--primary-color);
        text-align: center;
        margin-bottom: 1rem;
    }}
    
    .sub-header {{
        font-size: 1.5rem;
        color: var(--secondary-color);
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid var(--border-color);
        padding-bottom: 0.5rem;
    }}
    
    /* Section Boxes */
    .section-box {{
        background-color: var(--surface-color);
        padding: 1.5rem;
        border-radius: 10px;
        border: 1px solid var(--border-color);
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    }}
    
    /* File Type Tags */
    .file-type-tag {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    
    .exam-tag {{ background-color: var(--exam-tag-bg); color: var(--exam-tag-color); }}
    .assignment-tag {{ background-color: var(--assignment-tag-bg); color: var(--assignment-tag-color); }}
    .notes-tag {{ background-color: var(--notes-tag-bg); color: var(--notes-tag-color); }}
    .slides-tag {{ background-color: var(--slides-tag-bg); color: var(--slides-tag-color); }}
    .instructions-tag {{ background-color: var(--instructions-tag-bg); color: var(--instructions-tag-color); }}
    .other-tag {{ background-color: var(--border-color); color: var(--text-color); }}
    
    /* Buttons */
    .stButton > button {{
        background-color: var(--primary-color);
        color: white;
        border: none;
        border-radius: 5px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.2s ease;
    }}
    
    .stButton > button:hover {{
        background-color: var(--secondary-color);
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
    }}
    
    .stButton > button:active {{
        transform: translateY(0);
    }}
    
    /* Progress Bars */
    .stProgress > div > div > div > div {{
        background-color: var(--accent-color);
    }}
    
    /* Sidebar */
    .css-1d391kg {{
        background-color: var(--surface-color);
    }}
    
    /* Metric Cards */
    .metric {{
        background-color: var(--surface-color);
        padding: 1rem;
        border-radius: 8px;
        border: 1px solid var(--border-color);
    }}
    
    /* Success/Warning/Error Messages */
    .stAlert.success {{
        background-color: color-mix(in srgb, var(--success-color) 20%, transparent);
        border-left: 4px solid var(--success-color);
    }}
    
    .stAlert.warning {{
        background-color: color-mix(in srgb, var(--warning-color) 20%, transparent);
        border-left: 4px solid var(--warning-color);
    }}
    
    .stAlert.error {{
        background-color: color-mix(in srgb, var(--error-color) 20%, transparent);
        border-left: 4px solid var(--error-color);
    }}
    
    /* Custom Scrollbar */
    ::-webkit-scrollbar {{
        width: 8px;
    }}
    
    ::-webkit-scrollbar-track {{
        background: var(--background-color);
    }}
    
    ::-webkit-scrollbar-thumb {{
        background: var(--accent-color);
        border-radius: 4px;
    }}
    
    ::-webkit-scrollbar-thumb:hover {{
        background: var(--secondary-color);
    }}
    
    /* Tabbed Sections */
    .stTabs [data-baseweb="tab-list"] {{
        gap: 2px;
        background-color: var(--surface-color);
    }}
    
    .stTabs [data-baseweb="tab"] {{
        background-color: var(--surface-color);
        color: var(--text-color);
        border-radius: 4px 4px 0 0;
        padding: 10px 16px;
    }}
    
    .stTabs [aria-selected="true"] {{
        background-color: var(--primary-color);
        color: white;
    }}
    
    /* Input Fields */
    .stTextInput > div > div {{
        background-color: var(--surface-color);
        border: 1px solid var(--border-color);
    }}
    
    .stTextInput input {{
        color: var(--text-color);
    }}
    
    /* Select/Dropdown */
    .stSelectbox > div > div {{
        background-color: var(--surface-color);
        border: 1px solid var(--border-color);
    }}
    
    /* File Uploader */
    .stFileUploader > div {{
        border: 2px dashed var(--border-color);
        background-color: var(--surface-color);
    }}
    
    /* Checkbox & Radio */
    .stCheckbox label, .stRadio label {{
        color: var(--text-color);
    }}
    
    /* Slider */
    .stSlider [data-baseweb="slider"] {{
        color: var(--primary-color);
    }}
    
    /* Dataframe */
    .dataframe {{
        border: 1px solid var(--border-color);
    }}
    
    .dataframe th {{
        background-color: var(--primary-color);
        color: white;
    }}
    
    .dataframe tr:nth-child(even) {{
        background-color: var(--surface-color);
    }}
    
    .dataframe tr:hover {{
        background-color: color-mix(in srgb, var(--accent-color) 20%, transparent);
    }}
    </style>
    """
    
    return css

# ============================================================================
# PALETTE SELECTOR UI
# ============================================================================

def palette_selector_ui():
    """UI for selecting or creating a color palette"""
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎨 Theme Customization")
    
    # Theme selection
    theme_options = list(COLOR_PALETTES.keys()) + ["Custom Palette"]
    selected_theme = st.sidebar.selectbox(
        "Select Theme",
        theme_options,
        index=0,
        help="Choose from predefined themes or create your own"
    )
    
    palette = COLOR_PALETTES.get("Ocean Blue")  # Default
    
    if selected_theme == "Custom Palette":
        st.sidebar.markdown("---")
        with st.sidebar.expander("🎨 Custom Colors", expanded=True):
            custom_palette = custom_color_picker()
            
            # Save custom palette button
            if st.button("💾 Save Custom Palette"):
                palette_name = st.text_input("Name your palette", "My Custom Theme")
                if palette_name:
                    COLOR_PALETTES[palette_name] = custom_palette
                    st.success(f"Saved as '{palette_name}'")
            
            palette = custom_palette
    else:
        palette = COLOR_PALETTES[selected_theme]
    
    # Show palette preview
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 🎨 Palette Preview")
    
    cols = st.sidebar.columns(3)
    cols[0].color_picker("Primary", palette['primary'], disabled=True)
    cols[1].color_picker("Secondary", palette['secondary'], disabled=True)
    cols[2].color_picker("Accent", palette['accent'], disabled=True)
    
    # Export/Import palette
    st.sidebar.markdown("---")
    with st.sidebar.expander("📁 Palette Management"):
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📤 Export Palette"):
                palette_json = json.dumps(palette, indent=2)
                st.download_button(
                    label="Download JSON",
                    data=palette_json,
                    file_name="custom_palette.json",
                    mime="application/json"
                )
        
        with col2:
            uploaded_file = st.file_uploader("Import JSON", type=['json'])
            if uploaded_file:
                try:
                    imported_palette = json.load(uploaded_file)
                    # Validate imported palette has required keys
                    required_keys = ['primary', 'secondary', 'accent', 'background']
                    if all(key in imported_palette for key in required_keys):
                        st.success("Palette imported successfully!")
                        palette.update(imported_palette)
                    else:
                        st.error("Invalid palette format")
                except:
                    st.error("Error reading palette file")
    
    return palette

# ============================================================================
# EXAMPLE USAGE IN YOUR STREAMLIT APP
# ============================================================================

# def main_app():
#     """Example of how to integrate the color palette system"""
    
#     # Get selected palette
#     selected_palette = palette_selector_ui()
    
#     # Generate and inject CSS
#     css = generate_css(selected_palette)
#     st.markdown(css, unsafe_allow_html=True)
    
#     # Your existing app code would go here
#     st.markdown('<h1 class="main-header">📚 AI Cheatsheet Generator</h1>', unsafe_allow_html=True)
    
#     # Example section with tags
#     st.markdown('<div class="section-box">', unsafe_allow_html=True)
#     st.markdown('<h2 class="sub-header">📤 Upload Course Materials</h2>', unsafe_allow_html=True)
    
#     # Example tags
#     st.markdown("#### File Types")
#     st.markdown('<span class="file-type-tag exam-tag">Past Exams</span>', unsafe_allow_html=True)
#     st.markdown('<span class="file-type-tag assignment-tag">Assignments</span>', unsafe_allow_html=True)
#     st.markdown('<span class="file-type-tag notes-tag">Lecture Notes</span>', unsafe_allow_html=True)
#     st.markdown('<span class="file-type-tag slides-tag">Slide Decks</span>', unsafe_allow_html=True)
#     st.markdown('<span class="file-type-tag instructions-tag">Instructions</span>', unsafe_allow_html=True)
    
#     st.markdown('</div>', unsafe_allow_html=True)
    
#     # Example metrics
#     col1, col2, col3 = st.columns(3)
#     with col1:
#         st.metric("Files Processed", "12", "+3")
#     with col2:
#         st.metric("Topics Identified", "45", "+8")
#     with col3:
#         st.metric("Processing Time", "2.3s", "-0.5s")
    
#     # Example progress bar
#     st.progress(0.75)
    
#     # Example buttons
#     if st.button("🚀 Generate Cheatsheet", type="primary"):
#         st.success("Cheatsheet generated successfully!")
    
#     if st.button("🔄 Reset"):
#         st.warning("This will reset all settings")

# ============================================================================
# PALETTE UTILITY FUNCTIONS
# ============================================================================

def get_color_variants(base_color):
    """Generate color variants from a base color"""
    # This is a simplified version - in production, you might want
    # to use a proper color manipulation library like `colorsys`
    
    return {
        'light': base_color + "20",  # 20% opacity version
        'dark': base_color,
        'darker': base_color,
    }

def validate_palette(palette):
    """Validate that a palette has all required keys"""
    required_keys = [
        'primary', 'secondary', 'accent', 'background', 'surface',
        'text', 'border', 'success', 'warning', 'error'
    ]
    
    missing_keys = [key for key in required_keys if key not in palette]
    if missing_keys:
        raise ValueError(f"Palette missing required keys: {missing_keys}")
    
    return True

# ============================================================================
# RUN THE APP
# ============================================================================

# if __name__ == "__main__":
#     # Page config
#     st.set_page_config(
#         page_title="AI Cheatsheet Generator",
#         page_icon="🎨",
#         layout="wide",
#         initial_sidebar_state="expanded"
#     )
    
#     # Run the app with color palette system
#     main_app()