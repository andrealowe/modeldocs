#!/usr/bin/env python3
"""
Seabed Object Classification - Model Training Script
Trains Vision Transformer model with MLflow experiment tracking and model registry

Usage:
    python train_model.py                    # Train with default settings
    python train_model.py --epochs 10        # Custom epochs
    python train_model.py --batch-size 32    # Custom batch size
    python train_model.py --no-gpu           # Force CPU training
"""

import os
import sys
import time
import argparse
import warnings
from datetime import datetime
from pathlib import Path

import torch
import numpy as np
from PIL import Image
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision.transforms import (
    CenterCrop, Compose, Normalize, RandomResizedCrop,
    RandomHorizontalFlip, RandomVerticalFlip, ColorJitter,
    RandomRotation, RandomAffine, GaussianBlur, Resize, ToTensor
)

# Import data_config - robust path resolution for different execution contexts
current_dir = Path(__file__).parent
src_paths = [
    str(current_dir),          # Same directory (src/)
    str(current_dir.parent),   # Parent directory (root)
    '/mnt/code/src',           # Git-based project absolute path
    '/mnt/src',                # File-based project absolute path
    '/mnt/code',               # Git-based project root
    '/mnt',                    # File-based project root
]
for src_path in src_paths:
    if src_path not in sys.path and Path(src_path).exists():
        sys.path.insert(0, src_path)

from data_config import DataConfig

# Suppress warnings
warnings.filterwarnings('ignore')

# HuggingFace imports
from transformers import (
    AutoImageProcessor,
    AutoModelForImageClassification,
    TrainingArguments,
    Trainer,
    DefaultDataCollator
)

# MLflow imports
import mlflow
import mlflow.pytorch
from mlflow.tracking import MlflowClient

# Evaluation imports
from sklearn.metrics import (
    accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
    matthews_corrcoef,
    roc_auc_score
)
import evaluate

# Optuna imports for hyperparameter optimization
import optuna


class BalancedImageDataset(Dataset):
    """
    Custom Dataset for balanced image classification with class weighting
    """
    def __init__(self, root_dir, transform=None, label_map=None):
        self.root_dir = root_dir
        self.transform = transform
        self.image_paths = []
        self.labels = []
        self.class_counts = {}
        self.label_map = label_map

        # Collect all image paths and labels
        for class_name, label in self.label_map.items():
            class_dir = os.path.join(self.root_dir, class_name)
            if os.path.isdir(class_dir):
                img_files = [f for f in os.listdir(class_dir)
                           if f.endswith(('.png', '.jpg', '.jpeg'))]

                self.class_counts[class_name] = len(img_files)
                self.image_paths.extend([os.path.join(class_dir, f) for f in img_files])
                self.labels.extend([label] * len(img_files))

        # Print class distribution
        total_images = len(self.labels)
        print(f"\n📊 Dataset: {Path(root_dir).name}")
        for class_name, count in self.class_counts.items():
            pct = (count / total_images) * 100 if total_images > 0 else 0
            print(f"   • {class_name:<10}: {count:4d} images ({pct:5.1f}%)")

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        label = self.labels[idx]

        try:
            image = Image.open(img_path).convert('RGB')
        except Exception as e:
            print(f"⚠️  Error loading {img_path}: {e}")
            image = Image.new('RGB', (224, 224), (0, 0, 0))

        if self.transform:
            image = self.transform(image)

        return {
            "pixel_values": image,
            "labels": torch.tensor(label, dtype=torch.long)
        }

    def get_class_weights(self):
        """Calculate class weights for balanced sampling"""
        class_counts = [0] * len(self.label_map)
        for label in self.labels:
            class_counts[label] += 1

        total_samples = len(self.labels)
        class_weights = [total_samples / (len(self.label_map) * count)
                        for count in class_counts]

        print(f"\n⚖️  Class Weights for Balanced Sampling:")
        for class_name, weight in zip(self.label_map.keys(), class_weights):
            print(f"   • {class_name:<10}: {weight:.3f}")

        return class_weights


