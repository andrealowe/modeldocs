# SEABED OBJECT DETECTION SYSTEM

## MISSION OVERVIEW

Advanced Vision Transformer (ViT) model for automated classification of side-scan sonar imagery. System designed for tactical identification of submerged objects including aircraft and vessels.


### OPERATIONAL CAPABILITIES
- **Enhanced VIT Model**: Optimized for imbalanced seabed object classification
- **Ship Detection Focus**: Specialized improvements for minority class performance  
- **Domino Experiments Integration**: Complete experiment tracking and model registry
- **Class Imbalance Solutions**: Balanced sampling, enhanced augmentation, focal loss

## DATASET INTELLIGENCE

The SeabedObjects dataset contains categorized side-scan sonar images across three target classes:

### TARGET CLASSIFICATION
- **AIRCRAFT**: Submerged aircraft (38 training samples)
- **VESSELS**: Submerged ships and boats (82 training samples)
- **SEAFLOOR**: Empty seabed terrain (378 training samples)

### DATA ORGANIZATION

#### 1. UNBALANCED TRAINING SET (498 images)
Contains comprehensive examples across all target classes with natural distribution:
- Aircraft: 38 images (7.6%)
- Vessels: 82 images (16.5%) 
- Seafloor: 378 images (75.9%)

#### 2. BALANCED TRAINING SET (138 images)
Strategically balanced subset for improved minority class training:
- Aircraft: 38 images (27.5%)
- Vessels: 50 images (36.2%)
- Seafloor: 50 images (36.2%)

#### 3. TEST SET (361 images)
Independent validation environment with varied image characteristics:
- Aircraft: 24 images
- Vessels: 138 images
- Seafloor: 199 images

### VISUAL INTELLIGENCE SAMPLES

#### TARGET CLASSIFICATION EXAMPLES
- **SEAFLOOR TERRAIN**: Standard seabed environment with no artificial objects detected
- **VESSEL CLASSIFICATION**: Submerged maritime vessels showing characteristic sonar signatures  
- **AIRCRAFT CLASSIFICATION**: Submerged aircraft displaying distinctive geometric patterns

---

## QUICK START

Complete the following steps for rapid system deployment:

### 1. Environment Setup
Ensure environment has been configured with required packages. See **Environment Configuration** section at the bottom of this document for Docker setup instructions.

### 2. Data Source Connection
Connect to the following Domino Data Sources:
- `seabed-object-detection` (primary dataset)
- `ground-truth-seabed` (monitoring data)

### 3. Dataset Creation
Execute `01_create_dataset.ipynb` to download and organize operational data from S3.

### 4. Model Training
Train the classification model using either:
- **Notebook**: `02_model_development.ipynb` (recommended for experimentation)
- **Script**: `python src/train_model.py` (recommended for production)

### 5. ETL Pipeline Execution
Run the Domino Flow for image preprocessing:
```bash
pyflyte run --remote flow.py seabed_etl_pipeline_balanced
```

### 6. Launcher Deployment
Configure and deploy the Intelligence Report Generator Launcher via Domino UI (Deployments > Launchers).

### 7. Application Deployment
Deploy the Streamlit application for interactive classification via Domino Apps.

### 8. API Endpoint and Monitoring
- Deploy `predict.py` as a Model API endpoint
- **Quick Setup**: Run `python src/monitoring/setup_monitoring.py` for interactive configuration
- Upload ground truth data: `python src/monitoring/upload_ground_truth_config.py`
- Configure Domino Model Monitor with ground truth auto-ingestion
- See `src/monitoring/MONITORING_README.md` for complete setup guide

---

## SYSTEM ARCHITECTURE

### DETECTION ENHANCEMENT PROTOCOLS
- **Balanced Sampling**: Equal representation during training operations
- **Enhanced Augmentation**: Target-specific transformations (rotation, flip, color)
- **Focal Loss**: Addresses severe class imbalance (optional deployment)
- **Ship-focused Metrics**: Optimizes for vessel F1-score performance
- **Detailed Monitoring**: Per-class confusion matrices and analysis

