#!/usr/bin/env python3
"""
Training Set Generation and Registration for Model Monitor
Combined script that generates training data CSV and registers with Domino Model Monitor

Supports both git-based and file-based Domino projects through dynamic path resolution.
Creates unique training set names with timestamps to avoid conflicts across projects.

Usage:
    python src/monitoring/generate_and_register_training_set.py
    python src/monitoring/generate_and_register_training_set.py --generate-only
    python src/monitoring/generate_and_register_training_set.py --register-only

Example Training Set Name: seabed-sonar-training-baseline-20251012_184918
"""

import sys
import os
import csv
import argparse
from pathlib import Path
from PIL import Image
import uuid
from datetime import datetime, timezone
import numpy as np
import pandas as pd

# Add working directory to path for imports
working_dir = os.environ.get('DOMINO_WORKING_DIR', '/mnt')
sys.path.insert(0, working_dir)

from predict import extract_sonar_features
from src.data_config import DataConfig

# Import Domino Training Set client (optional)
try:
    from domino.training_sets import TrainingSetClient, model
    DOMINO_AVAILABLE = True
except ImportError:
    DOMINO_AVAILABLE = False

# Initialize config for adaptive paths
config = DataConfig()

# Dynamic output path based on project type
# Git-based: /mnt/code -> save to /mnt/artifacts/monitoring
# File-based: /mnt -> save to /mnt/monitoring
if config.domino_working_dir == '/mnt/code':
    # Git-based project - use artifacts
    OUTPUT_BASE = Path('/mnt/artifacts/monitoring')
else:
    # File-based project - use main directory
    OUTPUT_BASE = Path('/mnt/monitoring')

OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
TRAINING_DATA_OUTPUT = OUTPUT_BASE / "training_data"
TRAINING_DATA_OUTPUT.mkdir(parents=True, exist_ok=True)

# Training set configuration with timestamp for uniqueness
TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")
TRAINING_SET_NAME = f"seabed-sonar-training-baseline-{TIMESTAMP}"
TRAINING_DATA_PATH = config.unbalanced_dataset_path

# Column specifications for Model Monitor
KEY_COLUMNS = ["event_id"]
TARGET_COLUMNS = ["predicted_class"]
TIMESTAMP_COLUMNS = ["timestamp"]

FEATURE_COLUMNS = [
    "image_filename", "image_size_kb", "image_width", "image_height",
    "mean_brightness", "std_brightness", "contrast",
    "edge_density", "dark_pixel_ratio", "bright_pixel_ratio", "snr_estimate",
    "confidence_score"
]

CATEGORICAL_COLUMNS = ["image_filename", "predicted_class"]
EXCLUDE_COLUMNS = ["data_type"]