def compute_metrics(eval_pred):
    """Compute detailed metrics including per-class performance and advanced metrics"""
    accuracy_metric = evaluate.load("accuracy")

    logits, labels = eval_pred
    predictions = np.argmax(logits, axis=1)

    # Apply softmax to get probabilities for AUC-ROC
    from scipy.special import softmax
    probabilities = softmax(logits, axis=1)

    # Overall accuracy
    accuracy = accuracy_metric.compute(predictions=predictions, references=labels)["accuracy"]

    # Per-class metrics
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, predictions, average=None, labels=[0, 1, 2], zero_division=0
    )

    # Macro and weighted averages
    precision_macro, recall_macro, f1_macro, _ = precision_recall_fscore_support(
        labels, predictions, average='macro', zero_division=0
    )
    _, _, f1_weighted, _ = precision_recall_fscore_support(
        labels, predictions, average='weighted', zero_division=0
    )
    _, _, f1_micro, _ = precision_recall_fscore_support(
        labels, predictions, average='micro', zero_division=0
    )

    # Advanced metrics for imbalanced classification
    mcc = matthews_corrcoef(labels, predictions)

    # AUC-ROC (multiclass, one-vs-rest)
    try:
        auc_roc = roc_auc_score(labels, probabilities, multi_class='ovr', average='macro')
    except:
        auc_roc = 0.0

    # Per-class specificity (TN / (TN + FP))
    cm = confusion_matrix(labels, predictions, labels=[0, 1, 2])
    specificities = []
    for i in range(3):
        tn = cm.sum() - (cm[i, :].sum() + cm[:, i].sum() - cm[i, i])
        fp = cm[:, i].sum() - cm[i, i]
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        specificities.append(specificity)

    # Class balance ratio
    class_counts = np.bincount(labels, minlength=3)
    class_balance = (class_counts.min() / class_counts.max()) if class_counts.max() > 0 else 0.0

    metrics = {
        "accuracy": accuracy,
        "precision_macro": precision_macro,
        "recall_macro": recall_macro,
        "f1_macro": f1_macro,
        "f1_weighted": f1_weighted,
        "f1_micro": f1_micro,

        # Advanced metrics
        "matthews_corrcoef": mcc,
        "auc_roc": auc_roc,
        "class_balance_ratio": class_balance,

        # Per-class F1 scores (for model selection)
        "plane_f1": f1[0],
        "ship_f1": f1[1],
        "seafloor_f1": f1[2],

        # Per-class precision
        "plane_precision": precision[0],
        "ship_precision": precision[1],
        "seafloor_precision": precision[2],

        # Per-class recall
        "plane_recall": recall[0],
        "ship_recall": recall[1],
        "seafloor_recall": recall[2],

        # Per-class specificity
        "plane_specificity": specificities[0],
        "ship_specificity": specificities[1],
        "seafloor_specificity": specificities[2],
    }

    return metrics


def setup_transforms(image_processor, is_training=True):
    """Setup image transforms for training or evaluation"""
    normalize = Normalize(mean=image_processor.image_mean, std=image_processor.image_std)
    size = (
        image_processor.size["shortest_edge"]
        if "shortest_edge" in image_processor.size
        else (image_processor.size["height"], image_processor.size["width"])
    )

    if is_training:
        # Enhanced augmentation for training (matches notebook approach)
        return Compose([
            RandomResizedCrop(size, scale=(0.8, 1.0)),
            RandomHorizontalFlip(p=0.5),
            RandomVerticalFlip(p=0.3),
            RandomRotation(degrees=15),
            ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
            RandomAffine(degrees=0, translate=(0.1, 0.1), scale=(0.9, 1.1)),
            GaussianBlur(kernel_size=3, sigma=(0.1, 2.0)),
            ToTensor(),
            normalize,
        ])
    else:
        # Mild augmentation for evaluation (matches notebook approach)
        return Compose([
            RandomResizedCrop(size, scale=(0.9, 1.0)),
            ToTensor(),
            normalize,
        ])


