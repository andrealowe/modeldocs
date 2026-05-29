import os
import subprocess
import sys
import warnings
from PIL import Image
import streamlit as st
from transformers import pipeline
import csv
from datetime import datetime
import json

# Compatibility fix for streamlit-drawable-canvas
import base64
from io import BytesIO

def image_to_url(pil_image, width=None, clamp=False, channels='RGB', output_format='auto', image_id=None):
    """Compatibility function for streamlit-drawable-canvas"""
    buffered = BytesIO()
    pil_image.save(buffered, format="PNG")
    img_data = base64.b64encode(buffered.getvalue()).decode()
    return f"data:image/png;base64,{img_data}"

# Monkey patch to fix compatibility
if not hasattr(st.elements.image, 'image_to_url'):
    st.elements.image.image_to_url = image_to_url

from streamlit_drawable_canvas import st_canvas

# Suppress warnings for cleaner Streamlit display
warnings.filterwarnings('ignore')

# ─── Page Configuration ─────────────────────────────────────────────────────
st.set_page_config(
    page_title="Seabed Object Classification",
    page_icon="🌊",
    layout="wide"
)

# ─── Military/Tactical Styling ─────────────────────────────────────────────────────────
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Rajdhani:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

    /* Global Dark Theme */
    .main {
        background-color: #0a0e14;
        padding: 0 2rem;
        color: #e0e6ed;
    }

    /* Remove default Streamlit padding */
    .block-container {
        padding-top: 0rem;
        padding-bottom: 0rem;
        margin-top: 0rem;
    }
    
    /* Remove header padding and margin */
    header[data-testid="stHeader"] {
        height: 0rem;
        background: transparent;
    }
    
    /* Remove top toolbar space */
    .stAppHeader {
        height: 0rem;
        margin: 0;
        padding: 0;
    }
    
    /* Remove any top margin/padding from main content area */
    section.main > div {
        padding-top: 0rem;
    }

    /* Override Streamlit's default backgrounds */
    .stApp {
        background-color: #0a0e14;
    }

    section[data-testid="stSidebar"] {
        background-color: #111720;
        border-right: 1px solid #1a2332;
    }

    section[data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }

    /* Typography - Military Style */
    h1, h2, h3, h4, h5, h6 {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 700;
        letter-spacing: 1px;
        text-transform: uppercase;
        color: #00ff9f !important;
    }

    h1 {
        font-size: 2.5rem;
        border-bottom: 2px solid #00ff9f;
        padding-bottom: 0.5rem;
        margin-bottom: 2rem;
        text-shadow: 0 0 10px rgba(0, 255, 159, 0.3);
    }

    h2 {
        font-size: 1.8rem;
        color: #58a6ff !important;
        margin-top: 1.5rem;
    }

    h3 {
        font-size: 1.4rem;
        color: #79c0ff !important;
    }

    p, span, div, label {
        font-family: 'Rajdhani', sans-serif;
        color: #c9d1d9;
        font-weight: 400;
    }

    /* Monospace for technical data */
    .mono {
        font-family: 'Share Tech Mono', monospace;
        color: #00ff9f;
        letter-spacing: 0.5px;
    }

    /* Tabs - Tactical Style */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0.5rem;
        background-color: #111720;
        padding: 0.5rem;
        border-radius: 0;
        border: 1px solid #1a2332;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 0.75rem 2rem;
        font-size: 1rem;
        font-weight: 600;
        font-family: 'Rajdhani', sans-serif;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        border-radius: 0;
        color: #8b949e !important;
        background-color: #0d1117;
        border: 1px solid #1a2332;
        border-bottom: 2px solid transparent;
    }

    .stTabs [data-baseweb="tab"]:hover {
        background-color: #161b22;
        color: #58a6ff !important;
        border-bottom: 2px solid #58a6ff;
    }

    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background-color: #0d1117;
        color: #00ff9f !important;
        border: 1px solid #00ff9f;
        border-bottom: 2px solid #00ff9f;
        box-shadow: 0 0 15px rgba(0, 255, 159, 0.2);
    }

    /* Prediction Box - Tactical HUD Style */
    .prediction-box {
        background: linear-gradient(135deg, #0d1117 0%, #161b22 100%);
        border: 2px solid #00ff9f;
        padding: 1.5rem;
        border-radius: 2px;
        color: #e0e6ed;
        margin: 1rem 0;
        box-shadow: 0 0 20px rgba(0, 255, 159, 0.15),
                    inset 0 0 20px rgba(0, 255, 159, 0.05);
        position: relative;
    }

    .prediction-box::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 2px;
        background: linear-gradient(90deg, transparent, #00ff9f, transparent);
    }

    .prediction-box h2, .prediction-box h3 {
        color: #00ff9f !important;
        margin: 0;
        text-shadow: 0 0 10px rgba(0, 255, 159, 0.5);
    }

    /* Feedback Section - Military Alert Style */
    .feedback-section {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        padding: 1.5rem;
        border-radius: 2px;
        margin-top: 1rem;
    }

    /* Buttons - Tactical Style */
    .stButton>button {
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
        letter-spacing: 1px;
        text-transform: uppercase;
        border-radius: 2px;
        border: 1px solid #30363d;
        background-color: #161b22;
        color: #c9d1d9;
        transition: all 0.2s ease;
        padding: 0.6rem 1.5rem;
    }

    .stButton>button:hover {
        background-color: #21262d;
        border-color: #58a6ff;
        color: #58a6ff;
        box-shadow: 0 0 15px rgba(88, 166, 255, 0.3);
        transform: translateY(-1px);
    }

    .stButton>button[kind="primary"] {
        background-color: #238636;
        border-color: #2ea043;
        color: #ffffff;
    }

    .stButton>button[kind="primary"]:hover {
        background-color: #2ea043;
        border-color: #3fb950;
        box-shadow: 0 0 15px rgba(46, 160, 67, 0.4);
    }

    /* Info/Warning boxes */
    .stAlert {
        background-color: #161b22;
        border: 1px solid #30363d;
        border-left: 4px solid #58a6ff;
        color: #c9d1d9;
        font-family: 'Rajdhani', sans-serif;
    }

    /* Selectbox and inputs */
    .stSelectbox, .stTextInput {
        font-family: 'Rajdhani', sans-serif;
    }

    .stSelectbox > div > div {
        background-color: #161b22;
        border: 1px solid #30363d;
        color: #c9d1d9;
    }

    /* Expander */
    .streamlit-expanderHeader {
        background-color: #161b22;
        border: 1px solid #30363d;
        color: #c9d1d9;
        font-family: 'Rajdhani', sans-serif;
        font-weight: 600;
    }

    /* Status indicators */
    .status-indicator {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 8px;
        animation: pulse 2s infinite;
    }

    .status-active {
        background-color: #00ff9f;
        box-shadow: 0 0 10px rgba(0, 255, 159, 0.7);
    }

    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }

    /* Grid lines effect */
    .grid-overlay {
        background-image:
            linear-gradient(rgba(0, 255, 159, 0.05) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0, 255, 159, 0.05) 1px, transparent 1px);
        background-size: 20px 20px;
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        pointer-events: none;
        z-index: -1;
    }
    </style>
    <div class="grid-overlay"></div>
