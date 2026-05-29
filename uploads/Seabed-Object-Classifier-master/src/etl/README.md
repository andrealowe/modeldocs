# SEABED SONAR ETL PROCESSING PIPELINE

## MISSION OVERVIEW

This directory contains the ETL processing scripts for the Seabed Object Detection system. The pipeline transforms raw side-scan sonar imagery through a four-stage process optimized for machine learning training.

## DIRECTORY STRUCTURE

```
src/etl/
├── etl_normalize.py        # Stage 1: Flow-compatible normalization
├── etl_denoise.py          # Stage 2: Flow-compatible denoising
├── etl_enhance.py          # Stage 3: Flow-compatible enhancement
├── etl_package.py          # Stage 4: Flow-compatible packaging
├── standalone/             # Standalone scripts (legacy)
│   ├── load-dataset.py
│   ├── denoise_and_background.py
│   ├── enhance_features.py
│   └── organize_outputs.py
├── README.md
└── requirements.txt
```

## DOMINO FLOWS PIPELINE (Recommended)

The **etl_*.py** scripts are designed for Domino Flows and use standardized I/O paths. These scripts work in both git-based and file-based Domino projects through dynamic path resolution.

### Execution via flow.py:
```bash
# Process balanced dataset (138 images)
pyflyte run --remote flow.py seabed_etl_pipeline_balanced

# Process unbalanced dataset (498 images)
pyflyte run --remote flow.py seabed_etl_pipeline_unbalanced

# Custom dataset path
pyflyte run --remote flow.py seabed_etl_pipeline \
  --input_dataset_path /path/to/dataset \
  --gamma_transform 0.5
```

---

## PROCESSING STAGES

### STAGE 1: NORMALIZATION (`etl_normalize.py`)
**OBJECTIVE**: Normalize raw sonar imagery and apply gamma correction.

**I/O**:
- Input: Command-line argument `--input_dir`
- Gamma: Reads from `/workflow/inputs/gamma` or `--gamma` flag
- Output: `/workflow/outputs/normalized_data/`

**OPERATIONS**:
- Intensity normalization to [0,1] range
- Gamma correction (0.5 default) or log transform (gamma=0.0)
- Preserve class directory structure (plane/ship/seafloor)

---

### STAGE 2: DENOISING (`etl_denoise.py`)
**OBJECTIVE**: Remove noise and subtract background.

**I/O**:
- Input: `/workflow/inputs/normalized_data/`
- Output: `/workflow/outputs/denoised_data/`

**OPERATIONS**:
- Median filtering (kernel size: 5) for impulse noise
- Bilateral filtering (d=9, sigma=75) for edge-preserving smoothing
- Morphological background subtraction (kernel: 51)

---

### STAGE 3: ENHANCEMENT (`etl_enhance.py`)
**OBJECTIVE**: Enhance contrast and sharpen features.

**I/O**:
- Input: `/workflow/inputs/denoised_data/`
- Output: `/workflow/outputs/enhanced_data/`

**OPERATIONS**:
- CLAHE (Contrast Limited Adaptive Histogram Equalization)
- Unsharp masking for feature sharpening
- Final preprocessing for training readiness

---

### STAGE 4: PACKAGING (`etl_package.py`)
**OBJECTIVE**: Package processed images into zip file.

**I/O**:
- Input: `/workflow/inputs/enhanced_data/`
- Output: `/workflow/outputs/cleaned_data_zip` (timestamped .zip file)

**OUTPUT FORMAT**: `cleaned_sonar_data_YYYYMMDD_HHMMSS.zip`

---

## STANDALONE SCRIPTS (Legacy)

The `standalone/` directory contains legacy scripts for manual processing outside of Flows:

- **`load-dataset.py`**: Stage 1 normalization (standalone)
- **`denoise_and_background.py`**: Stage 2 denoising (standalone)
- **`enhance_features.py`**: Stage 3 enhancement (standalone)
- **`organize_outputs.py`**: Utility for organizing outputs

These scripts accept command-line arguments and write to specified output directories. Use the Flow-compatible `etl_*.py` scripts for production workflows.

---

## REQUIREMENTS

Install dependencies:
```bash
pip install -r requirements.txt
```

**Core Dependencies**:
- OpenCV (`cv2`)
- NumPy
- Python 3.8+

---

## ENVIRONMENT COMPATIBILITY

The ETL pipeline automatically adapts to different Domino environments:

- **Git-based projects**: Uses `/mnt/code` as working directory
- **File-based projects**: Uses `/mnt` as working directory
- **Path resolution**: Handled via `DOMINO_WORKING_DIR` environment variable

No manual configuration required - scripts detect and adapt automatically.

---

## OUTPUT ARTIFACTS

### Final Output
Processed images packaged as a zip file containing:
```
cleaned_sonar_data_YYYYMMDD_HHMMSS.zip
├── plane/          # Enhanced aircraft images
├── ship/           # Enhanced vessel images
└── seafloor/       # Enhanced seafloor images
```

### Processing Stats
Each stage logs:
- Images processed count
- Processing timestamp
- Parameters used
- Success rate

---

## OPERATIONAL REQUIREMENTS

### Hardware
- **Minimum**: 4GB RAM, CPU processing
- **Recommended**: 8GB RAM for large datasets
- **Domino Flows Tier**: Small

### Input Specifications
- **Formats**: PNG, JPG, JPEG, TIF, BMP
- **Structure**: Class subdirectories (plane/ship/seafloor)
- **Type**: Grayscale sonar imagery

---

**CLASSIFICATION: UNCLASSIFIED**