def register_best_model(trainer, config, metrics, training_time, model_output_dir):
    """Register best model with MLflow Model Registry"""
    print("\n" + "="*60)
    print("📝 REGISTERING MODEL TO MLFLOW MODEL REGISTRY")
    print("="*60)

    try:
        # Save model locally
        final_model_path = Path(model_output_dir) / "model"
        final_model_path.mkdir(parents=True, exist_ok=True)

        trainer.save_model(str(final_model_path))
        print(f"✅ Model saved to: {final_model_path}")

        # Log model with MLflow - use user-specific model name (matches notebook)
        user_name = os.environ.get('DOMINO_USER_NAME', 'unknown')
        model_name = f"Seabed-Classifier-{user_name}_ViT_Classification"

        model_info = mlflow.pytorch.log_model(
            pytorch_model=trainer.model,
            artifact_path="model",
            registered_model_name=model_name
        )

        # Get model version and calculate model size
        client = MlflowClient()
        model_versions = client.search_model_versions(f"name='{model_name}'")
        latest_version = max([int(mv.version) for mv in model_versions])

        # Calculate model size
        model_size_bytes = sum(p.numel() * p.element_size() for p in trainer.model.parameters())
        model_size_mb = model_size_bytes / (1024 * 1024)

        # Count total parameters
        total_params = sum(p.numel() for p in trainer.model.parameters())
        trainable_params = sum(p.numel() for p in trainer.model.parameters() if p.requires_grad)

        # Add concise model version tags (top 5 most relevant)
        version_tags = {
            "accuracy": f"{metrics.get('eval_accuracy', 0):.4f}",
            "ship_f1": f"{metrics.get('eval_ship_f1', 0):.4f}",
            "auc_roc": f"{metrics.get('eval_auc_roc', 0):.4f}",
            "training_time_min": f"{training_time:.2f}",
            "dataset": "balanced" if hasattr(config, 'train_images') and 'balanced' in str(config.train_images) else "unbalanced"
        }

        for key, value in version_tags.items():
            client.set_model_version_tag(
                name=model_name,
                version=str(latest_version),
                key=key,
                value=value
            )

        # Add Model Specs tags (Domino-specific for deployment UI)
        model_specs = {
            "mlflow.domino.specs.Model Size": f"{model_size_mb:.1f} MB",
            "mlflow.domino.specs.Parameters": f"{total_params:,}",
            "mlflow.domino.specs.Architecture": "Vision Transformer (ViT-Base)",
            "mlflow.domino.specs.Input Resolution": "224x224"
        }

        for key, value in model_specs.items():
            client.set_registered_model_tag(model_name, key, value)

        # Update model version description
        client.update_model_version(
            name=model_name,
            version=str(latest_version),
            description=f"ViT model trained on seabed sonar images. "
                       f"Accuracy: {metrics.get('eval_accuracy', 0):.2%}, "
                       f"Ship F1: {metrics.get('eval_ship_f1', 0):.4f}, "
                       f"AUC-ROC: {metrics.get('eval_auc_roc', 0):.4f}"
        )

        print(f"\n✅ Model registered: {model_name} (Version {latest_version})")
        print(f"   📊 Accuracy: {metrics.get('eval_accuracy', 0):.2%}")
        print(f"   🚢 Ship F1: {metrics.get('eval_ship_f1', 0):.4f}")
        print(f"   📈 AUC-ROC: {metrics.get('eval_auc_roc', 0):.4f}")
        print(f"   💾 Model Size: {model_size_mb:.1f} MB")
        print(f"   🔢 Parameters: {total_params:,}")
        print(f"   ⏱️  Training time: {training_time:.2f} minutes")

        return model_info, latest_version

    except Exception as e:
        print(f"❌ Error registering model: {e}")
        return None, None


def suggest_hyperparameters(trial):
    """Define hyperparameter search space for Optuna optimization"""
    return {
        "learning_rate": trial.suggest_loguniform("learning_rate", 1e-5, 1e-4),
        "per_device_train_batch_size": trial.suggest_categorical("per_device_train_batch_size", [8, 16, 32]),
        "num_train_epochs": trial.suggest_int("num_train_epochs", 3, 7),
        "warmup_ratio": trial.suggest_uniform("warmup_ratio", 0.0, 0.3),
        "weight_decay": trial.suggest_loguniform("weight_decay", 1e-3, 1e-1),
        "lr_scheduler_type": trial.suggest_categorical("lr_scheduler_type", ["linear", "cosine", "cosine_with_restarts"]),
        "label_smoothing_factor": trial.suggest_uniform("label_smoothing_factor", 0.0, 0.2),
        "gradient_accumulation_steps": trial.suggest_categorical("gradient_accumulation_steps", [1, 2, 4]),
        "max_grad_norm": trial.suggest_uniform("max_grad_norm", 0.5, 2.0),
        "eval_steps": trial.suggest_categorical("eval_steps", [25, 50, 100]),
    }


