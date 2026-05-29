#!/usr/bin/env python3
"""
Unified Configuration Loader for Seabed Monitoring Scripts

Provides centralized configuration management for all monitoring scripts.
Supports both git-based and file-based Domino projects.
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional


class MonitoringConfig:
    """Unified configuration manager for seabed monitoring scripts"""
    
    def __init__(self, config_file: Optional[str] = None):
        """
        Initialize configuration loader.
        
        Args:
            config_file: Optional path to config file. If None, auto-detects location.
        """
        self.config_file = self._find_config_file(config_file)
        self.config = self._load_config()
        self._validate_config()
    
    def _find_config_file(self, config_file: Optional[str] = None) -> Path:
        """Find the configuration file location"""
        if config_file:
            return Path(config_file)
        
        # Auto-detect based on project type
        working_dir = os.environ.get('DOMINO_WORKING_DIR', '/mnt')
        is_git_based = (working_dir == '/mnt/code')
        
        # Always use artifacts directory to avoid syncing config to git
        candidates = [
            Path('/mnt/artifacts/monitoring/model_config.json')
        ]
        
        for candidate in candidates:
            if candidate.exists():
                return candidate
        
        # Default to first candidate if none exist
        return candidates[0]
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file"""
        try:
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_file}\n"
                f"Please create the config file using the template."
            )
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file {self.config_file}: {e}")
    
    def _validate_config(self):
        """Validate required configuration fields"""
        required_sections = ['domino', 'model_api', 'model_monitor', 'data_sources']
        missing_sections = [section for section in required_sections 
                          if section not in self.config]
        
        if missing_sections:
            raise ValueError(f"Missing required config sections: {missing_sections}")
        
        # Check for placeholder values
        if 'REPLACE_WITH_YOUR_MODEL_API_TOKEN' in str(self.config):
            print("⚠️  Warning: Model API token not configured (using placeholder)")
    
    # Domino Configuration
    @property
    def domino_base_url(self) -> str:
        """Domino base URL (e.g., https://se-demo.domino.tech)"""
        return self.config['domino']['base_url'].rstrip('/')
    
    @property
    def domino_api_key(self) -> str:
        """Domino User API Key (from environment variable)"""
        env_var = self.config['domino'].get('user_api_key_env', 'DOMINO_USER_API_KEY')
        api_key = os.environ.get(env_var)
        if not api_key:
            raise ValueError(f"Domino API key not found in environment variable: {env_var}")
        return api_key
    
    # Model API Configuration
    @property
    def model_api_url(self) -> str:
        """Model API endpoint URL"""
        return self.config['model_api']['endpoint_url']
    
    @property
    def model_api_token(self) -> str:
        """Model API authentication token"""
        return self.config['model_api']['token']
    
    @property
    def model_api_timeout(self) -> int:
        """Model API request timeout in seconds"""
        return self.config['model_api'].get('timeout', 60)
    
    # Model Monitor Configuration
    @property
    def model_monitor_id(self) -> str:
        """Model Monitor ID for API registration"""
        return self.config['model_monitor']['model_id']
    
    @property
    def prediction_model_id(self) -> str:
        """Model ID from prediction data (for file paths)"""
        return self.config['model_monitor']['prediction_model_id']
    
    # Data Source Configuration
    @property
    def ground_truth_datasource(self) -> str:
        """Ground truth S3 data source name"""
        return self.config['data_sources']['ground_truth']

    # Monitoring Configuration
    @property
    def daily_predictions(self) -> int:
        """Number of predictions to generate daily"""
        return self.config['monitoring'].get('daily_predictions', 30)
    
    @property
    def min_interval_seconds(self) -> int:
        """Minimum interval between predictions"""
        return self.config['monitoring'].get('min_interval_seconds', 1)
    
    @property
    def max_interval_seconds(self) -> int:
        """Maximum interval between predictions"""
        return self.config['monitoring'].get('max_interval_seconds', 5)
    
    @property
    def default_hours_back(self) -> int:
        """Default hours back for file discovery"""
        return self.config['monitoring'].get('default_hours_back', 24)
    
    # Path Configuration
    @property
    def ground_truth_prefix(self) -> str:
        """Ground truth file path prefix"""
        return self.config['paths'].get('ground_truth_prefix', 'ground_truth')
    
    @property
    def config_backup_dir(self) -> str:
        """Configuration backup directory"""
        return self.config['paths'].get('config_backup_dir', '/mnt/artifacts/monitoring')
    
    @property
    def training_data_dir(self) -> str:
        """Training data directory name"""
        return self.config['paths'].get('training_data_dir', 'training_data')
    
    # Model Classes Configuration
    @property
    def class_labels(self) -> list:
        """Model class labels"""
        return self.config['model_classes']['labels']
    
    @property
    def label_map(self) -> dict:
        """Class name to ID mapping"""
        return self.config['model_classes']['label_map']
    
    # Computed Properties
    @property
    def model_monitor_api_url(self) -> str:
        """Model Monitor API base URL"""
        return f"{self.domino_base_url}/model-monitor/v2/api"
    
    @property
    def ground_truth_file_path(self, date_str: str) -> str:
        """Generate ground truth file path for a specific date"""
        return f"{self.ground_truth_prefix}/{self.prediction_model_id}/{date_str}.csv"
    
    def get_ground_truth_file_path(self, date_str: str) -> str:
        """Generate ground truth file path for a specific date"""
        return f"{self.ground_truth_prefix}/{self.prediction_model_id}/{date_str}.csv"
    
    # Utility Methods
    def print_config_summary(self):
        """Print configuration summary for debugging"""
        print("🔧 MONITORING CONFIGURATION SUMMARY")
        print("=" * 50)
        print(f"📍 Config File: {self.config_file}")
        print(f"🌐 Domino URL: {self.domino_base_url}")
        print(f"🔗 Model API: {self.model_api_url}")
        print(f"📊 Monitor ID: {self.model_monitor_id}")
        print(f"🔢 Prediction ID: {self.prediction_model_id}")
        print(f"💾 Ground Truth DS: {self.ground_truth_datasource}")
        print(f"🏷️  Classes: {self.class_labels}")
        print("=" * 50)
    
    def save_backup_config(self):
        """Save a backup copy of config to artifacts directory"""
        backup_dir = Path(self.config_backup_dir)
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        backup_file = backup_dir / "model_config_backup.json"
        with open(backup_file, 'w') as f:
            json.dump(self.config, f, indent=2)
        
        print(f"💾 Config backup saved to: {backup_file}")


# Global config instance (lazy loaded)
_config_instance = None

def get_config(config_file: Optional[str] = None) -> MonitoringConfig:
    """
    Get the global configuration instance.
    
    Args:
        config_file: Optional path to config file (only used on first call)
        
    Returns:
        MonitoringConfig instance
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = MonitoringConfig(config_file)
    return _config_instance


def reload_config(config_file: Optional[str] = None) -> MonitoringConfig:
    """
    Force reload the configuration (useful for testing).
    
    Args:
        config_file: Optional path to config file
        
    Returns:
        New MonitoringConfig instance
    """
    global _config_instance
    _config_instance = MonitoringConfig(config_file)
    return _config_instance


if __name__ == "__main__":
    """Test the configuration loader"""
    try:
        config = get_config()
        config.print_config_summary()
        print("\n✅ Configuration loaded successfully!")
    except Exception as e:
        print(f"❌ Configuration error: {e}")