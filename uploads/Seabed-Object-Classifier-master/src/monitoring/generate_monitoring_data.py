#!/usr/bin/env python3
"""
Synthetic Data Generator for Model Monitoring
Generates realistic predictions per day with gradual drift

Schedule: Run daily at 2:00 AM
Command: python /mnt/src/monitoring/generate_monitoring_data.py
"""

import sys
import os
import json
import random
import time
import csv
import requests
import io
import base64
from datetime import datetime, timezone
from pathlib import Path

# Add src directory to path for imports
current_dir = Path(__file__).parent
src_paths = [
    str(current_dir.parent),   # /mnt/code/src
    '/mnt/code/src',           # Git-based project
    '/mnt/src',                # File-based project
    '/mnt/code',               # Git root
    '/mnt',                    # File-based root
]
for path in src_paths:
    if path not in sys.path and Path(path).exists():
        sys.path.insert(0, path)

# Import configurations
from data_config import DataConfig
from config_loader import get_config

# Initialize configurations
data_config = DataConfig()
monitoring_config = get_config()
TEST_DATASET_PATH = data_config.test_dataset_path

# Import Domino Data Source client
try:
    from domino.data_sources import DataSourceClient
    DATASOURCE_AVAILABLE = True
except ImportError:
    DATASOURCE_AVAILABLE = False
    print("⚠️  Warning: domino.data_sources not available - ground truth upload disabled")




def extract_model_id(model_url):
    """Extract model ID from Domino Model API URL"""
    try:
        # Expected format: https://domain.com/models/MODEL_ID/labels/LABEL/model
        if '/models/' not in model_url:
            raise ValueError("URL must contain '/models/' path")
        
        model_id = model_url.split('/models/')[1].split('/')[0]
        
        if not model_id or len(model_id) < 10:
            raise ValueError("Invalid model ID extracted")
            
        return model_id
    except Exception as e:
        print(f"❌ Failed to extract model ID from URL: {model_url}")
        print(f"   Error: {e}")
        print("   Expected format: https://domain.com/models/MODEL_ID/labels/LABEL/model")
        sys.exit(1)


def print_config_summary(config, model_id):
    """Print configuration summary with masked token"""
    print("="*60)
    print("CONFIGURATION SUMMARY")
    print("="*60)
    
    # Mask token for security
    token = config.model_api_token
    masked_token = f"****...{token[-4:]}" if len(token) > 4 else "****"
    
    print(f"Model API URL: {config.model_api_url}")
    print(f"Model ID: {model_id}")
    print(f"API Token: {masked_token}")
    print(f"Data Source: {config.ground_truth_datasource}")
    print(f"Daily Predictions: {config.daily_predictions}")
    print(f"API Timeout: {config.model_api_timeout}s")
    print(f"Ground Truth Path: ground_truth/{model_id}/")
    print(f"Config Location: {config.config_file}")
    print()


