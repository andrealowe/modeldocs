"""
Data Configuration - Environment adaptive paths
Shared configuration for dataset paths across different Domino environments
"""

import os
from pathlib import Path


class DataConfig:
    """Centralized configuration for dataset paths across different environments"""

    def __init__(self):
        self.domino_datasets_dir = os.environ.get('DOMINO_DATASETS_DIR', '/mnt/data')
        self.domino_project_name = os.environ.get('DOMINO_PROJECT_NAME', 'Seabed-Object-Detection')
        # Use DOMINO_WORKING_DIR - works for both git-based and file-based projects
        # In workspace: /mnt, In Flow tasks: usually /mnt/code for git projects
        self.domino_working_dir = os.environ.get('DOMINO_WORKING_DIR', '/mnt')

        # Determine project type based on DOMINO_WORKING_DIR
        self.is_git_based_project = (self.domino_working_dir == '/mnt/code')

        # Determine the correct base path based on project type
        if self.domino_datasets_dir == '/domino/datasets':
            # File-based project - use local subdirectory
            self.base_data_path = Path(self.domino_datasets_dir) / 'local' / self.domino_project_name
        else:
            # Git-based project - use direct path
            self.base_data_path = Path(self.domino_datasets_dir) / self.domino_project_name

        # Define dataset paths
        self.balanced_dataset_path = self.base_data_path / 'balanced_training_validation_set'
        self.unbalanced_dataset_path = self.base_data_path / 'unbalanced_training_validation_set'
        self.test_dataset_path = self.base_data_path / 'test_set'

        # Backward compatibility - string paths for notebook
        self.train_images_path = self.unbalanced_dataset_path
        self.test_images_path = self.test_dataset_path
        self.train_images = str(self.train_images_path)
        self.test_images = str(self.test_images_path)

        # Model artifacts path - use /mnt/artifacts for git-based projects, /mnt for file-based
        if self.is_git_based_project:
            self.models_base_path = Path('/mnt/artifacts')
        else:
            self.models_base_path = Path('/mnt')

        # Model directory path
        self.model_output_dir = self.models_base_path / 'models' / 'vit_classification_model'

        # Ensure model directory exists
        self.model_output_dir.mkdir(parents=True, exist_ok=True)

        # Dataset classes
        self.classes = ['plane', 'ship', 'seafloor']
        self.label_map = {'plane': 0, 'ship': 1, 'seafloor': 2}
        self.id2label = {0: 'plane', 1: 'ship', 2: 'seafloor'}
        self.label2id = {v: k for k, v in self.id2label.items()}

    def validate_paths(self):
        """Validate that data paths exist and are accessible"""
        issues = []

        if not self.train_images_path.exists():
            issues.append(f"Training data not found: {self.train_images}")
        else:
            # Check for class subdirectories
            for class_name in self.classes:
                class_path = self.train_images_path / class_name
                if not class_path.exists():
                    issues.append(f"Training class directory not found: {class_path}")

        if not self.test_images_path.exists():
            issues.append(f"Test data not found: {self.test_images}")
        else:
            # Check for class subdirectories
            for class_name in self.classes:
                class_path = self.test_images_path / class_name
                if not class_path.exists():
                    issues.append(f"Test class directory not found: {class_path}")

        return issues

    def print_config(self):
        """Print current configuration for debugging"""
        print("📁 DATA CONFIGURATION")
        print("=" * 50)
        print(f"📂 Project: {self.domino_project_name}")
        print(f"🏠 Working Dir: {self.domino_working_dir}")
        print(f"📊 Base Data Path: {self.base_data_path}")
        print(f"🚂 Training Data: {self.train_images}")
        print(f"🧪 Test Data: {self.test_images}")
        print(f"💾 Model Output: {self.model_output_dir}")
        print(f"🏷️  Classes: {self.classes}")
        print("=" * 50)

        # Validate paths
        issues = self.validate_paths()
        if issues:
            print("\n⚠️  PATH VALIDATION ISSUES:")
            for issue in issues:
                print(f"   ❌ {issue}")
        else:
            print("\n✅ All paths validated successfully!")
