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
    }
}

# ============================================================================
# SIMPLIFIED PALETTE SELECTOR (Auto-detect theme)
# ============================================================================

def palette_selector_ui():
    """Auto-detect system theme and return appropriate palette"""
    
    # Simple: just return Ocean Blue (light mode) by default
    # The actual theme switching will be handled by CSS media queries
    return COLOR_PALETTES["Ocean Blue"]

# ============================================================================
# CSS GENERATOR FUNCTION WITH AUTO THEME SWITCHING
# ============================================================================

def generate_css(palette):
    """Generate CSS that auto-switches between light/dark mode"""
    
    # Get both palettes
    light_palette = COLOR_PALETTES["Ocean Blue"]
    dark_palette = COLOR_PALETTES["Midnight Dark"]
    
    css = f"""
    <style>
    /* Default light mode (Ocean Blue) */
    :root {{
        --primary-color: {light_palette['primary']};
        --secondary-color: {light_palette['secondary']};
        --accent-color: {light_palette['accent']};
        --background-color: {light_palette['background']};
        --surface-color: {light_palette['surface']};
        --text-color: {light_palette['text']};
        --border-color: {light_palette['border']};
        --success-color: {light_palette['success']};
        --warning-color: {light_palette['warning']};
        --error-color: {light_palette['error']};
        
        --exam-tag-bg: {light_palette['tag_exam']};
        --exam-tag-color: {light_palette['tag_exam_text']};
        --assignment-tag-bg: {light_palette['tag_assignment']};
        --assignment-tag-color: {light_palette['tag_assignment_text']};
        --notes-tag-bg: {light_palette['tag_notes']};
        --notes-tag-color: {light_palette['tag_notes_text']};
        --slides-tag-bg: {light_palette['tag_slides']};
        --slides-tag-color: {light_palette['tag_slides_text']};
        --instructions-tag-bg: {light_palette['tag_instructions']};
        --instructions-tag-color: {light_palette['tag_instructions_text']};
    }}
    
    /* Dark mode override (Midnight Dark) */
    @media (prefers-color-scheme: dark) {{
        :root {{
            --primary-color: {dark_palette['primary']};
            --secondary-color: {dark_palette['secondary']};
            --accent-color: {dark_palette['accent']};
            --background-color: {dark_palette['background']};
            --surface-color: {dark_palette['surface']};
            --text-color: {dark_palette['text']};
            --border-color: {dark_palette['border']};
            --success-color: {dark_palette['success']};
            --warning-color: {dark_palette['warning']};
            --error-color: {dark_palette['error']};
            
            --exam-tag-bg: {dark_palette['tag_exam']};
            --exam-tag-color: {dark_palette['tag_exam_text']};
            --assignment-tag-bg: {dark_palette['tag_assignment']};
            --assignment-tag-color: {dark_palette['tag_assignment_text']};
            --notes-tag-bg: {dark_palette['tag_notes']};
            --notes-tag-color: {dark_palette['tag_notes_text']};
            --slides-tag-bg: {dark_palette['tag_slides']};
            --slides-tag-color: {dark_palette['tag_slides_text']};
            --instructions-tag-bg: {dark_palette['tag_instructions']};
            --instructions-tag-color: {dark_palette['tag_instructions_text']};
        }}
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
    
    /* File Type Tags - FORCE with !important */
    .file-type-tag {{
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 15px;
        font-size: 0.85rem;
        font-weight: 600;
        margin-right: 0.5rem;
        margin-bottom: 0.5rem;
    }}
    
    .exam-tag {{ 
        background-color: var(--exam-tag-bg) !important; 
        color: var(--exam-tag-color) !important; 
    }}
    
    .assignment-tag {{ 
        background-color: var(--assignment-tag-bg) !important; 
        color: var(--assignment-tag-color) !important; 
    }}
    
    .notes-tag {{ 
        background-color: var(--notes-tag-bg) !important; 
        color: var(--notes-tag-color) !important; 
    }}
    
    .slides-tag {{ 
        background-color: var(--slides-tag-bg) !important; 
        color: var(--slides-tag-color) !important; 
    }}
    
    .instructions-tag {{ 
        background-color: var(--instructions-tag-bg) !important; 
        color: var(--instructions-tag-color) !important; 
    }}
    
    .other-tag {{ 
        background-color: var(--border-color) !important; 
        color: var(--text-color) !important; 
    }}
    
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
# MINIMAL UTILITY FUNCTIONS (kept for compatibility)
# ============================================================================

def get_color_variants(base_color):
    """Generate color variants from a base color"""
    return {
        'light': base_color + "20",
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