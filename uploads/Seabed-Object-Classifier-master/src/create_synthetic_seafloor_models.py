#!/usr/bin/env python3
"""
Combined Synthetic Seafloor Terrain Model Registration and Tagging Script

Creates realistic synthetic models for different seafloor terrain types across
strategic US monitoring regions. Models are registered in MLflow with complete
metadata, hardware deployment specs, risk assessments, and individual tags.

This script combines both model registration and tagging functionality.

Author: Claude Code Assistant
Date: 2025-11-13
"""

import mlflow
import mlflow.pytorch
import os
import uuid
import random
from datetime import datetime, timedelta
from mlflow.tracking import MlflowClient
import time

# Synthetic model configurations
TERRAIN_CONFIGS = {
    "Continental_Shelf": {
        "architecture": "EfficientNet-B3 + Depth-Aware Convolutions", 
        "depth_range": "100-200m",
        "complexity": "High biodiversity, sediment-rich environments",
        "risk_level": "Medium",
        "hardware": "Autonomous Underwater Vehicle (AUV) - REMUS 600",
        "hardware_short": "AUV REMUS 600",
        "deployment_depth": "100-200m",
        "mission_duration": "12-24 hours",
        "accuracy_range": (0.91, 0.95),
        "f1_range": (0.87, 0.92)
    },
    "Seamount": {
        "architecture": "ResNet-101 + Topographic Gradient Analysis",
        "depth_range": ">1000m elevation",
        "complexity": "Volcanic hard-bottom substrates, complex terrain",
        "risk_level": "High", 
        "hardware": "Deep Sea ROV - Jason III",
        "hardware_short": "ROV Jason III",
        "deployment_depth": "1000-4000m",
        "mission_duration": "8-12 hours",
        "accuracy_range": (0.88, 0.93),
        "f1_range": (0.84, 0.89)
    },
    "Submarine_Canyon": {
        "architecture": "DenseNet-169 + Current-Flow Modeling",
        "depth_range": "Variable depth gradients",
        "complexity": "Erosional features, steep gradients, mass wasting",
        "risk_level": "High",
        "hardware": "Tethered ROV - Hercules Deep Sea Platform",
        "hardware_short": "ROV Hercules",
        "deployment_depth": "500-3000m", 
        "mission_duration": "6-10 hours",
        "accuracy_range": (0.89, 0.94),
        "f1_range": (0.85, 0.91)
    },
    "Abyssal_Plain": {
        "architecture": "Vision Transformer (ViT-Large) + Fine Sediment Analysis",
        "depth_range": "3000-6000m",
        "complexity": "Low-relief, fine sediment deposits",
        "risk_level": "Low",
        "hardware": "Long-Range AUV - Hugin 3000",
        "hardware_short": "AUV Hugin 3000",
        "deployment_depth": "3000-6000m",
        "mission_duration": "24-48 hours",
        "accuracy_range": (0.94, 0.97),
        "f1_range": (0.91, 0.95)
    },
    "Hydrothermal_Vent": {
        "architecture": "Inception-v4 + Thermal Signature Detection",
        "depth_range": "Variable depth",
        "complexity": "High-temperature anomalies, unique mineral formations",
        "risk_level": "High",
        "hardware": "Specialized Deep ROV - Alvin Research Submersible",
        "hardware_short": "ROV Alvin",
        "deployment_depth": "2000-6000m",
        "mission_duration": "4-8 hours",
        "accuracy_range": (0.86, 0.91),
        "f1_range": (0.82, 0.88)
    }
}

