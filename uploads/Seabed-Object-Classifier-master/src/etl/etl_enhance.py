#!/usr/bin/env python3
"""
STAGE 3: Enhancement - Flow-compatible version
Reads from /workflow/inputs/denoised_data, writes to /workflow/outputs/enhanced_data
"""
import os
import cv2
import numpy as np
from pathlib import Path

def apply_clahe(img, clip_limit=2.0, tile_grid_size=(8, 8)):
    """Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)"""
    clahe = cv2.createCLAHE(clipLimit=clip_limit, tileGridSize=tile_grid_size)
    return clahe.apply(img)

def unsharp_mask(img, kernel_size=(5, 5), sigma=1.0, amount=1.5, threshold=0):
    """Apply unsharp masking for feature sharpening"""
    blurred = cv2.GaussianBlur(img, kernel_size, sigma)
    sharpened = float(amount + 1) * img - float(amount) * blurred
    sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
    sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
    sharpened = sharpened.round().astype(np.uint8)

    if threshold > 0:
        low_contrast_mask = np.absolute(img - blurred) < threshold
        np.copyto(sharpened, img, where=low_contrast_mask)

    return sharpened

def main():
    # Input from previous stage
    input_dir = Path('/workflow/inputs/denoised_data')

    # Output for next stage
    output_dir = Path('/workflow/outputs/enhanced_data')
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
                    # Apply CLAHE
                    img_clahe = apply_clahe(img, clip_limit=2.0, tile_grid_size=(8, 8))

                    # Apply unsharp masking
                    img_enhanced = unsharp_mask(img_clahe, amount=1.5)

                    output_path = class_output_path / fname
                    cv2.imwrite(str(output_path), img_enhanced)
                    processed_count += 1

    print(f"STAGE 3 COMPLETE: Enhanced {processed_count}/{total_count} images")
    print(f"Output: {output_dir}")

if __name__ == "__main__":
    main()
