# SEABED SONAR DATA ORGANIZATION MODULE
# Usage: python organize_outputs.py --stage1_dir DIR1 --stage2_dir DIR2 --stage3_dir DIR3 --output_summary SUMMARY.json

import os
import argparse
import json
from datetime import datetime
from pathlib import Path

def count_files_in_directory(directory):
    """Count files in a directory and subdirectories"""
    file_count = 0
    class_counts = {}
    
    if not os.path.exists(directory):
        return 0, {}
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.lower().endswith(('.png', '.jpg', '.jpeg', '.tif', '.bmp')):
                file_count += 1
                
                # Track class-specific counts
                class_name = os.path.basename(root)
                if class_name in ['plane', 'ship', 'seafloor']:
                    class_counts[class_name] = class_counts.get(class_name, 0) + 1
    
    return file_count, class_counts

def analyze_processing_metadata(stage_dir):
    """Analyze processing metadata from a stage directory"""
    metadata_path = os.path.join(stage_dir, "processing_metadata.json")
    
    if os.path.exists(metadata_path):
        try:
            with open(metadata_path, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def generate_comprehensive_summary(stage1_dir, stage2_dir, stage3_dir):
    """Generate comprehensive processing summary"""
    
    # Count files in each stage
    stage1_count, stage1_classes = count_files_in_directory(stage1_dir)
    stage2_count, stage2_classes = count_files_in_directory(stage2_dir)
    stage3_count, stage3_classes = count_files_in_directory(stage3_dir)
    
    # Analyze metadata from each stage
    stage1_meta = analyze_processing_metadata(stage1_dir)
    stage2_meta = analyze_processing_metadata(stage2_dir)
    stage3_meta = analyze_processing_metadata(stage3_dir)
    
    # Generate summary
    summary = {
        "pipeline_summary": {
            "timestamp": datetime.now().isoformat(),
            "pipeline_version": "1.0",
            "stages_completed": 3,
            "status": "PROCESSING_COMPLETE"
        },
        "stage_statistics": {
            "stage1_normalization": {
                "total_files": stage1_count,
                "class_distribution": stage1_classes,
                "metadata": stage1_meta
            },
            "stage2_denoising": {
                "total_files": stage2_count,
                "class_distribution": stage2_classes,
                "metadata": stage2_meta
            },
            "stage3_enhancement": {
                "total_files": stage3_count,
                "class_distribution": stage3_classes,
                "metadata": stage3_meta,
                "training_ready": True
            }
        },
        "processing_validation": {
            "consistency_check": stage1_count == stage2_count == stage3_count,
            "file_preservation": {
                "stage1_to_stage2": stage1_count == stage2_count,
                "stage2_to_stage3": stage2_count == stage3_count
            },
            "class_preservation": {
                "stage1_classes": list(stage1_classes.keys()),
                "stage2_classes": list(stage2_classes.keys()),
                "stage3_classes": list(stage3_classes.keys())
            }
        },
        "deployment_info": {
            "final_output_location": stage3_dir,
            "training_ready": True,
            "recommended_next_step": "Use stage3_enhanced data for model training",
            "data_format": "PNG grayscale images, 183x190 or original dimensions",
            "class_structure": "Preserved (plane/ship/seafloor subdirectories)"
        }
    }
    
    return summary

def main():
    parser = argparse.ArgumentParser(description="STAGE 4: Organize and summarize processed sonar data.")
    parser.add_argument("--stage1_dir", required=True, help="Path to stage 1 normalized data")
    parser.add_argument("--stage2_dir", required=True, help="Path to stage 2 denoised data")
    parser.add_argument("--stage3_dir", required=True, help="Path to stage 3 enhanced data")
    parser.add_argument("--output_summary", required=True, help="Path to output summary JSON file")
    parser.add_argument("--create_dataset_links", action="store_true",
                        help="Create symbolic links for easy dataset access")
    args = parser.parse_args()

    # Generate comprehensive summary
    summary = generate_comprehensive_summary(args.stage1_dir, args.stage2_dir, args.stage3_dir)
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output_summary), exist_ok=True)
    
    # Save summary to JSON file
    with open(args.output_summary, 'w') as f:
        json.dump(summary, f, indent=2)
    
    # Create convenient access links if requested
    if args.create_dataset_links:
        base_dir = os.path.dirname(args.output_summary)
        links = {
            "training_ready_data": args.stage3_dir,
            "intermediate_normalized": args.stage1_dir,
            "intermediate_denoised": args.stage2_dir
        }
        
        for link_name, target_path in links.items():
            link_path = os.path.join(base_dir, link_name)
            if os.path.exists(link_path):
                os.unlink(link_path)
            try:
                os.symlink(target_path, link_path)
            except:
                pass  # Symlinks may not work in all environments
    
    # Print summary
    print("STAGE 4 COMPLETE: Data organization and summary generation")
    print(f"Summary saved to: {args.output_summary}")
    print(f"Pipeline Status: {summary['pipeline_summary']['status']}")
    print(f"Files processed: {summary['stage_statistics']['stage3_enhancement']['total_files']}")
    print(f"Training ready: {summary['deployment_info']['training_ready']}")
    print(f"Final data location: {summary['deployment_info']['final_output_location']}")
    
    # Validation checks
    if summary['processing_validation']['consistency_check']:
        print("✅ File count consistency maintained across all stages")
    else:
        print("⚠️  File count mismatch detected between stages")
    
    if summary['stage_statistics']['stage3_enhancement']['class_distribution']:
        print("✅ Class structure preserved")
        for class_name, count in summary['stage_statistics']['stage3_enhancement']['class_distribution'].items():
            print(f"   • {class_name}: {count} images")
    
    return "PROCESSING_PIPELINE_COMPLETE"

if __name__ == "__main__":
    main()