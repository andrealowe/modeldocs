# SEABED SONAR IMAGE FEATURE ENHANCEMENT MODULE
# Usage: python enhance_features.py --input_dir STEP2_DIR --output_dir STEP3_DIR

import os
import argparse
import cv2
import numpy as np
import json
from datetime import datetime

def unsharp_mask(img, kernel_size=(5,5), sigma=1.0, amount=1.5, threshold=0):
    """
    Apply unsharp masking for feature enhancement
    
    :param img: Input image
    :param kernel_size: Gaussian blur kernel size
    :param sigma: Gaussian blur sigma
    :param amount: Sharpening strength
    :param threshold: Low contrast threshold
    :return: Sharpened image
    """
    blurred = cv2.GaussianBlur(img, kernel_size, sigma)
    mask = img.astype(np.float32) - blurred.astype(np.float32)
    sharp = img.astype(np.float32) + amount * mask
    
    if threshold > 0:
        low_contrast = np.abs(img.astype(np.float32) - blurred.astype(np.float32)) < threshold
        sharp[low_contrast] = img[low_contrast]
    
    return np.clip(sharp, 0, 255).astype(np.uint8)

def process_sonar_enhancement(img, clahe_clip=2.0, clahe_grid=8, 
                             unsharp_sigma=1.0, unsharp_amount=1.5, 
                             unsharp_threshold=0):
    """
    Apply comprehensive feature enhancement to sonar imagery
    
    :param img: Input denoised sonar image
    :param clahe_clip: CLAHE clip limit
    :param clahe_grid: CLAHE tile grid size
    :param unsharp_sigma: Unsharp mask sigma
    :param unsharp_amount: Unsharp mask amount
    :param unsharp_threshold: Unsharp mask threshold
    :return: Enhanced image ready for training
    """
    # Stage 1: CLAHE for adaptive contrast enhancement
    clahe = cv2.createCLAHE(clipLimit=clahe_clip,
                           tileGridSize=(clahe_grid, clahe_grid))
    contrast_enhanced = clahe.apply(img)
    
    # Stage 2: Unsharp masking for feature sharpening
    enhanced = unsharp_mask(contrast_enhanced,
                           sigma=unsharp_sigma,
                           amount=unsharp_amount,
                           threshold=unsharp_threshold)
    
    return enhanced

def generate_processing_metadata(args, processed_count, total_count):
    """Generate metadata for the enhancement stage"""
    return {
        "stage": "feature_enhancement",
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "clahe_clip": args.clahe_clip,
            "clahe_grid": args.clahe_grid,
            "unsharp_sigma": args.unsharp_sigma,
            "unsharp_amount": args.unsharp_amount,
            "unsharp_threshold": args.unsharp_threshold,
            "input_dir": args.input_dir,
            "output_dir": args.output_dir
        },
        "processing_stats": {
            "images_processed": processed_count,
            "images_total": total_count,
            "success_rate": processed_count / max(total_count, 1)
        },
        "status": "TRAINING_READY"
    }

def main():
    parser = argparse.ArgumentParser(description="STAGE 3: Enhance contrast and features in sonar images.")
    parser.add_argument("--input_dir", required=True, help="Path to denoised sonar images")
    parser.add_argument("--output_dir", required=True, help="Path to save enhanced images")
    parser.add_argument("--clahe_clip", type=float, default=2.0, help="CLAHE clip limit")
    parser.add_argument("--clahe_grid", type=int, default=8, help="CLAHE tile grid size")
    parser.add_argument("--unsharp_sigma", type=float, default=1.0, help="Unsharp mask sigma")
    parser.add_argument("--unsharp_amount", type=float, default=1.5, help="Unsharp mask amount")
    parser.add_argument("--unsharp_threshold", type=int, default=0, help="Unsharp mask threshold")
    parser.add_argument("--preserve_structure", action="store_true",
                        help="Preserve class subdirectory structure (plane/ship/seafloor)")
    args = parser.parse_args()

    # Create output directory
    os.makedirs(args.output_dir, exist_ok=True)
    
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
                        enhanced_img = process_sonar_enhancement(
                            img, args.clahe_clip, args.clahe_grid,
                            args.unsharp_sigma, args.unsharp_amount,
                            args.unsharp_threshold
                        )
                        output_path = os.path.join(class_output_path, fname)
                        cv2.imwrite(output_path, enhanced_img)
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
                enhanced_img = process_sonar_enhancement(
                    img, args.clahe_clip, args.clahe_grid,
                    args.unsharp_sigma, args.unsharp_amount,
                    args.unsharp_threshold
                )
                output_path = os.path.join(args.output_dir, fname)
                cv2.imwrite(output_path, enhanced_img)
                processed_count += 1

    # Generate processing metadata
    metadata = generate_processing_metadata(args, processed_count, total_count)
    metadata_path = os.path.join(args.output_dir, "processing_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"STAGE 3 COMPLETE: Enhanced {processed_count}/{total_count} sonar images")
    print(f"Output: {args.output_dir}")
    print(f"CLAHE parameters: clip={args.clahe_clip}, grid={args.clahe_grid}")
    print(f"Unsharp parameters: sigma={args.unsharp_sigma}, amount={args.unsharp_amount}")
    print(f"Status: TRAINING READY")
    print(f"Metadata: {metadata_path}")

if __name__ == "__main__":
    main()