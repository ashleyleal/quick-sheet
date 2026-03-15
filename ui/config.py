# ============================================================================
# CONFIGURATION MANAGER
# ============================================================================

import json
import os
from pathlib import Path
import streamlit as st
from datetime import datetime



class ConfigManager:
    """Manages saving and loading configuration files"""
    
    def __init__(self, config_dir: str = "./data/configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_config_filename(self, course_code: str, version: str = None) -> str:
        """Generate a standardized config filename"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if version:
            return f"{course_code}_config_v{version}_{timestamp}.json"
        return f"{course_code}_config_{timestamp}.json"
    
    def save_config(self, course_code: str, config_data: dict) -> str:
        """Save configuration to a JSON file"""
        
        # Add metadata
        config_with_meta = {
            "metadata": {
                "created": datetime.now().isoformat(),
                "version": "1.0",
                "course_code": course_code,
                "course_name": config_data.get("course_name", ""),
                "config_type": "cheatsheet_settings"
            },
            "settings": config_data
        }
        
        # Generate filename
        filename = self.generate_config_filename(course_code)
        filepath = self.config_dir / filename
        
        # Save to file
        with open(filepath, 'w') as f:
            json.dump(config_with_meta, f, indent=2, default=str)
        
        return str(filepath)
    
    def load_config(self, filepath: str) -> dict:
        """Load configuration from a JSON file"""
        with open(filepath, 'r') as f:
            config = json.load(f)
        return config
    
    def list_configs(self, course_code: str = None) -> list:
        """List all available configs, optionally filtered by course"""
        configs = []
        
        for filepath in self.config_dir.glob("*.json"):
            try:
                config = self.load_config(filepath)
                metadata = config.get("metadata", {})
                
                if course_code and metadata.get("course_code") != course_code:
                    continue
                
                configs.append({
                    "filepath": str(filepath),
                    "metadata": metadata,
                    "settings": config.get("settings", {}),
                    "filename": filepath.name
                })
            except:
                continue
        
        # Sort by creation date (newest first)
        configs.sort(key=lambda x: x["metadata"].get("created", ""), reverse=True)
        return configs
    
    def delete_config(self, filepath: str) -> bool:
        """Delete a configuration file"""
        path = Path(filepath)
        if path.exists():
            path.unlink()
            return True
        return False
    
    def get_latest_config(self, course_code: str) -> dict:
        """Get the latest config for a specific course"""
        configs = self.list_configs(course_code)
        return configs[0] if configs else None

# ============================================================================
# STREAMLET SIDEBAR WITH CONFIG MANAGEMENT
# ============================================================================

def settings_sidebar(config_manager: ConfigManager):
    """Sidebar with settings and config management"""
    
    with st.sidebar:
        st.markdown("### 🛠️ Project Settings")
        
        # Course info
        course_name = st.text_input("Course Name", placeholder="e.g., Signals and Systems")
        course_code = st.text_input("Course Code", placeholder="e.g., ECE316")
        
        st.markdown("---")
        st.markdown("### 📄 Cheatsheet Formatting")
        
        # Formatting options
        col1, col2 = st.columns(2)
        with col1:
            font_size = st.selectbox("Font Size", ["8pt", "9pt", "10pt", "11pt", "12pt"], index=1)
            num_pages = st.number_input("Max Pages", min_value=1, max_value=10, value=2)
        with col2:
            font_family = st.selectbox("Font Family", ["Computer Modern", "Helvetica", "Times New Roman", "Arial"])
            columns = st.selectbox("Columns", ["1", "2", "3"], index=1)
        
        # Additional formatting
        include_diagrams = st.checkbox("Include Diagrams", value=True)
        include_examples = st.checkbox("Include Examples", value=True)
        color_scheme = st.selectbox("Color Scheme", ["Monochrome", "Colorful", "Custom"])
        
        st.markdown("---")
        st.markdown("### 🧠 Processing Settings")
        
        # Processing options
        topic_threshold = st.slider("Topic Importance Threshold", 0.0, 1.0, 0.3, 0.05)
        llm_model = st.selectbox("LLM Model", ["GPT-4", "Claude-3", "Gemini Pro", "Llama-3"])
        
        st.markdown("---")
        
        # ============================================================================
        # CONFIGURATION MANAGEMENT SECTION
        # ============================================================================
        st.markdown("### 💾 Configuration Management")
        
        # Create config dictionary
        config_data = {
            "course_name": course_name,
            "course_code": course_code,
            "formatting": {
                "font_size": font_size,
                "num_pages": num_pages,
                "font_family": font_family,
                "columns": columns,
                "include_diagrams": include_diagrams,
                "include_examples": include_examples,
                "color_scheme": color_scheme
            },
            "processing": {
                "topic_threshold": topic_threshold,
                "llm_model": llm_model
            }
        }
        
        # Config management buttons
        col_save, col_load = st.columns(2)
        
        with col_save:
            if st.button("💾 Save Config", type="secondary"):
                if course_code:
                    config_path = config_manager.save_config(course_code, config_data)
                    st.success(f"✅ Config saved to:\n`{config_path}`")
                    st.session_state.last_saved_config = config_path
                else:
                    st.error("Please enter a course code first")
        
        with col_load:
            if st.button("📂 Load Config", type="secondary"):
                st.session_state.show_config_selector = True
        
        # Config selector modal
        if st.session_state.get('show_config_selector', False):
            with st.sidebar.expander("📂 Select Config File", expanded=True):
                if course_code:
                    configs = config_manager.list_configs(course_code)
                    
                    if configs:
                        config_options = {cfg["filename"]: cfg for cfg in configs}
                        selected_file = st.selectbox(
                            "Available Configs",
                            list(config_options.keys()),
                            key="config_selector"
                        )
                        
                        if selected_file:
                            selected_config = config_options[selected_file]
                            
                            col_preview, col_action = st.columns([3, 1])
                            with col_preview:
                                st.caption(f"Created: {selected_config['metadata']['created'][:19]}")
                            
                            with col_action:
                                if st.button("📋 Load", key="load_selected_config"):
                                    # Populate the sidebar with loaded values
                                    st.session_state.loaded_config = selected_config
                                    st.success("Config loaded! Apply below")
                            
                            # Show preview
                            with st.expander("Preview Config"):
                                st.json(selected_config["settings"], expanded=False)
                            
                            # Apply loaded config button
                            if st.session_state.get('loaded_config'):
                                if st.button("✅ Apply Loaded Config"):
                                    # This would need to update the widget values
                                    # Since Streamlit doesn't support direct widget value setting,
                                    # we'd need to use session state and rerun
                                    st.info("To apply: Refresh page and config will auto-load")
                                    # For now, show the values
                                    st.write("Loaded values would appear here")
                    else:
                        st.info("No configs found for this course")
                
                if st.button("❌ Close"):
                    st.session_state.show_config_selector = False
                    st.rerun()
        
        st.markdown("---")
        
        # Action buttons
        if st.button("🔄 Reset All", type="secondary"):
            st.rerun()
        
        if st.button("🚀 Generate Cheatsheet", type="primary"):
            st.session_state.generate_clicked = True
        
        # Quick config info
        if course_code:
                st.caption(f"Configs will save to: `{config_manager.config_dir}`")
        
        return config_data