REGIONS = {
    "GIUK": {
        "full_name": "Greenland-Iceland-UK Gap",
        "tag_name": "GIUK Gap",
        "coordinates": "62.0°N, 18.0°W",
        "strategic_value": "North Atlantic submarine chokepoint",
        "risk_level": "High"
    },
    "SCS": {
        "full_name": "South China Sea",
        "tag_name": "South China Sea",
        "coordinates": "15.0°N, 115.0°E", 
        "strategic_value": "$3T+ annual commerce, critical Pacific trade route",
        "risk_level": "High"
    },
    "Hormuz": {
        "full_name": "Strait of Hormuz",
        "tag_name": "Strait of Hormuz",
        "coordinates": "26.5°N, 56.3°E",
        "strategic_value": "33% global seaborne trade, oil transit",
        "risk_level": "High"
    },
    "Arctic": {
        "full_name": "Arctic Ocean/Bering Strait",
        "tag_name": "Arctic Ocean",
        "coordinates": "71.0°N, 156.0°W",
        "strategic_value": "Emerging polar shipping corridor",
        "risk_level": "Medium"
    },
    "Pacific": {
        "full_name": "Eastern Pacific Shelf",
        "tag_name": "Eastern Pacific",
        "coordinates": "37.0°N, 123.0°W", 
        "strategic_value": "US West Coast submarine approaches",
        "risk_level": "Medium"
    }
}

def generate_synthetic_metrics(terrain_type, region):
    """Generate realistic performance metrics based on terrain complexity"""
    config = TERRAIN_CONFIGS[terrain_type]
    
    # Generate metrics with some variance
    accuracy = round(random.uniform(*config["accuracy_range"]), 4)
    f1 = round(random.uniform(*config["f1_range"]), 4)
    
    # Generate correlated metrics
    precision = round(f1 + random.uniform(-0.03, 0.03), 4)
    recall = round(f1 + random.uniform(-0.02, 0.04), 4)
    auc_roc = round(accuracy + random.uniform(-0.02, 0.05), 4)
    log_loss = round(random.uniform(0.15, 0.35), 4)
    
    # Terrain-specific adjustments
    if terrain_type == "Hydrothermal_Vent":
        log_loss += 0.05  # More challenging
    elif terrain_type == "Abyssal_Plain": 
        log_loss -= 0.05  # Easier detection
        
    return {
        "accuracy": min(accuracy, 0.97),
        "f1": min(f1, 0.95), 
        "precision": min(precision, 0.96),
        "recall": min(recall, 0.95),
        "auc_roc": min(auc_roc, 0.98),
        "log_loss": max(log_loss, 0.08)
    }

def generate_synthetic_params(terrain_type):
    """Generate realistic training parameters"""
    config = TERRAIN_CONFIGS[terrain_type]
    
    # Base parameters with terrain-specific variations
    params = {
        "learning_rate": random.choice([1e-4, 2e-4, 5e-4, 1e-3]),
        "batch_size": random.choice([16, 32, 64]),
        "epochs": random.randint(8, 15),
        "image_size": "224",
        "optimizer": "AdamW",
        "weight_decay": round(random.uniform(0.01, 0.05), 3),
        "warmup_ratio": 0.1,
        "model_architecture": config["architecture"].split(" + ")[0],
        "dropout_rate": round(random.uniform(0.1, 0.3), 2),
        "label_smoothing": round(random.uniform(0.05, 0.15), 2)
    }
    
    return params

