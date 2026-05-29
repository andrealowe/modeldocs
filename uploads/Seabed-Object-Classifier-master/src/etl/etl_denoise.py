#!/usr/bin/env python3
"""
STAGE 2: Denoising - Flow-compatible version
Reads from /workflow/inputs/normalized_data, writes to /workflow/outputs/denoised_data
"""
import os
import cv2
import numpy as np
from pathlib import Path

def denoise_sonar_image(img, median_ksize=5, bilateral_d=9, bilateral_sigma_color=75, bilateral_sigma_space=75):
    """Apply denoising filters to sonar image"""
    # Median filter for impulse noise
    img_median = cv2.medianBlur(img, median_ksize)

    # Bilateral filter for edge-preserving smoothing
    img_bilateral = cv2.bilateralFilter(img_median, bilateral_d, bilateral_sigma_color, bilateral_sigma_space)

    return img_bilateral

def background_subtraction(img, kernel_size=51):
    """Subtract background using morphological operations"""
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (kernel_size, kernel_size))
    background = cv2.morphologyEx(img, cv2.MORPH_OPEN, kernel)

    img_sub = cv2.subtract(img, background)
    img_sub = cv2.normalize(img_sub, None, 0, 255, cv2.NORM_MINMAX)

    return img_sub

def main():
    # Input from previous stage
    input_dir = Path('/workflow/inputs/normalized_data')

    # Output for next stage
    output_dir = Path('/workflow/outputs/denoised_data')
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    total_count = 0

    # Process class subdirectories
    for class_dir in ['plane', 'ship', 'seafloor']:
        class_input_path = input_dir / class_dir
        class_output_path = output_dir / class_dir

        if class_input_path.exists():
            class_output_path.mkdir(parents=True, exist_ok=True)

            for fname in os.listdir(class_input_path):
                if not fname.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp')):
                    continue

                total_count += 1
                img_path = class_input_path / fname
                img = cv2.imread(str(img_path), cv2.IMREAD_GRAYSCALE)

                if img is not None:
                    # Apply denoising
                    img_denoised = denoise_sonar_image(img)

                    # Apply background subtraction
                    img_final = background_subtraction(img_denoised)

                    output_path = class_output_path / fname
                    cv2.imwrite(str(output_path), img_final)
                    processed_count += 1

    print(f"STAGE 2 COMPLETE: Denoised {processed_count}/{total_count} images")
    print(f"Output: {output_dir}")

if __name__ == "__main__":
    main()