def objective(trial, config, device, train_dataset, eval_dataset, image_processor):
    """Objective function for Optuna hyperparameter optimization"""
    print(f"\n🔬 TRIAL {trial.number + 1}")
    print("=" * 50)
    
    # Sample hyperparameters for this trial
    params = suggest_hyperparameters(trial)
    
    # Display trial parameters
    print("Trial parameters:")
    for param, value in params.items():
        print(f"   • {param}: {value}")
    
    # Start MLflow run for this trial
    with mlflow.start_run(run_name=f"enhanced_trial_{trial.number}", nested=True):
        # Log trial parameters
        mlflow.log_params(params)
        mlflow.log_param("trial_number", trial.number)
        
        try:
            # Load model with dropout configuration
            checkpoint = "google/vit-base-patch16-224-in21k"
            from transformers import ViTConfig
            
            model_config = ViTConfig.from_pretrained(checkpoint)
            model_config.num_labels = len(config.classes)
            model_config.id2label = config.id2label
            model_config.label2id = config.label2id
            model_config.hidden_dropout_prob = 0.1
            model_config.attention_probs_dropout_prob = 0.1
            
            model = AutoModelForImageClassification.from_pretrained(
                checkpoint,
                config=model_config,
                ignore_mismatched_sizes=True
            )
            
            # Training arguments with trial parameters
            training_args = TrainingArguments(
                output_dir=str(config.model_output_dir),
                remove_unused_columns=False,
                
                # Trial parameters
                learning_rate=params["learning_rate"],
                per_device_train_batch_size=params["per_device_train_batch_size"],
                num_train_epochs=params["num_train_epochs"],
                warmup_ratio=params["warmup_ratio"],
                weight_decay=params["weight_decay"],
                lr_scheduler_type=params["lr_scheduler_type"],
                label_smoothing_factor=params["label_smoothing_factor"],
                gradient_accumulation_steps=params["gradient_accumulation_steps"],
                max_grad_norm=params["max_grad_norm"],
                eval_steps=params["eval_steps"],
                
                # Fixed parameters
                per_device_eval_batch_size=params["per_device_train_batch_size"] * 2,
                eval_strategy="steps",
                save_strategy="steps",
                save_steps=params["eval_steps"] * 2,
                logging_steps=25,
                logging_first_step=True,
                
                # Model selection
                load_best_model_at_end=True,
                metric_for_best_model="ship_f1",
                greater_is_better=True,
                
                # Performance optimization
                fp16=(device.type == "cuda"),
                dataloader_pin_memory=True,
                dataloader_num_workers=2,
                
                # Minimal logging for trials
                report_to=[],
                push_to_hub=False,
                save_total_limit=1,
                save_only_model=True,
            )
            
            # Create trainer
            trainer = Trainer(
                model=model,
                args=training_args,
                data_collator=DefaultDataCollator(),
                train_dataset=train_dataset,
                eval_dataset=eval_dataset,
                tokenizer=image_processor,
                compute_metrics=compute_metrics,
            )
            
            # Train the model
            trainer.train()
            eval_results = trainer.evaluate()
            
            # Log comprehensive metrics
            metrics_to_log = {
                "accuracy": eval_results.get("eval_accuracy", 0),
                "f1_weighted": eval_results.get("eval_f1_weighted", 0),
                "f1_macro": eval_results.get("eval_f1_macro", 0),
                "f1_micro": eval_results.get("eval_f1_micro", 0),
                "ship_f1": eval_results.get("eval_ship_f1", 0),
                "plane_f1": eval_results.get("eval_plane_f1", 0),
                "seafloor_f1": eval_results.get("eval_seafloor_f1", 0),
                "matthews_corrcoef": eval_results.get("eval_matthews_corrcoef", 0),
                "auc_roc": eval_results.get("eval_auc_roc", 0),
                "precision_macro": eval_results.get("eval_precision_macro", 0),
                "recall_macro": eval_results.get("eval_recall_macro", 0),
            }
            
            mlflow.log_metrics(metrics_to_log)
            
            # Print trial results
            ship_f1 = metrics_to_log['ship_f1']
            print(f"\n📊 Trial {trial.number + 1} Results:")
            print(f"   Ship F1: {ship_f1:.4f}")
            print(f"   Accuracy: {metrics_to_log['accuracy']:.4f}")
            print(f"   F1 Macro: {metrics_to_log['f1_macro']:.4f}")
            
            return ship_f1
            
        except Exception as e:
            print(f"❌ Trial {trial.number + 1} failed: {str(e)}")
            mlflow.log_param("error", str(e))
            mlflow.log_metric("ship_f1", 0.0)
            return 0.0


