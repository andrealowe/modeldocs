# predict.py

# CRITICAL: NumPy compatibility check must happen BEFORE any other imports
import subprocess
import sys
import os

def ensure_numpy_compatibility():
    """Ensure NumPy compatibility before importing other packages"""
    try:
        import numpy
        if numpy.__version__.startswith('2.'):
            print("⚠️ NumPy 2.x detected - attempting to downgrade for compatibility...")
            
            # Try different installation approaches
            install_commands = [
                [sys.executable, "-m", "pip", "install", "numpy<2", "--force-reinstall", "--no-deps"],
                [sys.executable, "-m", "pip", "install", "numpy==1.24.3", "--force-reinstall"],
                [sys.executable, "-m", "pip", "install", "numpy<2", "--user", "--force-reinstall"]
            ]
            
            success = False
            for cmd in install_commands:
                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                    success = True
                    break
                except subprocess.CalledProcessError:
                    continue
            
            if success:
                print("✅ NumPy downgraded - please restart the application")
                # Force restart by exiting
                os._exit(0)
            else:
                print("❌ Could not downgrade NumPy automatically")
                print("💡 Please manually run: pip install 'numpy<2' --force-reinstall")
                
    except ImportError:
        # Install NumPy if not present
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "numpy<2"],
                capture_output=True,
                text=True,
                check=True
            )
        except Exception:
            pass  # Continue and let other imports handle it
    except Exception as e:
        print(f"Warning: Could not check NumPy compatibility: {e}")

# Run compatibility check first
ensure_numpy_compatibility()

# Now safe to import other packages
from PIL import Image
from transformers import pipeline
import uuid
import base64
import io
from datetime import datetime, timezone

# Import Domino Model Monitoring DataCaptureClient
try:
    from domino_data_capture.data_capture_client import DataCaptureClient
    import numpy as np

    # Initialize DataCaptureClient for model monitoring
    # Features: Sonar image characteristics
    feature_names = [
        'image_filename',           # File identifier
        'image_size_kb',           # File size
        'image_width',             # Image dimensions
        'image_height',            # Image dimensions
        'mean_brightness',         # Average pixel intensity (0-255)
        'std_brightness',          # Brightness variation
        'contrast',                # Difference between max and min intensity
        'edge_density',            # Proportion of edge pixels (feature detection)
        'dark_pixel_ratio',        # Ratio of very dark pixels (<50)
        'bright_pixel_ratio',      # Ratio of very bright pixels (>200)
        'snr_estimate'             # Signal-to-noise ratio estimate
    ]
    predict_names = ['predicted_class', 'confidence_score']

    data_capture_client = DataCaptureClient(feature_names, predict_names)
    MONITORING_ENABLED = True
    print("✅ Model Monitoring enabled - predictions will be captured")
    print(f"   Tracking {len(feature_names)} sonar image features")
except ImportError:
    data_capture_client = None
    MONITORING_ENABLED = False
    print("ℹ️  Model Monitoring disabled - domino_data_capture not available")
except Exception as e:
    data_capture_client = None
    MONITORING_ENABLED = False
    print(f"⚠️  Model Monitoring initialization failed: {e}")

# Handle model path with fallbacks
def get_model_path():
    """Get model path with fallback options - handles git-based and file-based projects"""
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

        for alt_path in alternative_paths:
            if os.path.exists(alt_path):
                return alt_path

        # If no model found, raise error
        raise FileNotFoundError(f"Model not found. Checked paths: {[model_path] + alternative_paths}")

    return model_path

# Initialize classifier with error handling
try:
    model_path = get_model_path()
    classifier = pipeline(
        "image-classification",
        model=model_path,
        device=0 if int(os.getenv("DOMINO_TASK_GPU_COUNT", "0")) > 0 else -1
    )
except Exception as e:
    print(f"Error loading model: {e}")
    classifier = None