### TECHNICAL SPECIFICATIONS
- **Base Model**: Google VIT-Base-Patch16-224-in21k
- **Mixed Precision**: FP16 training for operational efficiency
- **Learning Rate Scheduling**: Cosine decay with warmup protocol
- **Label Smoothing**: Prevents overconfidence (0.1 factor)
- **Gradient Clipping**: Stable training with max norm 1.0

## MISSION EXECUTION

### CORE OPERATIONS
- **`01_create_dataset.ipynb`**: S3 data transfer from Domino Data Source into Domino Dataset
- **`02_model_development.ipynb`**: Enhanced training with ship class focus and hyperparameter optimization

### Prerequisites
**Data Source Setup**: Connect a Domino Data Source to your AWS S3 bucket named `seabed-object-detection` in region `us-west-2`. This data source is verified during training and monitoring operations.

### Deployment Steps
1. **DATA ACQUISITION**: Execute `01_create_dataset.ipynb` to download operational data from S3
2. **DATA PREPROCESSING** (Optional): Execute Domino Flows ETL pipeline for image enhancement
3. **TRAINING PROTOCOL**:
   - **Standalone Script**: `python src/train_model.py` (recommended for production)
   - **Notebook**: `02_model_development.ipynb` (recommended for experimentation)
4. **MODEL REGISTRY**: Best model automatically registered - check Models tab for deployment readiness

### Training Script Options
```bash
# Default training (5 epochs, unbalanced dataset)
python src/train_model.py

# Custom configuration
python src/train_model.py --epochs 10 --batch-size 32 --learning-rate 1e-4

# Use balanced dataset (138 images)
python src/train_model.py --balanced

# Force CPU training (no GPU)
python src/train_model.py --no-gpu
```

## DOMINO FLOWS ETL PIPELINE

### OVERVIEW
Automated 4-stage image preprocessing pipeline using Domino Flows for sonar image enhancement:

1. **NORMALIZATION**: Log-gamma transform for consistent luminance
2. **DENOISING**: Median + bilateral filtering with background subtraction
3. **ENHANCEMENT**: CLAHE contrast boost + unsharp mask sharpening
4. **PACKAGING**: Zip processed images and save as Flow Artifact

**Flow Artifacts**: The cleaned sonar data zip file is automatically registered as a "Cleaned Sonar Data" artifact in Domino, making it easily discoverable, inspectable, and reusable across projects. Access artifacts in the Domino UI under Flow Executions > Artifacts.

### EXECUTION COMMANDS

#### Standard Workflows (Recommended)
```bash
# Process balanced dataset (138 images)
pyflyte run --remote flow.py seabed_etl_pipeline_balanced

# Process unbalanced dataset (498 images)
pyflyte run --remote flow.py seabed_etl_pipeline_unbalanced

# Custom gamma transform (0.0 = log transform)
pyflyte run --remote flow.py seabed_etl_pipeline_balanced --gamma_transform 0.0
```

#### Custom Dataset Path
```bash
# Specify custom input dataset location
pyflyte run --remote flow.py seabed_etl_pipeline \
  --input_dataset_path /domino/datasets/local/Seabed-Object-Detection/balanced_training_validation_set

# Custom path with log transform
pyflyte run --remote flow.py seabed_etl_pipeline \
  --input_dataset_path /path/to/custom/dataset \
  --gamma_transform 0.0
```

### OUTPUT ARTIFACTS

**Flow Artifact**: `cleaned_sonar_data_YYYYMMDD_HHMMSS.zip`
- Artifact Name: "Cleaned Sonar Data"
- Type: DATA
- Discoverable in Domino UI Artifacts tab
- Download to workspace with generated code snippet
- Includes complete lineage tracking

### PIPELINE STAGES