def optimize_hyperparameters(config, device, train_dataset, eval_dataset, image_processor, n_trials=10):
    """Run Optuna hyperparameter optimization"""
    print("\n" + "="*80)
    print("🔬 OPTUNA HYPERPARAMETER OPTIMIZATION")
    print("="*80)
    print(f"Target: Maximize Ship F1-Score")
    print(f"Trials: {n_trials}")
    print(f"Dataset: {len(train_dataset)} train, {len(eval_dataset)} eval samples")
    print()
    
    # Create Optuna study
    study = optuna.create_study(
        direction="maximize",
        study_name="enhanced_seabed_classification"
    )
    
    # Define objective function with fixed arguments
    def trial_objective(trial):
        return objective(trial, config, device, train_dataset, eval_dataset, image_processor)
    
    # Run optimization
    study.optimize(trial_objective, n_trials=n_trials)
    
    # Results analysis
    best_trial = study.best_trial
    print("\n" + "="*80)
    print("🏆 OPTIMIZATION RESULTS")
    print("="*80)
    print(f"Best Ship F1-Score: {best_trial.value:.4f}")
    print(f"Best Trial Number: {best_trial.number + 1}")
    print()
    print("Best Parameters:")
    for param, value in best_trial.params.items():
        print(f"   • {param}: {value}")
    
    # Parameter importance analysis
    try:
        print("\n📈 PARAMETER IMPORTANCE:")
        importance = optuna.importance.get_param_importances(study)
        for param, imp in sorted(importance.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {param}: {imp:.4f}")
    except Exception as e:
        print(f"⚠️  Parameter importance analysis not available: {e}")
    
    # Trial performance summary
    print(f"\n📊 TRIAL PERFORMANCE SUMMARY:")
    trials = sorted(study.trials, key=lambda t: t.value if t.value else 0, reverse=True)
    for i, trial in enumerate(trials[:5]):  # Top 5 trials
        value = trial.value if trial.value else 0
        print(f"   {i+1}. Trial {trial.number + 1}: {value:.4f}")
    
    return study, best_trial


def train_model(args):
    """Main training function"""
    print("\n" + "="*60)
    print("🚀 SEABED OBJECT CLASSIFICATION - MODEL TRAINING")
    print("="*60)

    start_time = time.time()

    # Initialize configuration
    config = DataConfig()
    config.classes = ['plane', 'ship', 'seafloor']
    config.label_map = {cls: idx for idx, cls in enumerate(config.classes)}
    config.id2label = {idx: cls for idx, cls in enumerate(config.classes)}
    config.label2id = {cls: idx for idx, cls in enumerate(config.classes)}

    # Use unbalanced dataset for training (or specify balanced via args)
    if args.balanced:
        config.train_images = config.balanced_dataset_path
    else:
        config.train_images = config.unbalanced_dataset_path

    config.eval_images = config.test_dataset_path
    # Use model_output_dir from config (handles git-based vs file-based projects)
    model_output_dir = str(config.model_output_dir)

    # Device configuration
    if args.no_gpu:
        device = torch.device("cpu")
        print(f"\n🖥️  Training on: CPU (forced)")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"\n🖥️  Training on: {device}")
        if device.type == "cuda":
            print(f"   GPU: {torch.cuda.get_device_name(0)}")

    # Set MLflow experiment with user name
    user_name = os.environ.get('DOMINO_USER_NAME', 'unknown')
    experiment_name = f"Seabed-Classifier-{user_name}"
    mlflow.set_experiment(experiment_name)

    # Start MLflow run
    with mlflow.start_run(run_name=f"training_{datetime.now().strftime('%Y%m%d_%H%M%S')}"):

        # Log parameters
        mlflow.log_params({
            "model": "google/vit-base-patch16-224-in21k",
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "learning_rate": args.learning_rate,
            "dataset": "balanced" if args.balanced else "unbalanced",
            "device": str(device),
        })

        # Load image processor from enhanced model
        checkpoint = "google/vit-base-patch16-224-in21k"
        print(f"\n📦 Loading image processor from: {checkpoint}")
        image_processor = AutoImageProcessor.from_pretrained(checkpoint)

        # Setup transforms
        train_transforms = setup_transforms(image_processor, is_training=True)
        eval_transforms = setup_transforms(image_processor, is_training=False)

        # Verify Domino Data Source connection
        print("\n🔗 Verifying Domino Data Source connection...")
        try:
            from domino.data_sources import DataSourceClient
            object_store = DataSourceClient().get_datasource("seabed-object-detection")
            objects = object_store.list_objects()
            print(f"   ✅ Connected to 'seabed-object-detection' data source")
            print(f"   📦 First 5 objects: {objects[:5]}")
        except Exception as e:
            print(f"   ⚠️  Data source check failed (non-critical): {e}")

        # Create datasets
        print("\n📂 Loading datasets...")
        train_dataset = BalancedImageDataset(
            root_dir=str(config.train_images),
            transform=train_transforms,
            label_map=config.label_map
        )

        eval_dataset = BalancedImageDataset(
            root_dir=str(config.eval_images),
            transform=eval_transforms,
            label_map=config.label_map
        )

        # Setup balanced sampler
        class_weights = train_dataset.get_class_weights()
        sample_weights = [class_weights[label] for label in train_dataset.labels]
        sampler = WeightedRandomSampler(
            weights=sample_weights,
            num_samples=len(sample_weights),
            replacement=True
        )

        # Load model with dropout configuration
        print(f"\n🤖 Loading model: {checkpoint}")
        from transformers import ViTConfig

        model_config = ViTConfig.from_pretrained(checkpoint)
        model_config.num_labels = len(config.classes)
        model_config.id2label = config.id2label
        model_config.label2id = config.label2id
        model_config.hidden_dropout_prob = 0.1
        model_config.attention_probs_dropout_prob = 0.1

        model = AutoModelForImageClassification.from_pretrained(
            checkpoint,
            config=model_config,
            ignore_mismatched_sizes=True
        )

        # Determine hyperparameters (optimized from notebook's best trial vs original defaults)
        if args.use_defaults:
            # Original defaults for compatibility
            eval_steps, save_steps = 50, 100
            learning_rate = args.learning_rate if args.learning_rate != 7.655e-5 else 5e-5
            num_epochs = args.epochs if args.epochs != 7 else 5
            warmup_ratio, lr_scheduler = 0.1, "cosine"
            weight_decay, max_grad_norm = 0.01, 1.0
            label_smoothing = 0.1
            print("🔧 Using original default hyperparameters")
        else:
            # Optimized hyperparameters from notebook Trial 7
            eval_steps, save_steps = 25, 50
            learning_rate = args.learning_rate
            num_epochs = args.epochs
            warmup_ratio, lr_scheduler = 0.033, "linear"
            weight_decay, max_grad_norm = 0.015, 1.549
            label_smoothing = 0.031
            print("🚀 Using optimized hyperparameters from notebook (Trial 7 - Ship F1: 0.953)")

        # Training arguments 
        training_args = TrainingArguments(
            output_dir=model_output_dir,
            remove_unused_columns=False,

            # Evaluation and saving
            eval_strategy="steps",
            eval_steps=eval_steps,
            save_strategy="steps",
            save_steps=save_steps,

            # Learning parameters
            learning_rate=learning_rate,
            per_device_train_batch_size=args.batch_size,
            gradient_accumulation_steps=2,
            per_device_eval_batch_size=args.batch_size * 2,

            # Training duration
            num_train_epochs=num_epochs,

            # Learning rate scheduling
            warmup_ratio=warmup_ratio,
            lr_scheduler_type=lr_scheduler,

            # Optimization
            weight_decay=weight_decay,
            max_grad_norm=max_grad_norm,

            # Logging
            logging_dir=f"{model_output_dir}/logs",
            logging_strategy="steps",
            logging_steps=25,
            logging_first_step=True,

            # Model selection (prioritize ship F1)
            load_best_model_at_end=True,
            metric_for_best_model="ship_f1",
            greater_is_better=True,

            # Performance optimization
            fp16=(device.type == "cuda"),  # Mixed precision only on GPU
            dataloader_pin_memory=True,
            dataloader_num_workers=2,

            # Reporting
            report_to=[],
            push_to_hub=False,

            # Save settings
            save_total_limit=3,
            save_only_model=True,

            # Regularization
            label_smoothing_factor=label_smoothing,
        )

        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            data_collator=DefaultDataCollator(),
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=image_processor,
            compute_metrics=compute_metrics,
        )

        # Display training configuration
        print("\n" + "="*60)
        print("📋 TRAINING CONFIGURATION")
        print("="*60)
        print(f"   • Model: {checkpoint}")
        print(f"   • Train samples: {len(train_dataset)}")
        print(f"   • Eval samples: {len(eval_dataset)}")
        print(f"   • Epochs: {num_epochs}")
        print(f"   • Batch size: {args.batch_size}")
        print(f"   • Learning rate: {learning_rate}")
        print(f"   • LR scheduler: {lr_scheduler}")
        print(f"   • Warmup ratio: {warmup_ratio}")
        print(f"   • Weight decay: {weight_decay}")
        print(f"   • Max grad norm: {max_grad_norm}")
        print(f"   • Label smoothing: {label_smoothing}")
        print(f"   • Eval steps: {eval_steps}")
        print(f"   • Device: {device}")
        print(f"   • Mixed precision: {training_args.fp16}")
        print(f"   • Balanced sampling: Yes")
        print(f"   • Selection metric: ship_f1")
        print(f"   • Hyperparameters: {'Original defaults' if args.use_defaults else 'Notebook optimized (Trial 7)'}")

        # Train model
        print("\n" + "="*60)
        print("🎯 STARTING TRAINING")
        print("="*60)

        train_start = time.time()
        train_result = trainer.train()
        train_end = time.time()

        training_time_minutes = (train_end - train_start) / 60

        print("\n" + "="*60)
        print(f"✅ TRAINING COMPLETE - Time: {training_time_minutes:.2f} minutes")
        print("="*60)

        # Evaluate final model
        print("\n📊 Evaluating final model...")
        eval_results = trainer.evaluate()

        # Log metrics
        mlflow.log_metrics(eval_results)
        mlflow.log_metric("training_time_minutes", training_time_minutes)

        # Print results
        print("\n" + "="*60)
        print("📈 FINAL RESULTS")
        print("="*60)
        print(f"   Accuracy:      {eval_results['eval_accuracy']:.2%}")
        print(f"   F1 (macro):    {eval_results['eval_f1_macro']:.4f}")
        print(f"\n   Per-Class F1 Scores:")
        print(f"   • Plane:       {eval_results['eval_plane_f1']:.4f}")
        print(f"   • Ship:        {eval_results['eval_ship_f1']:.4f}")
        print(f"   • Seafloor:    {eval_results['eval_seafloor_f1']:.4f}")
        print(f"\n   Training time: {training_time_minutes:.2f} minutes")

        # Register model
        model_info, version = register_best_model(
            trainer, config, eval_results, training_time_minutes, model_output_dir
        )

        total_time = (time.time() - start_time) / 60
        print("\n" + "="*60)
        print(f"🎉 ALL COMPLETE - Total time: {total_time:.2f} minutes")
        print("="*60)

        return eval_results