def extract_sonar_features(img, image_path=None):
    """
    Extract sonar-specific image features for monitoring

    Args:
        img: PIL Image object
        image_path: Optional file path for metadata

    Returns:
        dict: Dictionary of feature values
    """
    try:
        # Convert to numpy array for analysis
        img_array = np.array(img)

        # Handle RGB by converting to grayscale for sonar analysis
        if len(img_array.shape) == 3:
            # Convert RGB to grayscale using standard weights
            img_gray = np.dot(img_array[...,:3], [0.299, 0.299, 0.114])
        else:
            img_gray = img_array

        # Basic dimensions
        height, width = img_gray.shape[:2]

        # Brightness statistics (0-255 range)
        mean_brightness = float(np.mean(img_gray))
        std_brightness = float(np.std(img_gray))

        # Contrast (dynamic range)
        contrast = float(np.max(img_gray) - np.min(img_gray))

        # Edge density (approximate using gradient magnitude)
        # Simple Sobel-like edge detection
        dy, dx = np.gradient(img_gray)
        edge_magnitude = np.sqrt(dx**2 + dy**2)
        edge_threshold = np.percentile(edge_magnitude, 90)  # Top 10% are "edges"
        edge_density = float(np.sum(edge_magnitude > edge_threshold) / edge_magnitude.size)

        # Dark and bright pixel ratios
        dark_pixel_ratio = float(np.sum(img_gray < 50) / img_gray.size)
        bright_pixel_ratio = float(np.sum(img_gray > 200) / img_gray.size)

        # Signal-to-noise ratio estimate
        # SNR = mean / std (simplified estimate)
        snr_estimate = float(mean_brightness / (std_brightness + 1e-6))

        # File metadata
        image_filename = "unknown"
        image_size_kb = 0.0

        if image_path and isinstance(image_path, str) and not image_path.startswith('data:'):
            image_filename = os.path.basename(image_path)
            try:
                image_size_kb = os.path.getsize(image_path) / 1024.0
            except:
                pass

        return {
            'image_filename': image_filename,
            'image_size_kb': round(image_size_kb, 2),
            'image_width': int(width),
            'image_height': int(height),
            'mean_brightness': round(mean_brightness, 2),
            'std_brightness': round(std_brightness, 2),
            'contrast': round(contrast, 2),
            'edge_density': round(edge_density, 4),
            'dark_pixel_ratio': round(dark_pixel_ratio, 4),
            'bright_pixel_ratio': round(bright_pixel_ratio, 4),
            'snr_estimate': round(snr_estimate, 2)
        }

    except Exception as e:
        # Return default values if feature extraction fails
        return {
            'image_filename': 'unknown',
            'image_size_kb': 0.0,
            'image_width': 0,
            'image_height': 0,
            'mean_brightness': 0.0,
            'std_brightness': 0.0,
            'contrast': 0.0,
            'edge_density': 0.0,
            'dark_pixel_ratio': 0.0,
            'bright_pixel_ratio': 0.0,
            'snr_estimate': 0.0
        }


def predict(image):
    """
    Decode a base64-encoded image and return the top class & probability.
    Captures prediction data for Domino Model Monitoring if enabled.

    Args:
        image (str or dict): Path to image file, base64 string, or dict with 'image' key

    Returns:
        dict: {
            "label": "<class name>",
            "score": <probability>,
            "event_id": "<uuid>" (if monitoring enabled)
        }
    """

    # Check if classifier is available
    if classifier is None:
        return {"error": "Model not loaded. Please check model availability."}

    # Handle different input formats
    try:
        # If input is a dict (from API), extract the image data
        if isinstance(image, dict):
            image_data = image.get('image', '')
        else:
            image_data = image

        # Check if it's a base64 string or file path
        if isinstance(image_data, str) and (image_data.startswith('data:image') or len(image_data) > 500):
            # It's a base64 string
            # Remove data URI prefix if present
            if image_data.startswith('data:'):
                image_data = image_data.split(',')[1]

            # Decode base64
            image_bytes = base64.b64decode(image_data)
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            image_path = None  # No file path for base64
        else:
            # It's a file path
            img = Image.open(image_data).convert("RGB")
            image_path = image_data
    except Exception as e:
        return {"error": f"Invalid image data: {e}"}

    try:
        # Run the classifier and get all class probabilities
        all_results = classifier(img, top_k=None)  # Get all classes

        # Top prediction
        result = all_results[0]
        predicted_class = result["label"]
        confidence_score = float(result["score"])

        # Extract probabilities for all classes in consistent order (alphabetical)
        class_order = ['plane', 'ship', 'seafloor']
        class_probs = {r['label']: float(r['score']) for r in all_results}
        prediction_probabilities = [class_probs.get(cls, 0.0) for cls in class_order]

        # Generate unique event ID and timestamp for all responses
        event_id = str(uuid.uuid4())
        event_time = datetime.now(timezone.utc).isoformat()

        response = {
            "label": predicted_class,
            "score": confidence_score,
            "probabilities": prediction_probabilities,  # [plane, ship, seafloor]
            "event_id": event_id,
            "timestamp": event_time
        }

        # Capture prediction for Model Monitoring (using same event_id and timestamp)
        if MONITORING_ENABLED and data_capture_client is not None:
            try:
                # Extract sonar image features
                sonar_features = extract_sonar_features(img, image_path)

                # Feature values (sonar image characteristics)
                feature_values = [
                    sonar_features['image_filename'],
                    sonar_features['image_size_kb'],
                    sonar_features['image_width'],
                    sonar_features['image_height'],
                    sonar_features['mean_brightness'],
                    sonar_features['std_brightness'],
                    sonar_features['contrast'],
                    sonar_features['edge_density'],
                    sonar_features['dark_pixel_ratio'],
                    sonar_features['bright_pixel_ratio'],
                    sonar_features['snr_estimate']
                ]

                # Prediction values (model output)
                predict_values = [predicted_class, confidence_score]

                # Capture prediction with probabilities for AUC-ROC and log loss
                data_capture_client.capturePrediction(
                    feature_values,
                    predict_values,
                    event_id=event_id,
                    timestamp=event_time,
                    prediction_probability=prediction_probabilities  # [plane, ship, seafloor]
                )

            except Exception as monitor_error:
                # Don't fail prediction if monitoring fails
                print(f"⚠️  Monitoring capture failed: {monitor_error}")

        return response

    except Exception as e:
        return {"error": f"Prediction failed: {e}"}