| Stage | Description | Output Directory |
|-------|-------------|------------------|
| **Stage 1** | Normalization & gamma correction | `stage1_normalized/` |
| **Stage 2** | Denoising & background subtraction | `stage2_denoised/` |
| **Stage 3** | Feature enhancement (CLAHE + unsharp) | `stage3_enhanced/` |
| **Stage 4** | Package to zip and save to dataset | `cleaned_sonar_data_*.zip` |

### PARAMETERS

- **`input_dataset_path`** (str, required): Path to raw sonar images directory
- **`gamma_transform`** (float, default=0.5): Gamma correction factor
  - `0.0`: Log transform (maximum dynamic range)
  - `0.5`: Standard gamma correction (default)
  - `1.0`: No transformation

## PERFORMANCE REQUIREMENTS

- **Overall Accuracy**: >90%
- **Vessel F1-Score**: >80% (primary optimization target)
- **Balanced Performance**: Enhanced minority class detection capability
- **Tracking**: Complete experiment lineage and model versioning

## OPERATIONAL DEPLOYMENTS

### DOMINO LAUNCHER: INTELLIGENCE REPORT GENERATOR

Self-service web interface for generating customized sonar analysis reports from existing image datasets. Designed for non-technical users to run AI-powered analysis without code.

**CAPABILITIES:**
- **Point-and-Analyze**: Specify any dataset folder and generate intelligence reports
- **Customizable Reports**: Select which sections to include (summary, detections, tactical assessment, detailed results, metadata)
- **Multi-Format Export**: Generate Markdown, HTML, JSON, and CSV outputs simultaneously
- **Rapid Analysis**: Process datasets in 1-3 minutes with configurable image limits
- **Tactical Intelligence**: Automated threat level assessment and operational recommendations

**CONFIGURATION:**
- Location: `src/launchers/simple_report_launcher.py`
- Documentation: `src/launchers/SIMPLE_LAUNCHER_CONFIG.md`
- Setup: Deployments > Launchers > New Launcher in Domino UI

**USE CASES:**
- Quick executive briefings for command staff
- Comprehensive analysis reports for marine archaeologists
- JSON data feeds for automated security systems
- Multi-format intelligence packages for field operations

### APP DEPLOYMENT & ACCESS

#### App Development
To modify and preview your Streamlit app in a Domino Workspace, construct the URL based on your run context. To get the link to view the app, 
replace `your-domino-url` with your actual Domino domain and run:

```bash
echo -e "import os\nprint('https://your-domino-url/{}/{}/notebookSession/{}/proxy/8501/'.format(os.environ['DOMINO_PROJECT_OWNER'], os.environ['DOMINO_PROJECT_NAME'], os.environ['DOMINO_RUN_ID']))" | python3
```

**Note**: Port 8501 is Streamlit's default. Remap to 8888 when publishing as a Domino App.

Then start the app with the following:
```bash
# Launch in workspace
streamlit run streamlit-app.py
```

Open the generated URL in your browser to access the live app.

### INTERACTIVE CLASSIFICATION SYSTEM
Streamlit-based SONAR TARGET CLASSIFICATION SYSTEM with dual-mode operations:


**OPERATIONAL MODES:**
- **TEST MODE**: Real-time sonar image classification with model predictions and user feedback collection
- **ANNOTATION MODE**: Military-grade bounding box annotation system for training data creation
  - Two-click bounding box creation with real-time preview
  - Single-box annotation for precision targeting
  - Annotation data archived for model improvement

### API ENDPOINT & CLI TESTING
**Domino Model API**: Deploy `predict.py` as REST API endpoint for programmatic integration

**Command-Line Testing**: Test predictions directly in terminal
```bash
# Quick prediction
python predict.py /path/to/image.png

# Detailed analysis with sonar features
python predict.py /path/to/image.png --verbose

# JSON output for automation
python predict.py /path/to/image.png --json
```

**Example Output:**
```
Analyzing: /mnt/example-images/ship.png
SHIP (75.23% confidence)
   183x190px | Brightness: 62.9 | Contrast: 160.2
   Edges: 0.1000 | Dark: 25.68% | Bright: 0.00% | SNR: 2.22
```
---

