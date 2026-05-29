# SEABED SONAR IMAGE NORMALIZATION MODULE
# Usage: python load-dataset.py --input_dir RAW_DIR --output_dir STEP1_DIR

import os
import argparse
import cv2
import numpy as np
import json
from datetime import datetime

def process_sonar_normalization(img, gamma=None):
    """
    Apply normalization and gamma correction to sonar imagery
    
    :param img: Input grayscale sonar image
    :param gamma: Gamma correction factor (None, 0 for log, or float value)
    :return: Normalized image
    """
    # Normalize to [0,1] range
    img_f = img.astype(np.float32)
    img_f = (img_f - img_f.min()) / (img_f.max() - img_f.min() + 1e-8)
    
    # Apply gamma correction or log transform
    if gamma is not None:
        if gamma == 0:
            # Log transform for maximum dynamic range
            img_f = np.log1p(img_f)
        else:
            # Power law transformation
            img_f = np.power(img_f, gamma)
        # Re-normalize after transformation
        img_f = (img_f - img_f.min()) / (img_f.max() - img_f.min() + 1e-8)
    
    # Convert back to uint8
    return (img_f * 255).astype(np.uint8)

def generate_processing_metadata(args, processed_count, total_count):
    """Generate metadata for the processing stage"""
    return {
        "stage": "normalization",
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "gamma": args.gamma,
            "input_dir": args.input_dir,
            "output_dir": args.output_dir
        },
        "processing_stats": {
            "images_processed": processed_count,
            "images_total": total_count,
            "success_rate": processed_count / max(total_count, 1)
        }
    }

def main():
    parser = argparse.ArgumentParser(description="STAGE 1: Load and normalize sonar images for seabed object detection.")
    parser.add_argument("--input_dir", required=True, help="Path to raw sonar images directory")
    parser.add_argument("--output_dir", required=True, help="Path to save normalized images")
    parser.add_argument("--gamma", type=float, default=0.5, 
                        help="Gamma correction factor (0.5 default, 0 for log transform)")
    parser.add_argument("--preserve_structure", action="store_true",
                        help="Preserve class subdirectory structure (plane/ship/seafloor)")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)

    # Create workflow outputs directory for Domino Flows
    workflow_output_dir = '/workflow/outputs'
    os.makedirs(workflow_output_dir, exist_ok=True)

    processed_count = 0
    total_count = 0
    
    # Handle both flat directory and class-structured directory
    if args.preserve_structure:
        # Process class subdirectories
        for class_dir in ["plane", "ship", "seafloor"]:
            class_input_path = os.path.join(args.input_dir, class_dir)
            class_output_path = os.path.join(args.output_dir, class_dir)
            
            if os.path.exists(class_input_path):
                os.makedirs(class_output_path, exist_ok=True)
                
                for fname in os.listdir(class_input_path):
                    if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".bmp")):
                        continue
                        
                    total_count += 1
                    img_path = os.path.join(class_input_path, fname)
                    img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
                    
                    if img is not None:
                        normalized_img = process_sonar_normalization(img, args.gamma)
                        output_path = os.path.join(class_output_path, fname)
                        cv2.imwrite(output_path, normalized_img)
                        processed_count += 1
    else:
        # Process flat directory structure
        for fname in os.listdir(args.input_dir):
            if not fname.lower().endswith((".png", ".jpg", ".jpeg", ".tif", ".bmp")):
                continue
                
            total_count += 1
            img_path = os.path.join(args.input_dir, fname)
            img = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
            
            if img is not None:
                normalized_img = process_sonar_normalization(img, args.gamma)
                output_path = os.path.join(args.output_dir, fname)
                cv2.imwrite(output_path, normalized_img)
                processed_count += 1
    
    # Generate processing metadata
    metadata = generate_processing_metadata(args, processed_count, total_count)
    metadata_path = os.path.join(args.output_dir, "processing_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"STAGE 1 COMPLETE: Normalized {processed_count}/{total_count} sonar images")
    print(f"Output: {args.output_dir}")
    print(f"Gamma correction: {args.gamma}")
    print(f"Metadata: {metadata_path}")

    # Write output for Domino Flow
    with open(os.path.join(workflow_output_dir, 'normalized_complete'), 'w') as f:
        f.write(f'{processed_count}')

if __name__ == "__main__":
    main()