def run_optimization(args):
    """Run Optuna hyperparameter optimization (matches notebook approach)"""
    # Set MLflow experiment with user name (matches notebook)
    user_name = os.environ.get('DOMINO_USER_NAME', 'unknown')
    experiment_name = f"Seabed-Classifier-{user_name}"
    mlflow.set_experiment(experiment_name)
    
    print(f"📊 MLflow Experiment: {experiment_name}")
    
    # Initialize configuration
    config = DataConfig()
    
    # Determine device
    if args.no_gpu:
        device = torch.device("cpu")
        print("🔧 Using CPU (forced)")
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        print(f"🔧 Using device: {device}")
    
    # Load datasets
    if args.balanced:
        print("⚖️  Using balanced dataset (138 images)")
        train_images = load_images(config.balanced_train_dataset_path)
        eval_images = load_images(config.test_dataset_path)
    else:
        print("📊 Using unbalanced dataset (498 images)")
        train_images = load_images(config.unbalanced_train_dataset_path)
        eval_images = load_images(config.test_dataset_path)
    
    # Setup image processor
    checkpoint = "google/vit-base-patch16-224-in21k"
    image_processor = AutoImageProcessor.from_pretrained(checkpoint)
    
    # Create datasets
    train_dataset = BalancedImageDataset(train_images, image_processor, config)
    eval_dataset = BalancedImageDataset(eval_images, image_processor, config)
    
    # Start main MLflow run for the optimization
    with mlflow.start_run(run_name="optuna_hyperparameter_optimization"):
        # Log optimization metadata
        mlflow.log_param("optimization_method", "optuna")
        mlflow.log_param("n_trials", args.n_trials)
        mlflow.log_param("balanced_dataset", args.balanced)
        mlflow.log_param("total_train_samples", len(train_dataset))
        mlflow.log_param("total_eval_samples", len(eval_dataset))
        mlflow.log_param("device", str(device))
        
        # Run Optuna optimization
        study, best_trial = optimize_hyperparameters(
            config, device, train_dataset, eval_dataset, image_processor, args.n_trials
        )
        
        # Log best trial results
        mlflow.log_metric("best_ship_f1", best_trial.value)
        mlflow.log_params({f"best_{k}": v for k, v in best_trial.params.items()})
        
        print("\n" + "="*80)
        print("🎯 TRAINING FINAL MODEL WITH BEST PARAMETERS")
        print("="*80)
        
        # Train final model with best parameters
        final_args = type(args)()  # Create a copy of args
        for attr in dir(args):
            if not attr.startswith('_'):
                setattr(final_args, attr, getattr(args, attr))
        
        # Override with best trial parameters
        final_args.learning_rate = best_trial.params["learning_rate"]
        final_args.batch_size = best_trial.params["per_device_train_batch_size"]
        final_args.epochs = best_trial.params["num_train_epochs"]
        
        # Train final model (this will be a separate MLflow run)
        print(f"Training final model with best Ship F1: {best_trial.value:.4f}")
        final_results = train_model_with_params(final_args, best_trial.params, config, device, train_dataset, eval_dataset, image_processor)
        
        print("\n" + "="*80)
        print("🏁 OPTIMIZATION COMPLETE")
        print("="*80)
        print(f"Best Ship F1 achieved: {best_trial.value:.4f}")
        print(f"Final model trained with optimized parameters")
        print("Check MLflow for detailed trial results and model artifacts")