""", unsafe_allow_html=True)

st.markdown('<h1><span class="status-indicator status-active"></span>SONAR TARGET CLASSIFICATION SYSTEM</h1>', unsafe_allow_html=True)

# ─── Load Classifier ─────────────────────────────────────────────────────────
@st.cache_resource
def load_classifier():
    """Load model - handles git-based and file-based projects"""
    working_dir = os.environ.get('DOMINO_WORKING_DIR', '.')
    is_git_based_project = (working_dir == '/mnt/code')

    # Determine primary model path based on project type
    if is_git_based_project:
        model_path = "/mnt/artifacts/models/vit_classification_model/model"
    else:
        model_path = f"{working_dir}/models/vit_classification_model/model"

    # Check if model path exists
    if not os.path.exists(model_path):
        # Fallback paths
        alternative_paths = [
            "/mnt/artifacts/models/vit_classification_model/model",  # Git-based project
            "/mnt/models/vit_classification_model/model",  # File-based project
            "./models/vit_classification_model/model",
            "./vit_classification_model/model",  # Legacy path
            "./model",
            "models/vit_classification_model/model"
        ]

        model_path = None
        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                model_path = alt_path
                break

        if model_path is None:
            st.error(f"Model not found. Please ensure the model is available at one of these paths: {alternative_paths}")
            st.stop()

    return pipeline(
        "image-classification",
        model=model_path,
        device=0 if int(os.getenv("DOMINO_TASK_GPU_COUNT", "0")) > 0 else -1
    )

try:
    classifier = load_classifier()
except Exception as e:
    st.error(f"Failed to load classifier: {str(e)}")
    st.stop()

# ─── Helper Functions ─────────────────────────────────────────────────────────
# DataConfig setup - matches Model_Dev.ipynb logic
def get_data_paths():
    """Get data paths using same logic as DataConfig class in Model_Dev notebook"""
    from pathlib import Path
    
    # Get environment variables with defaults
    domino_datasets_dir = os.environ.get('DOMINO_DATASETS_DIR', '/mnt/data')
    domino_project_name = os.environ.get('DOMINO_PROJECT_NAME', 'Seabed-Object-Detection')
    
    # Use same logic as DataConfig
    if domino_datasets_dir == '/domino/datasets':
        # Domino 5.x path structure
        base_data_path = Path(domino_datasets_dir) / 'local' / domino_project_name
    else:
        # Domino 6.x or local path structure  
        base_data_path = Path(domino_datasets_dir) / domino_project_name
    
    test_images_path = base_data_path / 'test_set'
    
    # Fallback paths if main path doesn't exist
    if not test_images_path.exists():
        alternative_paths = [
            Path('./test_set'),
            Path('./data/test_set'), 
            Path('./datasets/test_set'),
            Path(f'./{domino_project_name}/test_set')
        ]
        
        for alt_path in alternative_paths:
            if alt_path.exists():
                return str(alt_path)
        
        # Return original path even if it doesn't exist for error handling
        return str(test_images_path)
    
    return str(test_images_path)

# Get test images root using DataConfig logic
test_images_root = get_data_paths()

@st.cache_data
def get_categories(path):
    """Return list of category subdirectories."""
    try:
        return [d for d in os.listdir(path) if os.path.isdir(os.path.join(path, d))]
    except FileNotFoundError:
        return []

@st.cache_data
def get_image_list(path):
    """Return list of image filenames in given directory."""
    exts = (".png", ".jpg", ".jpeg")
    try:
        return [f for f in os.listdir(path) if f.lower().endswith(exts)]
    except FileNotFoundError:
        return []

def save_feedback(feedback_data, feedback_type="classification"):
    """Save user feedback to CSV file."""
    from pathlib import Path
    
    # Use same DataConfig logic as main data paths - put user-feedback WITHIN the project
    domino_datasets_dir = os.environ.get('DOMINO_DATASETS_DIR', '/mnt/data')
    domino_project_name = os.environ.get('DOMINO_PROJECT_NAME', 'Seabed-Object-Detection')
    
    # Create feedback directory within the project dataset directory
    if domino_datasets_dir == '/domino/datasets':
        # Domino 5.x: /domino/datasets/local/Seabed-Object-Detection/user-feedback
        base_data_path = Path(domino_datasets_dir) / 'local' / domino_project_name
    else:
        # Domino 6.x: /DOMINO_DATASETS_DIR/Seabed-Object-Detection/user-feedback
        base_data_path = Path(domino_datasets_dir) / domino_project_name
    
    feedback_dir = base_data_path / 'user-feedback'
    
    # Fallback if project directory doesn't exist
    if not base_data_path.exists():
        feedback_dir = Path("./user-feedback")
    
    # Create the user-feedback directory
    feedback_dir.mkdir(parents=True, exist_ok=True)
    feedback_file = feedback_dir / f"{feedback_type}_feedback.csv"
    
    file_exists = os.path.exists(feedback_file)
    with open(feedback_file, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(feedback_data.keys()))
        if not file_exists:
            writer.writeheader()
        writer.writerow(feedback_data)

# ─── Create Tabs ─────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["OBJECT ANALYSIS", "TARGET ANNOTATION"])

# ─── Sidebar Content (Shared) ───────────────────────────────────────────────
with st.sidebar:
    st.header("TARGET SELECTION")
    
    if not os.path.exists(test_images_root):
        st.error(f"⚠️ ALERT: Test images directory not found: {test_images_root}")
        st.info("Ensure test images are available in designated locations")
        categories = []
    else:
        categories = get_categories(test_images_root)
    
    if not categories:
        st.warning("⚠️ No target categories found in directory")
        selected_category = None
        selected_image = None
        images = []
    else:
        selected_category = st.selectbox("TARGET CLASS", categories, key="shared_category")
        images = get_image_list(os.path.join(test_images_root, selected_category)) if selected_category else []
        
        if not images and selected_category:
            st.warning(f"⚠️ No images found in category '{selected_category}'")
            selected_image = None
        else:
            selected_image = st.selectbox("SONAR IMAGE ID", images, key="shared_image") if images else None
    
    # Annotation tools (only show in annotation tab)
    st.markdown("---")
    st.header("ANNOTATION TOOLS")
    drawing_mode = st.selectbox("DRAW MODE", ["rect", "transform"], key="drawing_mode")
    stroke_color = st.color_picker("MARKER COLOR", "#00FF00")
    stroke_width = st.slider("LINE WIDTH", 1, 10, 3)

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: OBJECT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════
with tab1:
    st.markdown("### SONAR IMAGE CLASSIFICATION • SELECT TARGET FOR ANALYSIS")
    
    if selected_category and selected_image:
        col1, col2 = st.columns([3, 2])
        
        with col1:
            img_path = os.path.join(test_images_root, selected_category, selected_image)
            image = Image.open(img_path).convert("RGB")
            st.markdown(f"<p class='mono'>◆ TARGET ID: {selected_category}/{selected_image}</p>", unsafe_allow_html=True)
            st.image(image, caption=f"")

        with col2:
            with st.spinner("ANALYZING SONAR SIGNATURE..."):
                results = classifier(image)

            # Show top prediction with styling
            top = results[0]
            label = top["label"]
            score = top["score"]

            # Map labels to military terms
            label_map = {
                "plane": "AIRCRAFT",
                "ship": "VESSEL",
                "seafloor": "SEAFLOOR"
            }
            display_label = label_map.get(label, label.upper())

            st.markdown(f"""
                <div class="prediction-box">
                    <h3 style="margin-top:0; color: #00ff9f;">PRIMARY CLASSIFICATION</h3>
                    <h2 style="margin: 0.5rem 0; color: #00ff9f; font-size: 2rem;">{display_label}</h2>
                    <p style="font-size: 1.3rem; margin-bottom: 0; color: #c9d1d9;">CONFIDENCE: <strong class="mono">{score:.1%}</strong></p>
                </div>
            """, unsafe_allow_html=True)

            # Show all predictions
            with st.expander("FULL CLASSIFICATION REPORT"):
                for i, res in enumerate(results[:5], 1):
                    display_res = label_map.get(res['label'], res['label'].upper())
                    st.markdown(f"<p class='mono'>{i}. {display_res}: {res['score']:.2%}</p>", unsafe_allow_html=True)

            # User Feedback Section
            st.markdown('<div class="feedback-section">', unsafe_allow_html=True)
            st.markdown("#### VERIFICATION REQUEST")
            
            col_yes, col_no = st.columns(2)
            feedback = None

            with col_yes:
                if st.button("✓ CONFIRMED", use_container_width=True, type="primary"):
                    feedback = "yes"
            with col_no:
                if st.button("✗ INCORRECT", use_container_width=True):
                    feedback = "no"

            if feedback:
                feedback_data = {
                    "timestamp": datetime.now().isoformat(),
                    "category": selected_category,
                    "image": selected_image,
                    "predicted_label": label,
                    "score": float(score),
                    "feedback": feedback
                }
                save_feedback(feedback_data, "classification")
                st.success("✓ FEEDBACK LOGGED • CLASSIFICATION VERIFIED")

            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("SELECT TARGET FROM SIDEBAR TO INITIATE ANALYSIS")

# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: TARGET ANNOTATION
# ═══════════════════════════════════════════════════════════════════════════
with tab2:
    st.markdown("### TARGET ANNOTATION SYSTEM • DEFINE REGIONS OF INTEREST")
    
    if selected_category and selected_image:
        img_path_label = os.path.join(test_images_root, selected_category, selected_image)
        
        try:
            image_label = Image.open(img_path_label).convert("RGB")
            
            col1, col2 = st.columns([3, 2])
            
            with col1:
                st.markdown("#### SONAR IMAGE ANNOTATION")
                st.info("USE STREAMLIT IMAGE COORDINATES TO MARK BOUNDING BOXES")
                
                # Scale image for display
                scale_factor = 1.0
                display_width = image_label.width
                display_height = image_label.height
                
                if display_width > 600:
                    scale_factor = 600 / display_width
                    display_width = 600
                    display_height = int(image_label.height * scale_factor)
                    
                if display_height > 500:
                    scale_factor = min(scale_factor, 500 / image_label.height)
                    display_height = 500
                    display_width = int(image_label.width * scale_factor)
                
                # Resize image for display if needed
                if scale_factor < 1.0:
                    display_image = image_label.resize((display_width, display_height), Image.Resampling.LANCZOS)
                else:
                    display_image = image_label
                
                # Initialize bounding box in session state (single box only)
                bbox_key = f"bbox_{selected_category}_{selected_image}"
                if bbox_key not in st.session_state:
                    st.session_state[bbox_key] = None
                
                # Clear button
                col_clear, col_info = st.columns([1, 2])
                with col_clear:
                    if st.button("🗑️ CLEAR BOX", help="Clear the bounding box"):
                        st.session_state[bbox_key] = None
                        # Also clear drawing state
                        drawing_key = f"drawing_{selected_category}_{selected_image}"
                        if drawing_key in st.session_state:
                            st.session_state[drawing_key] = {"mode": "start", "start_point": None, "last_click": None, "current_hover": None}
                        st.rerun()
                
                with col_info:
                    st.markdown(f"<p class='mono'>📐 {image_label.width}×{image_label.height}px</p>", unsafe_allow_html=True)
                
                # Initialize drawing state first
                drawing_key = f"drawing_{selected_category}_{selected_image}"
                if drawing_key not in st.session_state:
                    st.session_state[drawing_key] = {"mode": "start", "start_point": None, "last_click": None, "current_hover": None}
                
                # Import streamlit-image-coordinates 
                from streamlit_image_coordinates import streamlit_image_coordinates
                
                # Get coordinates FIRST to check for new clicks
                coordinates = streamlit_image_coordinates(
                    display_image,  # Use base image for initial coordinate detection
                    width=display_width,
                    height=display_height,
                    key=f"image_coords_{selected_category}_{selected_image}"
                )
                
                # Now draw bounding box on the image (performance optimized)
                from PIL import ImageDraw
                display_image_with_box = display_image.copy()
                draw = ImageDraw.Draw(display_image_with_box)
                
                # Draw existing bounding box (single box only)
                if st.session_state[bbox_key] is not None:
                    bbox = st.session_state[bbox_key]
                    # Scale bounding box to display coordinates
                    x1 = bbox["x"] * scale_factor
                    y1 = bbox["y"] * scale_factor
                    x2 = x1 + bbox["width"] * scale_factor
                    y2 = y1 + bbox["height"] * scale_factor
                    
                    # Draw rectangle
                    draw.rectangle([x1, y1, x2, y2], outline=stroke_color, width=stroke_width)
                    
                    # Draw label
                    draw.text((x1 + 2, y1 + 2), "Object", fill=stroke_color)
                
                # Draw preview box if we're in the middle of drawing
                if (drawing_key in st.session_state and 
                    st.session_state[drawing_key]["mode"] == "end" and 
                    st.session_state[drawing_key]["start_point"] is not None):
                    
                    start_x, start_y = st.session_state[drawing_key]["start_point"]
                    # Scale to display coordinates
                    disp_start_x = start_x * scale_factor
                    disp_start_y = start_y * scale_factor
                    
                    # Draw a crosshair at start point
                    cross_size = 10
                    draw.line([disp_start_x - cross_size, disp_start_y, disp_start_x + cross_size, disp_start_y], fill="red", width=3)
                    draw.line([disp_start_x, disp_start_y - cross_size, disp_start_x, disp_start_y + cross_size], fill="red", width=3)
                    draw.text((disp_start_x + 5, disp_start_y + 5), "START", fill="red")
                    
                    # Draw preview box if we have current coordinates
                    if coordinates is not None:
                        # Scale current coordinates to display
                        curr_x = coordinates["x"]
                        curr_y = coordinates["y"]
                        
                        # Draw preview bounding box
                        preview_x1 = min(disp_start_x, curr_x)
                        preview_y1 = min(disp_start_y, curr_y)
                        preview_x2 = max(disp_start_x, curr_x)
                        preview_y2 = max(disp_start_y, curr_y)
                        
                        # Draw preview box
                        draw.rectangle([preview_x1, preview_y1, preview_x2, preview_y2], 
                                     outline="orange", width=2)
                        draw.text((preview_x1 + 2, preview_y1 + 2), "PREVIEW", fill="orange")
                    else:
                        # Draw instruction text
                        text_x = disp_start_x + 20
                        text_y = disp_start_y - 20 if disp_start_y > 20 else disp_start_y + 20
                        draw.text((text_x, text_y), "Click to complete box", fill="red")
                
                # Re-display with the updated image (if preview was drawn)
                if (drawing_key in st.session_state and 
                    st.session_state[drawing_key]["mode"] == "end" and 
                    coordinates is not None):
                    # Show the image with preview box
                    st.image(display_image_with_box, width=display_width)
                else:
                    # Show the regular image
                    pass  # coordinates already contains the display call
                
                # Get drawing state (already initialized above)
                drawing_state = st.session_state[drawing_key]
                
                # Handle coordinate clicks for bounding box creation
                if coordinates is not None:
                    # Scale coordinates back to original image size
                    orig_x = coordinates["x"] / scale_factor
                    orig_y = coordinates["y"] / scale_factor
                    
                    # Check if this is a new click (avoid processing same click multiple times)
                    current_click = (round(orig_x, 2), round(orig_y, 2))
                    if drawing_state.get("last_click") == current_click:
                        # Same click, ignore
                        pass
                    else:
                        # New click, update last click
                        drawing_state["last_click"] = current_click
                        
                        if drawing_state["mode"] == "start":
                            # First click - set start point
                            drawing_state["start_point"] = (orig_x, orig_y)
                            drawing_state["mode"] = "end"
                            # Don't rerun immediately - let user see the start point
                            
                        elif drawing_state["mode"] == "end":
                            # Second click - create bounding box
                            start_x, start_y = drawing_state["start_point"]
                            end_x, end_y = orig_x, orig_y
                            
                            # Calculate bounding box coordinates
                            bbox_x = min(start_x, end_x)
                            bbox_y = min(start_y, end_y)
                            bbox_width = abs(end_x - start_x)
                            bbox_height = abs(end_y - start_y)
                            
                            # Ensure box is within image bounds
                            bbox_x = max(0, bbox_x)
                            bbox_y = max(0, bbox_y)
                            bbox_width = min(bbox_width, image_label.width - bbox_x)
                            bbox_height = min(bbox_height, image_label.height - bbox_y)
                            
                            # Only create box if it has meaningful size (reduced minimum)
                            if bbox_width >= 3 and bbox_height >= 3:
                                bbox = {
                                    "x": bbox_x,
                                    "y": bbox_y,
                                    "width": bbox_width,
                                    "height": bbox_height
                                }
                                st.session_state[bbox_key] = bbox  # Replace existing box
                            
                            # Reset drawing state
                            drawing_state["mode"] = "start"
                            drawing_state["start_point"] = None
                            drawing_state["last_click"] = None
                
                # Show drawing instructions and status
                if drawing_key in st.session_state:
                    if st.session_state[drawing_key]["mode"] == "start":
                        if st.session_state[bbox_key] is not None:
                            st.markdown("**🔄 REPLACE MODE:** Click to replace the current box with a new one")
                        else:
                            st.markdown("**📐 DRAWING MODE:** Click on the image to start drawing a bounding box")
                    elif st.session_state[drawing_key]["mode"] == "end":
                        start_point = st.session_state[drawing_key]["start_point"]
                        if start_point:
                            st.markdown(f"**📍 FIRST POINT SET:** ({start_point[0]:.0f}, {start_point[1]:.0f})")
                            st.info("👆 **Click another point to complete the bounding box**")
                
                # Reset drawing button
                if drawing_key in st.session_state and st.session_state[drawing_key]["mode"] == "end":
                    if st.button("🔄 Cancel Current Box"):
                        st.session_state[drawing_key]["mode"] = "start"
                        st.session_state[drawing_key]["start_point"] = None
                        st.session_state[drawing_key]["last_click"] = None
                        st.session_state[drawing_key]["current_hover"] = None
                        st.rerun()
                
                # Show current bounding box
                if st.session_state[bbox_key] is not None:
                    st.markdown("#### CURRENT BOUNDING BOX")
                    bbox = st.session_state[bbox_key]
                    st.markdown(f"<p class='mono'>OBJECT: ({bbox['x']:.0f}, {bbox['y']:.0f}) {bbox['width']:.0f}×{bbox['height']:.0f}</p>", unsafe_allow_html=True)
                
                # Create mock canvas result for compatibility
                if st.session_state[bbox_key] is not None:
                    bbox = st.session_state[bbox_key]
                    canvas_result = type('MockCanvas', (), {
                        'json_data': {
                            'objects': [
                                {
                                    'type': 'rect',
                                    'left': bbox['x'] * scale_factor,
                                    'top': bbox['y'] * scale_factor,
                                    'width': bbox['width'] * scale_factor,
                                    'height': bbox['height'] * scale_factor
                                }
                            ]
                        }
                    })()
                else:
                    canvas_result = type('MockCanvas', (), {'json_data': None})()
            
        except Exception as e:
            st.error(f"❌ ERROR LOADING IMAGE: {str(e)}")
            st.info(f"Attempted path: {img_path_label}")
            canvas_result = None
        
        with col2:
            st.markdown("#### TARGET CLASSIFICATION")

            # Label selection
            label_options = ["VESSEL", "AIRCRAFT", "SEAFLOOR"]
            label_map_reverse = {"VESSEL": "ship", "AIRCRAFT": "plane", "SEAFLOOR": "seafloor"}
            selected_label_display = st.selectbox(
                "CLASSIFICATION TYPE",
                label_options,
                key="object_label"
            )
            selected_label = label_map_reverse[selected_label_display]
            
            # Display drawn objects
            if canvas_result is not None and canvas_result.json_data is not None:
                objects = canvas_result.json_data["objects"]
                num_boxes = len([obj for obj in objects if obj["type"] == "rect"])

                st.markdown(f"<p class='mono'>REGIONS MARKED: {num_boxes}</p>", unsafe_allow_html=True)

                if num_boxes > 0:
                    st.markdown("---")
                    st.markdown("#### ANNOTATION DATA")

                    for i, obj in enumerate(objects):
                        if obj["type"] == "rect":
                            st.markdown(f"<p class='mono'>BOX {i+1}: {obj['width']:.0f} × {obj['height']:.0f} px</p>", unsafe_allow_html=True)

                    st.markdown("---")

                    # Save annotation button
                    if st.button("COMMIT ANNOTATION", use_container_width=True, type="primary"):
                        # Save general annotation metadata
                        annotation_data = {
                            "timestamp": datetime.now().isoformat(),
                            "category": selected_category,
                            "image": selected_image,
                            "label": selected_label,
                            "num_boxes": num_boxes,
                            "annotations": json.dumps(objects)
                        }
                        save_feedback(annotation_data, "annotation")
                        
                        # Save detailed bounding box coordinates (scaled back to original image size)
                        for i, obj in enumerate(objects):
                            if obj["type"] == "rect":
                                # Scale coordinates back to original image size
                                orig_x = obj.get("left", 0) / scale_factor
                                orig_y = obj.get("top", 0) / scale_factor  
                                orig_width = obj.get("width", 0) / scale_factor
                                orig_height = obj.get("height", 0) / scale_factor
                                
                                bbox_data = {
                                    "timestamp": datetime.now().isoformat(),
                                    "category": selected_category,
                                    "image": selected_image,
                                    "label": selected_label,
                                    "box_id": i + 1,
                                    "x": orig_x,
                                    "y": orig_y,
                                    "width": orig_width,
                                    "height": orig_height,
                                    "x_center": orig_x + orig_width / 2,
                                    "y_center": orig_y + orig_height / 2,
                                    "image_width": image_label.width,
                                    "image_height": image_label.height,
                                    "scale_factor": scale_factor,
                                    "display_width": display_width,
                                    "display_height": display_height,
                                    "stroke_color": obj.get("stroke", "#00FF00"),
                                    "fill_color": obj.get("fill", "rgba(0, 255, 0, 0.3)")
                                }
                                save_feedback(bbox_data, "bounding_boxes")
                        
                        st.success("✓ ANNOTATION COMMITTED • DATA LOGGED TO ANNOTATION & BOUNDING_BOXES FILES")

            # Instructions
            with st.expander("OPERATION MANUAL"):
                st.markdown("""
                **ANNOTATION PROTOCOL:**
                1. DRAW rectangle around target object
                2. SELECT appropriate classification type
                3. COMMIT annotation to database

                **NOTES:**
                - Multiple bounding boxes supported per image
                - Use TRANSFORM mode to adjust existing boxes
                - All annotations are time-stamped and logged
                """)
    else:
        st.info("SELECT TARGET FROM SIDEBAR TO BEGIN ANNOTATION")

# ─── Footer ─────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align: center; color: #58a6ff; font-family: \"Share Tech Mono\", monospace; letter-spacing: 2px;'>◆ SONAR TARGET CLASSIFICATION SYSTEM v2.1 ◆ CLASSIFIED</div>",
    unsafe_allow_html=True
)