def create_model_card(terrain_type, region, config, region_info):
    """Generate model card content for synthetic model"""
    return f"""# SEAFLOOR {terrain_type.upper().replace('_', ' ')} CLASSIFICATION MODEL - {region.upper()}

## MISSION BRIEF

This is a **{config["architecture"]}** model optimized for {terrain_type.replace('_', ' ').lower()} classification in the **{region_info["full_name"]}** region. The model is specifically designed for **{config["complexity"].lower()}** operational environments.

### OPERATIONAL CAPABILITIES
- **Architecture**: {config["architecture"]}
- **Deployment Depth**: {config["deployment_depth"]}
- **Mission Duration**: {config["mission_duration"]}
- **Target Terrain**: {terrain_type.replace('_', ' ')}
- **Strategic Region**: {region_info["full_name"]}

## DEPLOYMENT SPECIFICATIONS

### HARDWARE PLATFORM
- **Primary Platform**: {config["hardware"]}
- **Operational Depth**: {config["deployment_depth"]}
- **Mission Endurance**: {config["mission_duration"]}
- **Environmental Conditions**: {config["complexity"]}

### REGIONAL INTELLIGENCE
- **Area of Operations**: {region_info["full_name"]}
- **Coordinates**: {region_info["coordinates"]}
- **Strategic Value**: {region_info["strategic_value"]}
- **Risk Assessment**: {region_info["risk_level"]} Risk

## TERRAIN CHARACTERISTICS

### GEOLOGICAL FEATURES
- **Depth Range**: {config["depth_range"]}
- **Terrain Complexity**: {config["complexity"]}
- **Detection Challenges**: {config["complexity"]}

### OPERATIONAL ENVIRONMENT
- **Risk Level**: {config["risk_level"]}
- **Deployment Platform**: {config["hardware"]}
- **Mission Profile**: Autonomous seafloor classification and object detection

## MISSION OBJECTIVES

### PRIMARY TARGETS
- Automated terrain classification
- Object detection and identification  
- Environmental monitoring and assessment
- Strategic surveillance capabilities

### PERFORMANCE REQUIREMENTS
- High-accuracy terrain mapping
- Real-time classification capability
- Robust performance in challenging conditions
- Mission-critical reliability standards

---

*This model represents advanced capability for {terrain_type.replace('_', ' ').lower()} classification in the strategic {region_info["full_name"]} region, providing critical intelligence for maritime domain awareness.*
"""

def register_and_tag_synthetic_model(terrain_type, region):
    """Register a single synthetic model with complete metadata and tags"""
    
    config = TERRAIN_CONFIGS[terrain_type]
    region_info = REGIONS[region]
    
    # Model and experiment names
    model_name = f"Seafloor-{terrain_type}-{region}_Classification"
    experiment_name = f"Synthetic-Seafloor-{terrain_type}-{region}"
    
    print(f"🌊 Processing: {model_name}")
    
    # Set experiment
    mlflow.set_experiment(experiment_name=experiment_name)
    
    # Create synthetic run
    with mlflow.start_run(run_name=f"{terrain_type}_{region}_synthetic_run") as run:
        
        # Generate synthetic data
        metrics = generate_synthetic_metrics(terrain_type, region)
        params = generate_synthetic_params(terrain_type)
        
        # Log parameters
        for key, value in params.items():
            mlflow.log_param(key, value)
            
        # Log metrics
        for key, value in metrics.items():
            mlflow.log_metric(key, value)
            
        # Log additional metadata
        mlflow.log_param("terrain_type", terrain_type)
        mlflow.log_param("region", region)
        mlflow.log_param("hardware_platform", config["hardware"])
        mlflow.log_param("deployment_depth", config["deployment_depth"])
        mlflow.log_param("mission_duration", config["mission_duration"])
        
        # Simulate training time (random between 15-45 minutes)
        training_time_min = round(random.uniform(15.0, 45.0), 2)
        mlflow.log_metric("training_time_min", training_time_min)
        
        run_id = run.info.run_id
    
    # Register model in registry
    client = MlflowClient()
    
    # Model-level tags for registry (Specs)
    model_specs = {
        "mlflow.domino.specs.Architecture": config["architecture"],
        "mlflow.domino.specs.Terrain_Type": terrain_type.replace('_', ' '),
        "mlflow.domino.specs.Region": region_info["full_name"],
        "mlflow.domino.specs.Risk_Level": config["risk_level"],
        "mlflow.domino.specs.Hardware_Platform": config["hardware"],
        "mlflow.domino.specs.Deployment_Depth": config["deployment_depth"],
        "mlflow.domino.specs.Mission_Duration": config["mission_duration"],
        "mlflow.domino.specs.Strategic_Value": region_info["strategic_value"],
        "mlflow.domino.specs.Coordinates": region_info["coordinates"]
    }
    
    # Try to create registered model
    try:
        client.create_registered_model(model_name, tags=model_specs)
        print(f"   ✅ Created registered model: {model_name}")
    except Exception:
        print(f"   ⚠️  Model already exists: {model_name}")
    
    # Create model version
    model_uri = f"runs:/{run_id}/model"
    
    # Version-specific tags
    version_tags = {
        "accuracy": f"{metrics['accuracy']:.4f}",
        "f1_score": f"{metrics['f1']:.4f}",
        "auc_roc": f"{metrics['auc_roc']:.4f}",
        "training_time_min": f"{training_time_min:.2f}",
        "dataset": "synthetic_seafloor_data"
    }
    
    # Model version description
    description = f"""Synthetic {terrain_type.replace('_', ' ')} classification model for {region_info["full_name"]} region.

Hardware: {config["hardware"]}
Deployment: {config["deployment_depth"]}
Risk Level: {config["risk_level"]}

Performance: {metrics['accuracy']:.1%} accuracy, {metrics['f1']:.1%} F1-score
Training Time: {training_time_min:.1f} minutes"""
    
    # Create model version
    mv = client.create_model_version(
        name=model_name,
        source=model_uri,
        run_id=run_id,
        description=description,
        tags=version_tags
    )
    
    # Update model description with card
    model_card = create_model_card(terrain_type, region, config, region_info)
    client.update_registered_model(model_name, model_card)
    
    print(f"   🎯 Registered model version: {mv.version}")
    
    # Add individual tags for filtering
    print(f"   🏷️  Adding individual tags...")
    
    individual_tags = {
        "seafloor_type": terrain_type.replace('_', ' '),
        "region": region_info["tag_name"],
        "hardware_platform": config["hardware_short"],
        "risk_level": config["risk_level"]
    }
    
    for tag_key, tag_value in individual_tags.items():
        try:
            client.set_registered_model_tag(model_name, tag_key, tag_value)
            print(f"      • {tag_key}: {tag_value}")
        except Exception as e:
            print(f"      ❌ Failed to set {tag_key}: {str(e)}")
    
    print(f"   📊 Performance: {metrics['accuracy']:.1%} accuracy, {metrics['f1']:.1%} F1-score")
    print(f"   🔧 Hardware: {config['hardware_short']}")
    print(f"   ⚠️  Risk Level: {config['risk_level']}")
    print(f"   📍 Region: {region_info['full_name']}\n")
    
    return model_name, mv.version

