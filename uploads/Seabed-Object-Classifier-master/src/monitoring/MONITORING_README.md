# Model Monitoring - Quick Setup Guide

## Overview

Seabed object detection model monitoring with **Domino Model Monitor**:
- **Data Drift**: 11 sonar image features tracked
- **Model Quality**: Accuracy, precision, recall, F1-score, AUC-ROC, log loss  
- **Ground Truth Matching**: Automatic event_id correlation

---

## Quick Setup (10 Minutes)

### Step 1: Configure Monitoring

**Option A: Interactive Setup (Recommended)**
```bash
python src/monitoring/setup_monitoring.py
```
Follow prompts to configure URLs, model IDs, and data sources.

**Option B: Manual Config**
Edit `/mnt/artifacts/monitoring/model_config.json`:
```json
{
  "domino": {
    "base_url": "https://se-demo.domino.tech"
  },
  "model_api": {
    "endpoint_url": "https://se-demo.domino.tech:443/models/YOUR_MODEL_ID/latest/model",
    "token": "YOUR_API_TOKEN"
  },
  "model_monitor": {
    "model_id": "68efe5dcdbdc7bf9bad685b8"
  },
  "data_sources": {
    "ground_truth": "ground-truth-seabed-classifier"
  }
}
```

### Step 2: Set Environment Variables

```bash
export DOMINO_USER_API_KEY="your-api-key-here"
```

### Step 3: Upload Ground Truth Data

```bash
# Upload ground truth files from last 24 hours
python src/monitoring/upload_ground_truth_config.py

# Upload specific date range
python src/monitoring/upload_ground_truth_config.py --start-date 2025-10-25 --end-date 2025-10-27

# Test without uploading
python src/monitoring/upload_ground_truth_config.py --dry-run
```

### Step 4: Deploy Model Endpoint

1. Deploy `predict.py` as Domino Model API
2. In Model Monitor UI, configure ground truth auto-ingestion
3. Use content from `src/monitoring/ground_truth_config.json`

### Step 5: Schedule Daily Monitoring (Optional)

```bash
# Generate daily predictions and ground truth
python src/monitoring/generate_monitoring_data.py
```

**Done!** Model Monitor will automatically match predictions to ground truth via `event_id`.

---

## Key Commands

### Upload Ground Truth
```bash
python src/monitoring/upload_ground_truth_config.py           # Last 24 hours
python src/monitoring/upload_ground_truth_config.py --hours 48 # Last 48 hours  
python src/monitoring/upload_ground_truth_config.py --dry-run  # Test mode
```

### Test Predictions
```bash
python predict.py /path/to/image.png                         # Quick test
python predict.py /path/to/image.png --verbose               # Detailed output
```

### Generate Monitoring Data
```bash
python src/monitoring/generate_monitoring_data.py            # 30 daily predictions
```

---

## Architecture

### Data Flow
```
Predictions → DataCaptureClient → Model Monitor
Ground Truth → S3 Data Source → Model Monitor Auto-Ingestion
                     ↓
            Event ID Matching → Quality Metrics
```

### Key Files
- **`model_config.json`** - Unified configuration
- **`config_loader.py`** - Configuration management
- **`upload_ground_truth_config.py`** - Ground truth registration
- **`predict.py`** - Model inference with monitoring
- **`generate_monitoring_data.py`** - Daily data generation

---

## Troubleshooting

### No Quality Metrics
- Wait 24 hours for first ingestion
- Check Model Monitor → Configuration → Ground Truth (Status: Active)
- Verify data source exists: `ground-truth-seabed-classifier`

### Configuration Issues
```bash
python src/monitoring/config_loader.py  # Test config loading
```

### Event ID Matching
- Predictions use same `event_id` as ground truth
- Both have matching timestamps
- Ground truth uploaded to correct S3 path

---

## Metrics Tracked

**Quality Metrics**: Accuracy (>90%), F1-Score (>85%), AUC-ROC (>0.85)  
**Drift Detection**: 11 sonar features (brightness, contrast, edge density, SNR)  
**Classes**: plane, ship, seafloor

---

## Support

- **Project docs**: `/mnt/artifacts/CLAUDE.md`
- **Interactive setup**: `python src/monitoring/setup_monitoring.py`
- **Config test**: `python src/monitoring/config_loader.py`