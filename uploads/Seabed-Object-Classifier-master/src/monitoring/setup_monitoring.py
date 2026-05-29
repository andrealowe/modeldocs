#!/usr/bin/env python3
"""
Setup Script for Seabed Monitoring Configuration

Interactive setup to configure monitoring for any Domino project.
Prompts user for required values and creates the unified config file.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any

def get_user_input(prompt: str, default: str = None, required: bool = True) -> str:
    """Get user input with optional default value"""
    if default:
        full_prompt = f"{prompt} [{default}]: "
    else:
        full_prompt = f"{prompt}: "
    
    while True:
        value = input(full_prompt).strip()
        
        if value:
            return value
        elif default:
            return default
        elif not required:
            return ""
        else:
            print("This field is required. Please enter a value.")

def extract_model_id_from_url(url: str) -> str:
    """Extract model ID from API endpoint URL"""
    # Example: https://se-demo.domino.tech:443/models/68eda1eb2500c81ff5fed203/latest/model
    try:
        parts = url.split('/models/')
        if len(parts) > 1:
            model_part = parts[1].split('/')[0]
            return model_part
    except:
        pass
    return ""

def create_monitoring_config() -> Dict[str, Any]:
    """Interactive configuration creation with verification"""
    print("🔧 SEABED MONITORING SETUP")
    print("=" * 50)
    print("This will create a unified configuration for all monitoring scripts.")
    print()

    while True:
        # Domino Configuration
        print("📍 DOMINO CONFIGURATION")
        print("-" * 30)
        domino_url = get_user_input(
            "Domino base URL (e.g., https://se-demo.domino.tech)",
            "https://se-demo.domino.tech"
        ).rstrip('/')

        # Model API Configuration
        print("\n🔗 MODEL API CONFIGURATION")
        print("-" * 30)
        model_api_url = get_user_input(
            "Model API endpoint URL",
            "https://se-demo.domino.tech:443/models/68eda1eb2500c81ff5fed203/latest/model"
        )

        # Try to extract model ID from URL
        extracted_api_id = extract_model_id_from_url(model_api_url)
        if extracted_api_id:
            print(f"💡 Detected API model ID: {extracted_api_id}")

        model_api_token = get_user_input(
            "Model API token",
            required=False
        )
        if not model_api_token:
            model_api_token = "REPLACE_WITH_YOUR_MODEL_API_TOKEN"

        # Model Monitor Configuration
        print("\n📊 MODEL MONITOR CONFIGURATION")
        print("-" * 30)
        model_monitor_id = get_user_input(
            "Model Monitor ID",
            "68efe5dcdbdc7bf9bad685b8"
        )

        # Data Sources
        print("\n💾 DATA SOURCE CONFIGURATION")
        print("-" * 30)
        ground_truth_ds = get_user_input(
            "Ground truth data source name",
            "ground-truth-seabed-classifier"
        )

        # Create configuration
        config = {
            "_comment": "Unified Monitoring Configuration",
            "_description": "Single config file for all seabed monitoring scripts",

            "domino": {
                "base_url": domino_url,
                "user_api_key_env": "DOMINO_USER_API_KEY"
            },

            "model_api": {
                "endpoint_url": model_api_url,
                "token": model_api_token,
                "timeout": 60
            },

            "model_monitor": {
                "model_id": model_monitor_id,
                "prediction_model_id": model_monitor_id
            },

            "data_sources": {
                "ground_truth": ground_truth_ds
            },

            "monitoring": {
                "daily_predictions": 30,
                "min_interval_seconds": 1,
                "max_interval_seconds": 5,
                "default_hours_back": 24
            },

            "paths": {
                "ground_truth_prefix": "ground_truth",
                "config_backup_dir": "/mnt/artifacts/monitoring",
                "training_data_dir": "training_data"
            },

            "model_classes": {
                "labels": ["plane", "ship", "seafloor"],
                "label_map": {"plane": 0, "ship": 1, "seafloor": 2}
            }
        }

        # Display configuration for verification
        print("\n" + "=" * 50)
        print("📋 CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"🌐 Domino URL: {domino_url}")
        print(f"🔗 Model API URL: {model_api_url}")

        # Mask token for display
        if model_api_token and model_api_token != "REPLACE_WITH_YOUR_MODEL_API_TOKEN":
            masked_token = f"****...{model_api_token[-4:]}" if len(model_api_token) > 4 else "****"
            print(f"🔑 API Token: {masked_token}")
        else:
            print(f"🔑 API Token: [NOT SET - will need to configure later]")

        print(f"📊 Model Monitor ID: {model_monitor_id}")
        print(f"💾 Ground Truth Data Source: {ground_truth_ds}")
        print("=" * 50)

        # Ask for confirmation
        confirmation = input("\n✅ Is this configuration correct? (yes/no/cancel): ").strip().lower()

        if confirmation in ['yes', 'y']:
            return config
        elif confirmation in ['cancel', 'c', 'quit', 'q']:
            print("\n❌ Setup cancelled by user.")
            return None
        else:
            print("\n🔄 Let's start over...\n")
            continue

def save_config(config: Dict[str, Any]) -> Path:
    """Save configuration to artifacts directory"""
    # Always save to artifacts directory to avoid syncing to git
    config_file = Path('/mnt/artifacts/monitoring/model_config.json')
    
    # Ensure directory exists
    config_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Save config
    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    
    print(f"\n✅ Configuration saved to:")
    print(f"   📁 Config: {config_file}")
    
    return config_file

def main():
    """Main setup function"""
    try:
        # Create configuration interactively
        config = create_monitoring_config()

        # Handle cancellation
        if config is None:
            sys.exit(1)

        # Save configuration
        config_file = save_config(config)

        print("\n🎉 SETUP COMPLETE!")
        print("=" * 50)
        print("Your monitoring configuration is ready!")
        print()
        print("📋 NEXT STEPS:")
        step_num = 1
        if config['model_api']['token'] == "REPLACE_WITH_YOUR_MODEL_API_TOKEN":
            print(f"{step_num}. Update the model API token in the config file")
            step_num += 1
        print(f"{step_num}. Run monitoring scripts with:")
        print("   python src/monitoring/upload_ground_truth_config.py")
        print("   python src/monitoring/generate_monitoring_data.py")
        print()
        print("🔧 Configuration summary:")
        print(f"   🌐 Domino URL: {config['domino']['base_url']}")
        print(f"   📊 Monitor ID: {config['model_monitor']['model_id']}")
        print(f"   💾 Ground Truth Data Source: {config['data_sources']}")

    except KeyboardInterrupt:
        print("\n\n❌ Setup cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()