def main():
    """Register and tag all synthetic seafloor terrain models"""
    
    print("🌊 SYNTHETIC SEAFLOOR TERRAIN MODEL CREATION")
    print("=" * 60)
    print()
    
    registered_models = []
    
    # Optimal terrain-region combinations
    combinations = [
        ("Continental_Shelf", "GIUK"),
        ("Seamount", "SCS"), 
        ("Submarine_Canyon", "Hormuz"),
        ("Abyssal_Plain", "Arctic"),
        ("Hydrothermal_Vent", "Pacific")
    ]
    
    for i, (terrain, region) in enumerate(combinations, 1):
        print(f"[{i}/5] Processing {terrain} - {region}")
        
        try:
            model_name, version = register_and_tag_synthetic_model(terrain, region)
            registered_models.append((model_name, version))
            
            # Small delay to avoid overwhelming MLflow
            time.sleep(2)
            
        except Exception as e:
            print(f"❌ Error processing {terrain}-{region}: {str(e)}")
            continue
    
    print("=" * 60)
    print(f"🎉 CREATION COMPLETE: {len(registered_models)}/5 models created")
    print()
    
    print("✅ Successfully Created Models:")
    for model_name, version in registered_models:
        print(f"   • {model_name} (v{version})")
    
    print("\n📋 Each model includes:")
    print("   • Complete MLflow experiment with realistic metrics")
    print("   • Model Specs (mlflow.domino.specs.*)")
    print("   • Individual filterable tags:")
    print("     - seafloor_type (Continental Shelf, Seamount, etc.)")
    print("     - region (GIUK Gap, South China Sea, etc.)")
    print("     - hardware_platform (AUV REMUS 600, ROV Jason III, etc.)")
    print("     - risk_level (Low, Medium, High)")
    print("   • Comprehensive model cards with mission specifications")
    print("   • Strategic deployment information")
    
    print("\n🔍 Check Models tab in Domino for full model registry")

if __name__ == "__main__":
    main()