## TRAINING DATA EXPORT FOR MODEL MONITORING

Generate comprehensive training baseline CSV with all 11 sonar features using the `/mnt/monitoring/generate_training_data.py` script

**Output:** `/mnt/monitoring/training_data/training_data.csv`

**Contents:**
- 498 training images (unbalanced dataset: 7.6% plane, 16.5% ship, 75.9% seafloor)
- 11 sonar features per image (same features used in predictions)
- Ground truth labels with perfect confidence (1.0)
- Event IDs and timestamps for tracking

**Features Extracted:**
- Image metadata: filename, size, width, height
- Brightness stats: mean, std, contrast
- Detection features: edge density, dark/bright pixel ratios, SNR estimate

**Register with Domino Model Monitoring:**

```bash
# Register as Domino TrainingSet with monitoring metadata
python /mnt/monitoring/register_training_set.py

# Verify: Data > Training Sets > seabed-sonar-training-baseline
```
---

## MODEL MONITORING (DOMINO MODEL MONITOR)

Real-time performance tracking and drift detection with unified configuration system.

### CAPABILITIES
- **Model Quality**: Accuracy, precision, recall, F1-score, AUC-ROC, log loss
- **Data Drift**: 11 sonar-specific features tracked continuously  
- **Ground Truth Matching**: Automatic event ID correlation

### QUICK SETUP

**Interactive Setup (Recommended):**
```bash
python src/monitoring/setup_monitoring.py
```

**Manual Commands:**
```bash
# Upload ground truth data
python src/monitoring/upload_ground_truth_config.py

# Generate daily monitoring data  
python src/monitoring/generate_monitoring_data.py
```

**Complete Guide:** See `src/monitoring/MONITORING_README.md`

---

## ENVIRONMENT CONFIGURATION (DOMINO 6.1)

To deploy required dependencies in Domino 6.1 environment, add the following Docker configuration:

```dockerfile
USER root

# Fix NumPy, TensorFlow and Keras compatibility
RUN pip install --no-cache-dir "numpy==1.26.4" --force-reinstall && \
      pip install --no-cache-dir "tensorflow>=2.19.0,<2.20.0" && \
      pip install --no-cache-dir "tf-keras>=2.19.0,<2.20.0" && \
      pip install --no-cache-dir "protobuf>=4.24.0,<5.0.0"

# Install ML and Streamlit dependencies
RUN pip install --no-cache-dir \
      "streamlit>=1.28.0,<1.30.0" \
      "streamlit-image-coordinates>=0.1.6" \
      "transformers>=4.20.0" \
      "torch>=1.13.0" \
      "Pillow>=9.0.0" \
      "accelerate>=0.26.0" \
      "packaging>=21.0" \
	   torchvision \
       evaluate \
       opencv-python \
       streamlit-drawable-canvas
```

### DEPLOYMENT INSTRUCTIONS

1. **Environment Management**: Navigate to Domino workspace → Environments
2. **Configuration**: Create new environment or edit existing configuration
3. **Docker Instructions**: Add RUN commands to "Dockerfile Instructions" section
4. **Build Process**: Save and build environment
5. **Project Assignment**: Select environment for workspace and application deployment

### DEPENDENCY MANIFEST
- **Core ML**: `torch`, `torchvision`, `transformers`, `accelerate`
- **Interface**: `streamlit`, `streamlit-drawable-canvas` 
- **Data Processing**: `pandas`, `numpy<2.0.0`, `Pillow`
- **Model Evaluation**: `evaluate`, `optuna`
- **Computer Vision**: `opencv-python`
- **Compatibility**: `tf-keras`, `packaging`

**NOTE**: NumPy version locked to `<2.0.0` to prevent compatibility conflicts with transformers and ML libraries.

---

**CLASSIFICATION: UNCLASSIFIED**