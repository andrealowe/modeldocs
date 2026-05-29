#!/usr/bin/env python3
"""
STAGE 1: Normalization - Flow-compatible version
Reads from dataset snapshot, writes to /workflow/outputs/normalized_data
"""
import os
import argparse
import cv2
import numpy as np
import shutil
from pathlib import Path

def process_sonar_normalization(img, gamma=None):
    """Apply normalization and gamma correction to sonar imagery"""
    img_f = img.astype(np.float32)
    img_f = (img_f - img_f.min()) / (img_f.max() - img_f.min() + 1e-8)

    if gamma is not None:
        if gamma == 0:
            img_f = np.log1p(img_f)
        else:
            img_f = np.power(img_f, gamma)
        img_f = (img_f - img_f.min()) / (img_f.max() - img_f.min() + 1e-8)

    return (img_f * 255).astype(np.uint8)

def main():
    parser = argparse.ArgumentParser(description="STAGE 1: Normalize sonar images")
    parser.add_argument("--input_dir", required=True, help="Path to raw sonar images")
    parser.add_argument("--gamma", type=float, default=0.5, help="Gamma correction factor")
    args = parser.parse_args()

    # Check if running in workflow - read gamma from input file if available
    gamma_input_path = Path('/workflow/inputs/gamma')
    if gamma_input_path.exists():
        args.gamma = float(gamma_input_path.read_text().strip())

    # Output to /workflow/outputs for Domino Flows
    output_dir = Path('/workflow/outputs/normalized_data')
    output_dir.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    total_count = 0

    # Process class subdirectories
    for class_dir in ['plane', 'ship', 'seafloor']:
        class_input_path = Path(args.input_dir) / class_dir
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
                    normalized_img = process_sonar_normalization(img, args.gamma)
                    output_path = class_output_path / fname
                    cv2.imwrite(str(output_path), normalized_img)
                    processed_count += 1

    print(f"STAGE 1 COMPLETE: Normalized {processed_count}/{total_count} images")
    print(f"Output: {output_dir}")
    print(f"Gamma: {args.gamma}")

if __name__ == "__main__":
    main()