def main():
    """
    Command-line interface for testing predictions

    Usage:
        python predict.py <image_path>
        python predict.py <image_path> --verbose
        python predict.py <image_path> --json
    """
    import argparse
    import json

    parser = argparse.ArgumentParser(
        description='Seabed Object Detection - Test sonar image classification',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python predict.py /path/to/image.png
  python predict.py /path/to/image.png --verbose
  python predict.py /path/to/image.png --json

Classes:
  - plane: Submerged aircraft
  - ship: Submerged vessels
  - seafloor: Empty seabed terrain
        '''
    )

    parser.add_argument('image_path', help='Path to sonar image file')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Show detailed output including features')
    parser.add_argument('--json', '-j', action='store_true',
                       help='Output raw JSON response')

    args = parser.parse_args()

    # Check if image exists
    if not os.path.exists(args.image_path):
        print(f"❌ Error: Image not found: {args.image_path}")
        sys.exit(1)

    # Run prediction
    print(f"🔍 Analyzing: {args.image_path}")
    result = predict(args.image_path)

    # Handle errors
    if "error" in result:
        print(f"❌ Error: {result['error']}")
        sys.exit(1)

    # Output results
    if args.json:
        # Raw JSON output
        print(json.dumps(result, indent=2))
    elif args.verbose:
        # Detailed output
        print("\n" + "="*60)
        print("PREDICTION RESULTS")
        print("="*60)
        print(f"📷 Image: {os.path.basename(args.image_path)}")
        print(f"🎯 Predicted Class: {result['label'].upper()}")
        print(f"📊 Confidence: {result['score']:.2%}")

        if 'event_id' in result:
            print(f"🔗 Event ID: {result['event_id']}")
            print(f"⏰ Timestamp: {result['timestamp']}")
            print("✅ Prediction captured for Model Monitoring")

        # Extract and display features
        try:
            img = Image.open(args.image_path).convert("RGB")
            features = extract_sonar_features(img, args.image_path)

            print("\n" + "-"*60)
            print("SONAR IMAGE FEATURES")
            print("-"*60)
            print(f"📐 Dimensions: {features['image_width']}x{features['image_height']} px")
            print(f"💾 File Size: {features['image_size_kb']:.2f} KB")
            print(f"💡 Mean Brightness: {features['mean_brightness']:.2f}")
            print(f"📈 Contrast: {features['contrast']:.2f}")
            print(f"🔲 Edge Density: {features['edge_density']:.4f}")
            print(f"🌑 Dark Pixel Ratio: {features['dark_pixel_ratio']:.4f}")
            print(f"🌕 Bright Pixel Ratio: {features['bright_pixel_ratio']:.4f}")
            print(f"📡 SNR Estimate: {features['snr_estimate']:.2f}")
        except Exception as e:
            print(f"\n⚠️  Could not extract features: {e}")

        print("="*60)
    else:
        # Simple output with features
        confidence_emoji = "🟢" if result['score'] > 0.9 else "🟡" if result['score'] > 0.7 else "🟠"
        print(f"{confidence_emoji} {result['label'].upper()} ({result['score']:.2%} confidence)")

        # Extract and display features in compact format
        try:
            img = Image.open(args.image_path).convert("RGB")
            features = extract_sonar_features(img, args.image_path)

            print(f"   📐 {features['image_width']}x{features['image_height']}px | "
                  f"💡 Brightness: {features['mean_brightness']:.1f} | "
                  f"📈 Contrast: {features['contrast']:.1f}")
            print(f"   🔲 Edges: {features['edge_density']:.4f} | "
                  f"🌑 Dark: {features['dark_pixel_ratio']:.2%} | "
                  f"🌕 Bright: {features['bright_pixel_ratio']:.2%} | "
                  f"📡 SNR: {features['snr_estimate']:.2f}")
        except Exception as e:
            pass  # Skip features if extraction fails

        if 'event_id' in result:
            print(f"   🔗 Event ID: {result['event_id']}")


if __name__ == "__main__":
    main()