class TrainingSetManager:
    """Generate training data and register with Model Monitor"""

    def __init__(self):
        self.output_file = TRAINING_DATA_OUTPUT / "training_data.csv"
        self.records = []

    def generate_training_data(self):
        """Process all training images and extract features"""
        print("="*60)
        print("TRAINING DATA GENERATION")
        print("="*60)
        print(f"Project Type: {'Git-based' if config.domino_working_dir == '/mnt/code' else 'File-based'}")
        print(f"Output Path: {OUTPUT_BASE}")
        print(f"Source: {TRAINING_DATA_PATH}")
        print()

        classes = ['plane', 'ship', 'seafloor']
        total_processed = 0

        for class_name in classes:
            class_dir = TRAINING_DATA_PATH / class_name

            if not class_dir.exists():
                print(f"⚠️  Warning: {class_dir} not found, skipping...")
                continue

            # Get all images
            images = list(class_dir.glob("*.png")) + list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.jpeg"))

            print(f"📂 Processing {class_name}: {len(images)} images")

            for img_path in images:
                try:
                    # Extract image features using predict.py function
                    img = Image.open(img_path).convert("RGB")

                    # Extract all 11 sonar features
                    features = extract_sonar_features(img, str(img_path))

                    # Create training record with all features
                    record = {
                        'event_id': str(uuid.uuid4()),
                        'timestamp': datetime.now(timezone.utc).isoformat(),
                        # Sonar image features (11 total)
                        'image_filename': features['image_filename'],
                        'image_size_kb': features['image_size_kb'],
                        'image_width': features['image_width'],
                        'image_height': features['image_height'],
                        'mean_brightness': features['mean_brightness'],
                        'std_brightness': features['std_brightness'],
                        'contrast': features['contrast'],
                        'edge_density': features['edge_density'],
                        'dark_pixel_ratio': features['dark_pixel_ratio'],
                        'bright_pixel_ratio': features['bright_pixel_ratio'],
                        'snr_estimate': features['snr_estimate'],
                        # Target and metadata
                        'predicted_class': class_name,  # Ground truth used as "prediction"
                        'confidence_score': 1.0,  # Perfect confidence for training labels
                        'data_type': 'training'
                    }

                    self.records.append(record)
                    total_processed += 1

                except Exception as e:
                    print(f"   ⚠️  Error processing {img_path.name}: {e}")

        print()
        print(f"✅ Total images processed: {total_processed}")
        print()

        return total_processed > 0

    def save_training_data(self):
        """Save training data to CSV"""
        print("💾 Saving training data...")

        with open(self.output_file, 'w', newline='') as f:
            if self.records:
                fieldnames = [
                    'event_id', 'timestamp',
                    # Sonar features (11 total)
                    'image_filename', 'image_size_kb', 'image_width', 'image_height',
                    'mean_brightness', 'std_brightness', 'contrast',
                    'edge_density', 'dark_pixel_ratio', 'bright_pixel_ratio', 'snr_estimate',
                    # Target and metadata
                    'predicted_class', 'confidence_score', 'data_type'
                ]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.records)

        print(f"   File: {self.output_file}")
        print(f"   Records: {len(self.records)}")
        print(f"   Features: 11 sonar image features")
        print()

    def show_statistics(self):
        """Generate training data statistics"""
        if not self.records:
            return

        # Calculate class distribution and feature statistics
        class_counts = {}
        total_size = 0
        brightness_sum = 0
        contrast_sum = 0
        edge_density_sum = 0
        snr_sum = 0

        for record in self.records:
            cls = record['predicted_class']
            class_counts[cls] = class_counts.get(cls, 0) + 1
            total_size += record['image_size_kb']
            brightness_sum += record['mean_brightness']
            contrast_sum += record['contrast']
            edge_density_sum += record['edge_density']
            snr_sum += record['snr_estimate']

        n = len(self.records)
        avg_size = total_size / n
        avg_brightness = brightness_sum / n
        avg_contrast = contrast_sum / n
        avg_edge_density = edge_density_sum / n
        avg_snr = snr_sum / n

        print("="*60)
        print("TRAINING DATA STATISTICS")
        print("="*60)
        print(f"Total Records: {n}")
        print()
        print("Class Distribution:")
        for cls in ['plane', 'ship', 'seafloor']:
            count = class_counts.get(cls, 0)
            pct = count / n * 100
            print(f"   {cls:12s}: {count:4d} ({pct:5.1f}%)")
        print()
        print("Feature Averages (Training Baseline):")
        print(f"   Image Size:      {avg_size:.2f} KB")
        print(f"   Mean Brightness: {avg_brightness:.2f}")
        print(f"   Contrast:        {avg_contrast:.2f}")
        print(f"   Edge Density:    {avg_edge_density:.4f}")
        print(f"   SNR Estimate:    {avg_snr:.2f}")
        print()
        print("="*60)
        print()

    def register_with_domino(self):
        """Register training set with Domino Model Monitor"""
        if not DOMINO_AVAILABLE:
            print("⚠️  Warning: domino.training_sets not available")
            print("   Install with: pip install dominodatalab")
            print("   Skipping registration...")
            return False

        if not self.output_file.exists():
            print(f"❌ Training data not found: {self.output_file}")
            print(f"   Run with --generate-only first")
            return False

        print("="*60)
        print("DOMINO TRAINING SET REGISTRATION")
        print("="*60)
        print()

        # Load CSV
        print(f"📂 Loading training data from: {self.output_file}")
        df = pd.read_csv(self.output_file)

        print(f"   Records: {len(df)}")
        print(f"   Columns: {len(df.columns)}")
        print()

        # Show class distribution
        class_counts = df['predicted_class'].value_counts()
        print("Class Distribution:")
        for cls, count in class_counts.items():
            pct = count / len(df) * 100
            print(f"   {cls:12s}: {count:4d} ({pct:5.1f}%)")
        print()

        # Define monitoring metadata
        print("📋 Registering Training Set with Domino...")
        print(f"   Name: {TRAINING_SET_NAME}")
        print()

        monitoring_meta = model.MonitoringMeta(
            timestamp_columns=TIMESTAMP_COLUMNS,
            categorical_columns=CATEGORICAL_COLUMNS,
        )

        # Additional metadata
        meta = {
            "dataset": "unbalanced_training_validation_set",
            "total_images": str(len(df)),
            "classes": "plane, ship, seafloor",
            "features": str(len(FEATURE_COLUMNS)),
            "description": "Sonar image training baseline with 11 extracted features",
            "project_type": "git-based" if config.domino_working_dir == '/mnt/code' else "file-based",
            "output_path": str(OUTPUT_BASE)
        }

        try:
            # Create training set version
            print("Creating training set version...")
            training_set_version = TrainingSetClient.create_training_set_version(
                training_set_name=TRAINING_SET_NAME,
                df=df,
                key_columns=KEY_COLUMNS,
                target_columns=TARGET_COLUMNS,
                exclude_columns=EXCLUDE_COLUMNS,
                monitoring_meta=monitoring_meta,
                meta=meta
            )

            print("✅ Training set registered successfully!")
            print()
            print("Training Set Details:")
            print(f"   Name: {TRAINING_SET_NAME}")

            # Try to get version number if available
            try:
                if hasattr(training_set_version, 'training_set_version_number'):
                    print(f"   Version: {training_set_version.training_set_version_number}")
                elif hasattr(training_set_version, 'version'):
                    print(f"   Version: {training_set_version.version}")
            except:
                pass

            print(f"   Records: {len(df)}")
            print(f"   Features: {len(FEATURE_COLUMNS)} (11 sonar + 1 confidence)")
            print(f"   Target: {TARGET_COLUMNS[0]}")
            print()

            # Show feature summary
            print("Feature Columns (matching prediction schema):")
            for feat in FEATURE_COLUMNS:
                feat_type = "categorical" if feat in CATEGORICAL_COLUMNS else "continuous"
                print(f"   - {feat:25s} ({feat_type})")
            print()

            print("="*60)
            print("NEXT STEPS")
            print("="*60)
            print()
            print("1. Verify training set in Domino UI:")
            print("   Navigate to: Data > Training Sets")
            print(f"   Look for: {TRAINING_SET_NAME}")
            print()
            print("2. Configure Model Monitor:")
            print("   - Use this training set as baseline")
            print("   - Enable drift detection on features")
            print("   - Set alert thresholds")
            print()

            return True

        except Exception as e:
            print(f"❌ Error registering training set: {e}")
            print()
            print("Troubleshooting:")
            print("   1. Ensure domino.training_sets is installed")
            print("   2. Verify Domino authentication is configured")
            print("   3. Check project permissions")
            print()
            import traceback
            traceback.print_exc()
            return False

    def run(self, generate=True, register=True):
        """Main execution"""
        try:
            if generate:
                # Process training images
                success = self.generate_training_data()

                if not success:
                    print("❌ No training data processed")
                    return 1

                # Save to CSV
                self.save_training_data()

                # Show statistics
                self.show_statistics()

            if register:
                # Register with Domino
                success = self.register_with_domino()

                if not success:
                    print("⚠️  Registration failed or skipped")
                    return 1

            print()
            print("✅ Process complete!")
            print()
            return 0

        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return 1


