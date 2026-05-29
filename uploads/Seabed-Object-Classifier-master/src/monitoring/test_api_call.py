#!/usr/bin/env python3
"""
Test script to verify Model API is accessible and working
Tests with a single image from the test set
"""

import os
import sys
import base64
import requests
from pathlib import Path

# Import centralized config for adaptive paths
working_dir = os.environ.get('DOMINO_WORKING_DIR', '/mnt')
sys.path.insert(0, working_dir)

from src.data_config import DataConfig
config = DataConfig()

# API Configuration
MODEL_API_URL = "https://pub-sec-demo.domino-eval.com:443/models/68decd84260273614f3974bd/labels/prod/model"
API_TIMEOUT = 60
# Model API token (specific to this deployed model)
MODEL_API_TOKEN = "99x1lplOhvKvmjXPiKvvbdmqFnfITSiK3xktnicmHfWQ0HpRu4RjEV8uSc7mCP02"

# Test image path - use centralized config
TEST_IMAGE = config.test_dataset_path / "plane" / "13.jpg"

def test_api_call():
    """Test single API call"""
    print("="*60)
    print("MODEL API TEST")
    print("="*60)
    print(f"API URL: {MODEL_API_URL}")
    print(f"Test Image: {TEST_IMAGE}")
    print()

    if not TEST_IMAGE.exists():
        print(f"❌ Test image not found: {TEST_IMAGE}")
        return 1

    try:
        print("📤 Sending image to API...")
        print(f"🔐 Using API Token: {MODEL_API_TOKEN[:10]}...{MODEL_API_TOKEN[-10:]}")
        print()

        # Read and encode image as base64
        with open(TEST_IMAGE, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Prepare JSON payload
        payload = {
            'data': {
                'image': image_data
            }
        }

        # Send request with Basic Auth
        response = requests.post(
            MODEL_API_URL,
            json=payload,
            auth=(MODEL_API_TOKEN, MODEL_API_TOKEN),
            timeout=API_TIMEOUT
        )

        print(f"✅ HTTP Status: {response.status_code}")
        print()

        # Check if response is successful
        response.raise_for_status()

        # Parse JSON
        response_data = response.json()

        print("📊 API RESPONSE:")
        print("-"*60)
        for key, value in response_data.items():
            print(f"   {key}: {value}")
        print("-"*60)
        print()

        # Extract result from nested structure
        result = response_data.get('result', response_data)

        # Validate expected fields
        if 'label' in result and 'score' in result:
            print(f"✅ Prediction: {result['label']} ({result['score']:.2%} confidence)")

            if 'event_id' in result:
                print(f"✅ Event ID: {result['event_id']}")
                print("✅ Monitoring is enabled - predictions will be captured")
            else:
                print("⚠️  No event_id - monitoring may not be enabled")

            print()
            print("="*60)
            print("✅ API TEST PASSED")
            print("="*60)
            return 0
        else:
            print(f"❌ Missing required fields (label/score) in response")
            return 1

    except requests.exceptions.Timeout:
        print(f"❌ API request timeout after {API_TIMEOUT} seconds")
        return 1
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Connection error: {e}")
        print("   Check: Is the API endpoint deployed and accessible?")
        return 1
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP error: {e}")
        print(f"   Response: {response.text}")
        return 1
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = test_api_call()
    exit(exit_code)