def train_model_with_params(args, best_params, config, device, train_dataset, eval_dataset, image_processor):
    """Train final model with optimized parameters"""
    with mlflow.start_run(run_name="final_optimized_model", nested=True):
        # Log that this is the final model
        mlflow.log_param("model_type", "final_optimized")
        mlflow.log_params(best_params)
        
        # Load model with dropout configuration
        checkpoint = "google/vit-base-patch16-224-in21k"
        from transformers import ViTConfig
        
        model_config = ViTConfig.from_pretrained(checkpoint)
        model_config.num_labels = len(config.classes)
        model_config.id2label = config.id2label
        model_config.label2id = config.label2id
        model_config.hidden_dropout_prob = 0.1
        model_config.attention_probs_dropout_prob = 0.1
        
        model = AutoModelForImageClassification.from_pretrained(
            checkpoint,
            config=model_config,
            ignore_mismatched_sizes=True
        )
        
        # Create final training arguments with best parameters
        training_args = TrainingArguments(
            output_dir=str(config.model_output_dir),
            remove_unused_columns=False,
            
            # Best parameters from optimization
            learning_rate=best_params["learning_rate"],
            per_device_train_batch_size=best_params["per_device_train_batch_size"],
            num_train_epochs=best_params["num_train_epochs"],
            warmup_ratio=best_params["warmup_ratio"],
            weight_decay=best_params["weight_decay"],
            lr_scheduler_type=best_params["lr_scheduler_type"],
            label_smoothing_factor=best_params["label_smoothing_factor"],
            gradient_accumulation_steps=best_params["gradient_accumulation_steps"],
            max_grad_norm=best_params["max_grad_norm"],
            eval_steps=best_params["eval_steps"],
            
            # Fixed parameters
            per_device_eval_batch_size=best_params["per_device_train_batch_size"] * 2,
            eval_strategy="steps",
            save_strategy="steps",
            save_steps=best_params["eval_steps"] * 2,
            logging_steps=25,
            logging_first_step=True,
            
            # Model selection
            load_best_model_at_end=True,
            metric_for_best_model="ship_f1",
            greater_is_better=True,
            
            # Performance optimization
            fp16=(device.type == "cuda"),
            dataloader_pin_memory=True,
            dataloader_num_workers=2,
            
            # Full logging for final model
            report_to=[],
            push_to_hub=False,
            save_total_limit=3,
            save_only_model=True,
        )
        
        # Create trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            data_collator=DefaultDataCollator(),
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=image_processor,
            compute_metrics=compute_metrics,
        )
        
        # Display configuration
        print(f"\n📋 FINAL MODEL CONFIGURATION")
        print(f"   • Learning rate: {best_params['learning_rate']}")
        print(f"   • Batch size: {best_params['per_device_train_batch_size']}")
        print(f"   • Epochs: {best_params['num_train_epochs']}")
        print(f"   • Warmup ratio: {best_params['warmup_ratio']}")
        print(f"   • Weight decay: {best_params['weight_decay']}")
        print(f"   • LR scheduler: {best_params['lr_scheduler_type']}")
        print(f"   • Label smoothing: {best_params['label_smoothing_factor']}")
        print(f"   • Max grad norm: {best_params['max_grad_norm']}")
        
        # Train the final model
        print(f"\n🎯 Training final model...")
        train_start = time.time()
        trainer.train()
        train_end = time.time()
        
        training_time_minutes = (train_end - train_start) / 60
        print(f"✅ Final training complete - Time: {training_time_minutes:.2f} minutes")
        
        # Final evaluation
        eval_results = trainer.evaluate()
        
        # Log comprehensive metrics
        metrics_to_log = {
            "final_accuracy": eval_results.get("eval_accuracy", 0),
            "final_ship_f1": eval_results.get("eval_ship_f1", 0),
            "final_f1_macro": eval_results.get("eval_f1_macro", 0),
            "final_matthews_corrcoef": eval_results.get("eval_matthews_corrcoef", 0),
            "final_auc_roc": eval_results.get("eval_auc_roc", 0),
            "training_time_minutes": training_time_minutes,
        }
        
        mlflow.log_metrics(metrics_to_log)
        
        # Save model
        final_model_path = config.model_output_dir / "final_optimized_model"
        trainer.save_model(str(final_model_path))
        print(f"✅ Final model saved to: {final_model_path}")
        
        # Register model with MLflow (matches notebook)
        user_name = os.environ.get('DOMINO_USER_NAME', 'unknown')
        model_name = f"Seabed-Classifier-{user_name}_ViT_Classification"
        
        model_info = mlflow.pytorch.log_model(
            pytorch_model=trainer.model,
            artifact_path="model",
            registered_model_name=model_name
        )
        
        print(f"✅ Model registered: {model_name}")
        
        return eval_results


