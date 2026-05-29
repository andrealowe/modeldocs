#!/usr/bin/env python3
"""
STAGE 4: Package - Flow-compatible version
Reads from /workflow/inputs/enhanced_data, creates zip at /workflow/outputs/cleaned_data_zip
"""
import os
import shutil
import zipfile
from pathlib import Path
from datetime import datetime

def main():
    # Input from previous stage
    input_dir = Path('/workflow/inputs/enhanced_data')

    # Output zip file
    output_file = Path('/workflow/outputs/cleaned_data_zip')

    # Create timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Create zip file
    print(f"Creating zip archive of enhanced data...")
    print(f"Input: {input_dir}")
    print(f"Output: {output_file}")

    with zipfile.ZipFile(str(output_file), 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Walk through all files in the enhanced_data directory
        for class_dir in ['plane', 'ship', 'seafloor']:
            class_path = input_dir / class_dir
            if class_path.exists():
                for fname in os.listdir(class_path):
                    if fname.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp')):
                        file_path = class_path / fname
                        # Add to zip with class structure preserved
                        arcname = f'{class_dir}/{fname}'
                        zipf.write(file_path, arcname=arcname)
                        print(f"  Added: {arcname}")

    # Get file size
    file_size = output_file.stat().st_size if output_file.exists() else 0

    print(f"\nSTAGE 4 COMPLETE: Packaged cleaned data")
    print(f"Zip file: {output_file}")
    print(f"File size: {file_size:,} bytes ({file_size / (1024*1024):.2f} MB)")
    print(f"\nTo create a dataset snapshot:")
    print(f"1. Download this zip file from the Flow execution")
    print(f"2. Upload to Domino Dataset")
    print(f"3. Create a snapshot for future flows")

if __name__ == "__main__":
    main()
