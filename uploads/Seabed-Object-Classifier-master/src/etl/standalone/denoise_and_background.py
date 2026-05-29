# SEABED SONAR IMAGE DENOISING AND BACKGROUND SUBTRACTION MODULE
# Usage: python denoise_and_background.py --input_dir STEP1_DIR --output_dir STEP2_DIR

import os
import argparse
import cv2
import numpy as np
import json
from datetime import datetime

def estimate_background(img, kernel_size=51):
    """
    Estimate background using morphological opening
    
    :param img: Input image
    :param kernel_size: Size of morphological kernel
    :return: Background estimate
    """
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    return cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

def process_sonar_denoising(img, median_ksize=5, bilateral_d=9, 
                           bilateral_sigmaColor=75, bilateral_sigmaSpace=75, 
                           bg_kernel=51):
    """
    Apply comprehensive denoising to sonar imagery
    
    :param img: Input normalized sonar image
    :param median_ksize: Median filter kernel size
    :param bilateral_d: Bilateral filter diameter
    :param bilateral_sigmaColor: Bilateral filter sigma color
    :param bilateral_sigmaSpace: Bilateral filter sigma space
    :param bg_kernel: Background estimation kernel size
    :return: Denoised and background-subtracted image
    """
    # Stage 1: Median filter for impulse noise removal
    denoised = cv2.medianBlur(img, median_ksize)
    
    # Stage 2: Bilateral filter for edge-preserving smoothing
    denoised = cv2.bilateralFilter(denoised, bilateral_d,
                                  bilateral_sigmaColor,
                                  bilateral_sigmaSpace)
    
    # Stage 3: Background subtraction for object enhancement
    background = estimate_background(denoised, kernel_size=bg_kernel)
    result = cv2.subtract(denoised, background)
    
    # Ensure valid intensity range
    return np.clip(result, 0, 255).astype(np.uint8)

def generate_processing_metadata(args, processed_count, total_count):
    """Generate metadata for the denoising stage"""
    return {
        "stage": "denoising_background_subtraction",
        "timestamp": datetime.now().isoformat(),
        "parameters": {
            "median_ksize": args.median_ksize,
            "bilateral_d": args.bilateral_d,
            "bilateral_sigmaColor": args.bilateral_sigmaColor,
            "bilateral_sigmaSpace": args.bilateral_sigmaSpace,
            "bg_kernel": args.bg_kernel,
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
    parser = argparse.ArgumentParser(description="STAGE 2: Denoise and subtract background from sonar images.")
    parser.add_argument("--input_dir", required=True, help="Path to normalized sonar images")
    parser.add_argument("--output_dir", required=True, help="Path to save denoised images")
    parser.add_argument("--median_ksize", type=int, default=5, help="Median filter kernel size")
    parser.add_argument("--bilateral_d", type=int, default=9, help="Bilateral filter diameter")
    parser.add_argument("--bilateral_sigmaColor", type=int, default=75, help="Bilateral sigma color")
    parser.add_argument("--bilateral_sigmaSpace", type=int, default=75, help="Bilateral sigma space")
    parser.add_argument("--bg_kernel", type=int, default=51, help="Background estimation kernel size")
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
                        denoised_img = process_sonar_denoising(
                            img, args.median_ksize, args.bilateral_d,
                            args.bilateral_sigmaColor, args.bilateral_sigmaSpace,
                            args.bg_kernel
                        )
                        output_path = os.path.join(class_output_path, fname)
                        cv2.imwrite(output_path, denoised_img)
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
                denoised_img = process_sonar_denoising(
                    img, args.median_ksize, args.bilateral_d,
                    args.bilateral_sigmaColor, args.bilateral_sigmaSpace,
                    args.bg_kernel
                )
                output_path = os.path.join(args.output_dir, fname)
                cv2.imwrite(output_path, denoised_img)
                processed_count += 1

    # Generate processing metadata
    metadata = generate_processing_metadata(args, processed_count, total_count)
    metadata_path = os.path.join(args.output_dir, "processing_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"STAGE 2 COMPLETE: Denoised {processed_count}/{total_count} sonar images")
    print(f"Output: {args.output_dir}")
    print(f"Denoising parameters: median={args.median_ksize}, bilateral_d={args.bilateral_d}")
    print(f"Background kernel: {args.bg_kernel}")
    print(f"Metadata: {metadata_path}")

if __name__ == "__main__":
    main()