def main():
    parser = argparse.ArgumentParser(description="Train Seabed Object Classification Model with Optuna Optimization")
    
    # Training mode options
    parser.add_argument("--optimize", action="store_true", help="Run Optuna hyperparameter optimization (matches notebook)")
    parser.add_argument("--n-trials", type=int, default=10, help="Number of Optuna trials for optimization")
    
    # Manual training options (used when not optimizing)
    parser.add_argument("--epochs", type=int, default=7, help="Number of training epochs (optimized default: 7)")
    parser.add_argument("--batch-size", type=int, default=16, help="Training batch size")
    parser.add_argument("--learning-rate", type=float, default=7.655e-5, help="Learning rate (optimized default: 7.655e-5)")
    parser.add_argument("--use-defaults", action="store_true", help="Use original defaults instead of optimized hyperparameters")
    
    # Dataset and hardware options
    parser.add_argument("--balanced", action="store_true", help="Use balanced dataset (138 images)")
    parser.add_argument("--no-gpu", action="store_true", help="Force CPU training")

    args = parser.parse_args()

    if args.optimize:
        print("\n🔬 Starting Optuna hyperparameter optimization (matches notebook approach)")
        run_optimization(args)
    else:
        print("\n🚀 Starting single training run with fixed hyperparameters")
        train_model(args)


if __name__ == "__main__":
    main()