class MonitoringDataGenerator:
    """Generate monitoring data from real API predictions"""

    def __init__(self, config):
        self.config = config
        self.model_id = extract_model_id(config.model_api_url)
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.predictions = []
        
        # Configuration values
        self.model_api_url = config.model_api_url
        self.model_api_token = config.model_api_token
        self.datasource_name = config.ground_truth_datasource
        self.daily_predictions = config.daily_predictions
        self.api_timeout = config.model_api_timeout
        self.min_interval = config.min_interval_seconds
        self.max_interval = config.max_interval_seconds
        
        # Model-specific ground truth path
        self.ground_truth_prefix = f"ground_truth/{self.model_id}/"

    def get_test_images(self):
        """Load test images organized by class"""
        images_by_class = {
            'plane': [],
            'ship': [],
            'seafloor': []
        }

        for class_name in images_by_class.keys():
            class_dir = TEST_DATASET_PATH / class_name
            if class_dir.exists():
                images = list(class_dir.glob("*.png")) + list(class_dir.glob("*.jpg"))
                images_by_class[class_name] = images

        return images_by_class

    def select_random_image(self, images_by_class, target_class):
        """Select a random image from target class"""
        if target_class in images_by_class and images_by_class[target_class]:
            return random.choice(images_by_class[target_class])
        return None

    def call_model_api(self, image_path):
        """
        Call deployed Model API with base64 encoded image

        Args:
            image_path: Path to image file

        Returns:
            dict: API response with label, score, event_id, timestamp
        """
        try:
            # Read and encode image as base64
            with open(image_path, 'rb') as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # Prepare JSON payload
            payload = {
                'data': {
                    'image': image_data
                }
            }

            # Send request with HTTP Basic Auth
            response = requests.post(
                self.model_api_url,
                json=payload,
                auth=(self.model_api_token, self.model_api_token),
                timeout=self.api_timeout
            )

            # Check HTTP status
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()

            # Extract result from nested structure
            result = response_data.get('result', response_data)

            # Validate response format
            if 'label' not in result or 'score' not in result:
                return {'error': f'Invalid API response format: {response_data}'}

            return result

        except requests.exceptions.Timeout:
            return {'error': f'API request timeout after {self.api_timeout} seconds'}
        except requests.exceptions.ConnectionError as e:
            return {'error': f'Connection error: {e}'}
        except requests.exceptions.HTTPError as e:
            return {'error': f'HTTP error {response.status_code}: {e}'}
        except Exception as e:
            return {'error': f'Unexpected error calling API: {e}'}

    def generate_predictions(self):
        """Generate predictions from real Model API calls"""
        print("="*60)
        print("MODEL API MONITORING DATA GENERATION")
        print("="*60)
        print(f"Date: {self.today}")
        print(f"Target predictions: {self.daily_predictions}")
        print()

        # Load test images
        print("📂 Loading test images...")
        images_by_class = self.get_test_images()
        total_available = sum(len(imgs) for imgs in images_by_class.values())
        print(f"   Available: {total_available} images")

        # Show distribution
        for cls, imgs in images_by_class.items():
            print(f"      {cls}: {len(imgs)} images")
        print()

        # Generate predictions
        print(f"🎯 Generating {self.daily_predictions} predictions...")
        successful = 0
        failed = 0

        for i in range(self.daily_predictions):
            try:
                # Randomly select class (uniform distribution)
                target_class = random.choice(['plane', 'ship', 'seafloor'])

                # Select random image from that class
                image_path = self.select_random_image(images_by_class, target_class)

                if not image_path:
                    print(f"   ⚠️  No images available for class: {target_class}")
                    failed += 1
                    continue

                # Call deployed Model API
                result = self.call_model_api(image_path)

                if 'error' in result:
                    print(f"   ❌ API call failed: {result['error']}")
                    failed += 1
                    continue

                # Get actual class from ground truth (folder structure)
                actual_class = target_class

                # Get predicted class and confidence from API response
                predicted_class = result.get('label', 'unknown')
                confidence_score = result.get('score', 0.0)

                # Store prediction metadata for ground truth generation
                prediction_record = {
                    'event_id': result.get('event_id', f'api_{i}_{datetime.now().timestamp()}'),
                    'timestamp': result.get('timestamp', datetime.now(timezone.utc).isoformat()),
                    'image_filename': os.path.basename(image_path),
                    'actual_class': actual_class,
                    'predicted_class': predicted_class,
                    'confidence_score': confidence_score
                }

                self.predictions.append(prediction_record)
                successful += 1

                # Progress indicator
                if (i + 1) % 5 == 0:
                    print(f"   Progress: {i + 1}/{self.daily_predictions} predictions")

                # Small delay between predictions
                sleep_time = random.uniform(self.min_interval, self.max_interval)
                time.sleep(sleep_time)

            except Exception as e:
                print(f"   ❌ Error generating prediction {i+1}: {e}")
                failed += 1

        print()
        print(f"✅ Generation complete:")
        print(f"   Successful: {successful}")
        print(f"   Failed: {failed}")
        print()

        return successful > 0

    def upload_ground_truth(self):
        """
        Upload ground truth data to Domino Data Source for Model Quality monitoring

        Creates a CSV with event_id, actual_class, and timestamp columns for matching
        to predictions captured by DataCaptureClient.
        """
        if not self.predictions:
            print("⚠️  No predictions to upload")
            return False

        if not DATASOURCE_AVAILABLE:
            print("⚠️  DataSourceClient not available - skipping ground truth upload")
            return False

        try:
            print("="*60)
            print("GROUND TRUTH UPLOAD")
            print("="*60)

            # Create ground truth CSV in memory with all required columns
            ground_truth_records = []
            for pred in self.predictions:
                ground_truth_records.append({
                    'event_id': pred['event_id'],
                    'actual_class': pred['actual_class'],
                    'timestamp': pred['timestamp']
                })

            # Write to in-memory CSV
            csv_buffer = io.StringIO()
            if ground_truth_records:
                writer = csv.DictWriter(csv_buffer, fieldnames=['event_id', 'actual_class', 'timestamp'])
                writer.writeheader()
                writer.writerows(ground_truth_records)

            # Convert to bytes for upload
            csv_bytes = csv_buffer.getvalue().encode('utf-8')

            # Upload to Data Source
            print(f"📤 Uploading ground truth to Data Source: {self.datasource_name}")
            print(f"   Records: {len(ground_truth_records)}")
            print(f"   Date: {self.today}")
            print(f"   Model-specific path: {self.ground_truth_prefix}{self.today}.csv")

            # Get Data Source client
            datasource = DataSourceClient().get_datasource(self.datasource_name)

            # Upload to model-specific ground_truth path
            s3_key = f"{self.ground_truth_prefix}{self.today}.csv"

            # Upload using fileobj method
            bytes_buffer = io.BytesIO(csv_bytes)
            datasource.upload_fileobj(s3_key, bytes_buffer)

            print(f"✅ Ground truth uploaded successfully")
            print(f"   S3 Key: {s3_key}")
            print(f"   Size: {len(csv_bytes)} bytes")
            print("="*60)
            print()

            return True

        except Exception as e:
            print(f"❌ Ground truth upload failed: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_summary(self):
        """Generate execution summary"""
        if not self.predictions:
            return

        # Calculate statistics
        class_counts = {}
        avg_confidence = 0
        correct_predictions = 0

        for pred in self.predictions:
            cls = pred['predicted_class']
            class_counts[cls] = class_counts.get(cls, 0) + 1
            avg_confidence += pred['confidence_score']

            if pred['actual_class'] == pred['predicted_class']:
                correct_predictions += 1

        avg_confidence /= len(self.predictions)
        accuracy = correct_predictions / len(self.predictions)

        print("="*60)
        print("SUMMARY")
        print("="*60)
        print(f"Date: {self.today}")
        print(f"Model ID: {self.model_id}")
        print(f"Total Predictions: {len(self.predictions)}")
        print(f"Simulated Accuracy: {accuracy:.1%}")
        print(f"Average Confidence: {avg_confidence:.1%}")
        print()
        print("Class Distribution:")
        for cls in ['plane', 'ship', 'seafloor']:
            count = class_counts.get(cls, 0)
            pct = count / len(self.predictions) * 100 if len(self.predictions) > 0 else 0
            print(f"   {cls}: {count} ({pct:.1f}%)")
        print()
        print(f"📁 Ground truth uploaded to S3: {self.ground_truth_prefix}{self.today}.csv")
        print("="*60)

    def run(self):
        """Main execution"""
        try:
            # Generate predictions
            success = self.generate_predictions()

            if not success:
                print("❌ No predictions generated")
                return 1

            # Upload ground truth to Data Source
            gt_uploaded = self.upload_ground_truth()

            # Show summary
            self.generate_summary()

            if gt_uploaded:
                print("✅ Ground truth uploaded to Domino Data Source")
                print(f"   Configure Model Monitor to ingest from: {self.ground_truth_prefix}*.csv")
            else:
                print("⚠️  Ground truth not uploaded - check Data Source configuration")

            return 0

        except Exception as e:
            print(f"❌ Fatal error: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == "__main__":
    # Load configuration
    config = get_config()
    
    # Extract model ID and print summary
    model_id = extract_model_id(config.model_api_url)
    print_config_summary(config, model_id)
    
    # Run monitoring data generation
    generator = MonitoringDataGenerator(config)
    exit_code = generator.run()
    sys.exit(exit_code)