def ensure_config_exists():
    """Create model_config.json template if it doesn't exist"""
    if not CONFIG_FILE.exists():
        print("🔧 Creating model configuration template...")
        
        template_content = {
            "_comment_1": "Model Monitoring Configuration",
            "_comment_2": "Fill in your Domino Model API details below",
            "_comment_3": "Example URL: https://your-domino.com/models/abc123def456/labels/prod/model",
            "model_api_url": "REPLACE_WITH_YOUR_MODEL_API_URL",
            "_comment_4": "Get API token from your deployed model's API settings",
            "model_api_token": "REPLACE_WITH_YOUR_MODEL_API_TOKEN",
            "_comment_5": "Name of your S3 Data Source in Domino (exact match required)",
            "datasource_name": "REPLACE_WITH_YOUR_DATASOURCE_NAME",
            "_comment_6": "Optional settings (these have sensible defaults)",
            "daily_predictions": 30,
            "api_timeout": 60,
            "min_interval_seconds": 1,
            "max_interval_seconds": 5
        }
        
        with open(CONFIG_FILE, 'w') as f:
            json.dump(template_content, f, indent=2)
        
        print(f"✅ Template created: {CONFIG_FILE}")
        print("📝 Please edit this file and fill in your model details before running monitoring scripts.")
        print("💡 This is just a template creation - training data generation will continue.")
        print()


def main():
    """Main execution with argument parsing"""
    parser = argparse.ArgumentParser(
        description="Generate and register training data for Model Monitor"
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Only generate training data CSV (skip registration)"
    )
    parser.add_argument(
        "--register-only",
        action="store_true",
        help="Only register existing CSV with Domino (skip generation)"
    )

    args = parser.parse_args()

    # Determine what to run
    generate = not args.register_only
    register = not args.generate_only

    manager = TrainingSetManager()
    exit_code = manager.run(generate=generate, register=register)
    sys.exit(exit_code)


if __name__ == "__main__":
    # Ensure config exists (create template if needed)
    ensure_config_exists()
    main()
