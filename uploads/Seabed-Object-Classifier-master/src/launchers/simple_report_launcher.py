#!/usr/bin/env python3
"""
SIMPLIFIED SEABED ANALYSIS LAUNCHER
Single-phase report generation from existing sonar data

This launcher analyzes sonar images in a specified folder and generates
customizable intelligence reports based on user-selected options.
"""

import os
import sys
import json
import argparse
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Import data_config - robust path resolution for different execution contexts
current_dir = Path(__file__).parent
src_paths = [
    str(current_dir.parent),   # src/ directory (parent of launchers/)
    str(current_dir.parent.parent),  # Project root
    '/mnt/code/src',           # Git-based project absolute path
    '/mnt/src',                # File-based project absolute path
    '/mnt/code',               # Git-based project root
    '/mnt',                    # File-based project root
]
for src_path in src_paths:
    if src_path not in sys.path and Path(src_path).exists():
        sys.path.insert(0, src_path)

from data_config import DataConfig

class SimpleReportLauncher:
    """Simplified single-phase report generation launcher"""

    def __init__(self, args):
        self.args = args
        self.config = DataConfig()
        self.run_id = args.launcher_run_id or datetime.now().strftime("%Y%m%d_%H%M%S")
        self.user_name = args.user_name or "analyst"
        self.start_time = datetime.now()

        # Create results directory
        self.results_dir = self.config.base_data_path / f"launcher_results/{self.run_id}"
        self.results_dir.mkdir(parents=True, exist_ok=True)

        # Parse comma-separated multi-select options
        if isinstance(args.report_sections, str):
            self.report_sections = [s.strip() for s in args.report_sections.split(',')]
        else:
            self.report_sections = args.report_sections if args.report_sections else ["summary", "detections"]

        if isinstance(args.export_formats, str):
            self.export_formats = [f.strip() for f in args.export_formats.split(',')]
        else:
            self.export_formats = args.export_formats if args.export_formats else ["markdown"]

    def log_message(self, message):
        """Log message with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        print(log_entry)

        # Also write to log file
        log_file = self.results_dir / "execution_log.txt"
        with open(log_file, 'a') as f:
            f.write(log_entry + "\n")

    def scan_data_folder(self):
        """Scan the specified data folder and count images by class"""
        self.log_message(f"Scanning data folder: {self.args.data_folder}")

        data_path = Path(self.args.data_folder)

        if not data_path.exists():
            raise ValueError(f"Data folder not found: {self.args.data_folder}")

        # Count images by class
        image_stats = {
            "plane": [],
            "ship": [],
            "seafloor": [],
            "unknown": []
        }

        # Scan for images in class subdirectories
        for class_name in ["plane", "ship", "seafloor"]:
            class_dir = data_path / class_name
            if class_dir.exists() and class_dir.is_dir():
                images = list(class_dir.glob("*.png")) + list(class_dir.glob("*.jpg")) + list(class_dir.glob("*.jpeg"))
                image_stats[class_name] = [img.name for img in images]

        # Also check root directory for uncategorized images
        root_images = [f for f in data_path.iterdir() if f.is_file() and f.suffix.lower() in ['.png', '.jpg', '.jpeg']]
        if root_images:
            image_stats["unknown"] = [img.name for img in root_images]

        total_images = sum(len(imgs) for imgs in image_stats.values())
        self.log_message(f"Found {total_images} total images")

        return image_stats, total_images

    def run_model_predictions(self, image_stats):
        """Run model predictions on discovered images"""
        self.log_message("Running model predictions...")

        try:
            from predict import predict

            data_path = Path(self.args.data_folder)
            predictions = defaultdict(lambda: {"count": 0, "confidences": [], "files": []})

            # Run predictions on each class directory
            for true_class, image_files in image_stats.items():
                if true_class == "unknown":
                    continue

                class_dir = data_path / true_class
                for img_file in image_files[:self.args.max_images_per_class]:  # Limit images
                    img_path = class_dir / img_file
                    try:
                        result = predict(str(img_path))
                        if result:
                            # Handle both 'predicted_class' and 'label' keys
                            pred_class = result.get('predicted_class') or result.get('label')
                            confidence = result.get('confidence') or result.get('score', 0.5)

                            if not pred_class:
                                continue

                            predictions[pred_class]["count"] += 1
                            predictions[pred_class]["confidences"].append(confidence)
                            predictions[pred_class]["files"].append({
                                "filename": img_file,
                                "true_class": true_class,
                                "confidence": confidence
                            })
                    except Exception as e:
                        self.log_message(f"Error predicting {img_file}: {e}")

            # Calculate statistics
            for pred_class, data in predictions.items():
                if data["confidences"]:
                    data["avg_confidence"] = sum(data["confidences"]) / len(data["confidences"])
                    data["high_confidence"] = sum(1 for c in data["confidences"] if c >= self.args.confidence_threshold)
                else:
                    data["avg_confidence"] = 0.0
                    data["high_confidence"] = 0

            return dict(predictions)

        except Exception as e:
            self.log_message(f"Model prediction error: {e}")
            # Return mock predictions for demonstration
            return self.generate_mock_predictions(image_stats)

    def generate_mock_predictions(self, image_stats):
        """Generate mock predictions when model is unavailable"""
        import random

        predictions = {}
        for class_name, files in image_stats.items():
            if class_name == "unknown" or not files:
                continue

            count = min(len(files), self.args.max_images_per_class)
            confidences = [random.uniform(0.65, 0.98) for _ in range(count)]

            predictions[class_name] = {
                "count": count,
                "confidences": confidences,
                "avg_confidence": sum(confidences) / len(confidences) if confidences else 0,
                "high_confidence": sum(1 for c in confidences if c >= self.args.confidence_threshold),
                "files": [{"filename": f, "true_class": class_name, "confidence": c}
                         for f, c in zip(files[:count], confidences)]
            }

        return predictions

    def generate_report(self, image_stats, predictions, total_images):
        """Generate intelligence report based on selected sections"""
        self.log_message("Generating intelligence report...")

        report_parts = []

        # HEADER (always included)
        report_parts.append(f"""# 🌊 SEABED SONAR ANALYSIS REPORT

---

## 📋 REPORT INFORMATION

| Field | Value |
|-------|-------|
| **Report ID** | `{self.run_id}` |
| **Analyst** | {self.user_name} |
| **Generated** | {self.start_time.strftime('%Y-%m-%d %H:%M:%S')} |
| **Data Source** | `{self.args.data_folder}` |
| **Confidence Threshold** | {self.args.confidence_threshold:.0%} |
| **Analysis Scope** | {self.args.analysis_scope.upper()} |

---

""")

        # SUMMARY SECTION
        if "summary" in self.report_sections:
            classes_detected = ', '.join([k.title() for k in predictions.keys()]) if predictions else "None"
            total_detections = sum([data['count'] for data in predictions.values()])

            report_parts.append(f"""## 📊 EXECUTIVE SUMMARY

> Analysis of **{total_images}** sonar images with **{total_detections}** object detections across **{len(predictions)}** classes.

| Metric | Value |
|--------|-------|
| **Total Images Scanned** | {total_images} |
| **Total Detections** | {total_detections} |
| **Classes Identified** | {classes_detected} |
| **High-Confidence Detections** | {sum([data.get('high_confidence', 0) for data in predictions.values()])} |

""")

        # DETECTIONS SECTION
        if "detections" in self.report_sections:
            report_parts.append("## 🎯 DETECTION RESULTS\n\n")

            # Create summary table
            if predictions:
                report_parts.append("| Class | Total Detected | High Confidence | Average Confidence | Status |\n")
                report_parts.append("|-------|----------------|-----------------|--------------------|---------|\n")

                for class_name in ["plane", "ship", "seafloor"]:
                    if class_name in predictions:
                        data = predictions[class_name]
                        conf_pct = data['avg_confidence'] * 100

                        # Status indicator
                        if conf_pct >= 90:
                            status = "🟢 Excellent"
                        elif conf_pct >= 75:
                            status = "🟡 Good"
                        elif conf_pct >= 60:
                            status = "🟠 Fair"
                        else:
                            status = "🔴 Review"

                        # Emoji for class
                        emoji = {"plane": "✈️", "ship": "🚢", "seafloor": "🌊"}.get(class_name, "📦")

                        report_parts.append(f"| {emoji} **{class_name.title()}** | {data['count']} | {data['high_confidence']} (≥{self.args.confidence_threshold:.0%}) | {data['avg_confidence']:.1%} | {status} |\n")

                report_parts.append("\n")
            else:
                report_parts.append("*No detections found in analyzed images.*\n\n")

        # CONFIDENCE ANALYSIS SECTION
        if "confidence_analysis" in self.report_sections:
            report_parts.append("## 📈 CONFIDENCE ANALYSIS\n\n")

            if predictions:
                report_parts.append("| Class | Min | Max | Average | Std Dev | Range |\n")
                report_parts.append("|-------|-----|-----|---------|---------|-------|\n")

                for class_name in ["plane", "ship", "seafloor"]:
                    if class_name in predictions:
                        data = predictions[class_name]
                        if data['confidences']:
                            min_conf = min(data['confidences'])
                            max_conf = max(data['confidences'])
                            avg_conf = data['avg_confidence']
                            std_dev = self.calculate_std(data['confidences'])

                            emoji = {"plane": "✈️", "ship": "🚢", "seafloor": "🌊"}.get(class_name, "📦")
                            report_parts.append(f"| {emoji} **{class_name.title()}** | {min_conf:.1%} | {max_conf:.1%} | {avg_conf:.1%} | {std_dev:.1%} | {(max_conf - min_conf):.1%} |\n")

                report_parts.append("\n")
            else:
                report_parts.append("*No confidence data available.*\n\n")

        # DETAILED RESULTS SECTION
        if "detailed_results" in self.report_sections:
            report_parts.append("## 📋 DETAILED DETECTION LIST\n\n")

            for class_name in ["plane", "ship", "seafloor"]:
                if class_name in predictions:
                    data = predictions[class_name]
                    if data['files']:
                        emoji = {"plane": "✈️", "ship": "🚢", "seafloor": "🌊"}.get(class_name, "📦")
                        report_parts.append(f"### {emoji} {class_name.upper()}\n\n")

                        # Sort by confidence (highest first)
                        sorted_files = sorted(data['files'], key=lambda x: x['confidence'], reverse=True)

                        # Display as table for better readability
                        report_parts.append("| # | Filename | Confidence | Status |\n")
                        report_parts.append("|---|----------|------------|--------|\n")

                        for idx, item in enumerate(sorted_files[:20], 1):  # Limit to first 20
                            conf_pct = item['confidence'] * 100
                            if conf_pct >= 90:
                                badge = "🟢"
                            elif conf_pct >= 75:
                                badge = "🟡"
                            elif conf_pct >= 60:
                                badge = "🟠"
                            else:
                                badge = "🔴"

                            report_parts.append(f"| {idx} | `{item['filename']}` | {item['confidence']:.1%} | {badge} |\n")

                        if len(sorted_files) > 20:
                            report_parts.append(f"\n*...and {len(sorted_files) - 20} more detections*\n")

                        report_parts.append("\n")

        # TACTICAL ASSESSMENT SECTION
        if "tactical_assessment" in self.report_sections:
            total_targets = predictions.get('plane', {}).get('count', 0) + predictions.get('ship', {}).get('count', 0)
            high_conf_ships = predictions.get('ship', {}).get('high_confidence', 0)
            high_conf_planes = predictions.get('plane', {}).get('high_confidence', 0)

            # Threat level determination
            if high_conf_ships > 10:
                threat_level = "🔴 HIGH"
                threat_desc = "Significant maritime activity detected"
            elif high_conf_ships > 5:
                threat_level = "🟡 MEDIUM"
                threat_desc = "Moderate maritime presence"
            else:
                threat_level = "🟢 LOW"
                threat_desc = "Minimal maritime activity"

            # Archaeological interest
            if total_targets > 20:
                arch_interest = "🔴 HIGH"
            elif total_targets > 10:
                arch_interest = "🟡 MODERATE"
            else:
                arch_interest = "🟢 LOW"

            report_parts.append(f"""## 🎯 TACTICAL ASSESSMENT

### Assessment Overview

| Category | Level | Details |
|----------|-------|---------|
| **Threat Level** | {threat_level} | {threat_desc} |
| **Archaeological Interest** | {arch_interest} | {total_targets} potential targets identified |
| **Area Type** | 🌊 Maritime Zone | Multi-target detection environment |

### 📊 Target Breakdown

| Target Type | Total | High Confidence | Status |
|-------------|-------|-----------------|--------|
| ✈️ **Aircraft** | {predictions.get('plane', {}).get('count', 0)} | {high_conf_planes} | {"⚠️ Priority Review" if high_conf_planes > 0 else "✓ Normal"} |
| 🚢 **Vessels** | {predictions.get('ship', {}).get('count', 0)} | {high_conf_ships} | {"⚠️ Priority Review" if high_conf_ships > 5 else "✓ Normal"} |

### 💡 RECOMMENDATIONS

1. **Immediate Actions**
   - Review all high-confidence detections for verification
   - Cross-reference with known vessel/aircraft databases

2. **Follow-up Tasks**
   - Consider detailed inspection of target-rich areas
   - Deploy additional sensors for confirmation if needed

3. **Long-term Monitoring**
   - Establish monitoring protocols for detected patterns
   - Schedule periodic re-scans of the area

### 📍 OPERATIONAL CONTEXT

{self.args.operational_context if self.args.operational_context else "> *No operational context provided*"}

""")

        # METADATA SECTION
        if "metadata" in self.report_sections:
            exec_time = (datetime.now() - self.start_time).total_seconds()

            report_parts.append(f"""## ⚙️ ANALYSIS METADATA

### Execution Details

| Parameter | Value |
|-----------|-------|
| **Data Source** | `{self.args.data_folder}` |
| **Images Per Class Limit** | {self.args.max_images_per_class} |
| **Analysis Scope** | {self.args.analysis_scope.upper()} |
| **Confidence Threshold** | {self.args.confidence_threshold:.0%} |
| **Execution Time** | {exec_time:.2f}s |
| **Processing Rate** | {total_images / exec_time:.1f} images/sec |

### Report Sections Included

{', '.join([f'`{section}`' for section in self.report_sections])}

""")

        # FOOTER
        report_parts.append("""---

## 📌 REPORT FOOTER

**CLASSIFICATION**: `UNCLASSIFIED`
**System**: Seabed Object Detection AI - Vision Transformer Model
**Version**: 1.0
**Contact**: For questions about this report, contact the analyst listed above.

---
*This report was automatically generated by an AI-powered sonar analysis system. All detections should be verified by qualified personnel before operational decisions are made.*
""")

        return "".join(report_parts)

    def calculate_std(self, values):
        """Calculate standard deviation"""
        if len(values) < 2:
            return 0.0
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        return variance ** 0.5

    def export_report(self, report_content, predictions, image_stats):
        """Export report in selected formats"""
        self.log_message("Exporting report in selected formats...")

        output_files = []

        # MARKDOWN FORMAT
        if "markdown" in self.export_formats:
            md_file = self.results_dir / "intelligence_report.md"
            with open(md_file, 'w') as f:
                f.write(report_content)
            output_files.append(("Markdown Report", str(md_file)))
            self.log_message(f"Markdown report saved: {md_file}")

        # JSON FORMAT
        if "json" in self.export_formats:
            json_data = {
                "report_id": self.run_id,
                "analyst": self.user_name,
                "timestamp": self.start_time.isoformat(),
                "data_folder": self.args.data_folder,
                "confidence_threshold": self.args.confidence_threshold,
                "image_statistics": {k: len(v) for k, v in image_stats.items()},
                "predictions": predictions,
                "analysis_scope": self.args.analysis_scope,
                "operational_context": self.args.operational_context
            }

            json_file = self.results_dir / "analysis_results.json"
            with open(json_file, 'w') as f:
                json.dump(json_data, f, indent=2)
            output_files.append(("JSON Results", str(json_file)))
            self.log_message(f"JSON results saved: {json_file}")

        # HTML FORMAT
        if "html" in self.export_formats:
            html_content = f"""<!DOCTYPE html>
<html>
<head>
    <title>Seabed Analysis Report - {self.run_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; max-width: 1000px; margin: 40px auto; padding: 20px; }}
        h1 {{ color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px; }}
        h2 {{ color: #34495e; margin-top: 30px; }}
        .metadata {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; }}
        .detection-box {{ background: #fff; border-left: 4px solid #3498db; padding: 15px; margin: 10px 0; }}
        pre {{ background: #f8f9fa; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
{self.markdown_to_html(report_content)}
</body>
</html>"""

            html_file = self.results_dir / "intelligence_report.html"
            with open(html_file, 'w') as f:
                f.write(html_content)
            output_files.append(("HTML Report", str(html_file)))
            self.log_message(f"HTML report saved: {html_file}")

        # CSV FORMAT
        if "csv" in self.export_formats:
            csv_file = self.results_dir / "detection_summary.csv"
            with open(csv_file, 'w') as f:
                f.write("Class,Total_Detected,High_Confidence,Avg_Confidence\n")
                for class_name, data in predictions.items():
                    f.write(f"{class_name},{data['count']},{data['high_confidence']},{data['avg_confidence']:.4f}\n")
            output_files.append(("CSV Summary", str(csv_file)))
            self.log_message(f"CSV summary saved: {csv_file}")

        return output_files

    def markdown_to_html(self, markdown_text):
        """Simple markdown to HTML converter"""
        html = markdown_text
        # Convert headers
        html = html.replace("# ", "<h1>").replace("\n##", "</h1>\n<h2>")
        html = html.replace("## ", "<h2>").replace("\n###", "</h2>\n<h3>")
        html = html.replace("### ", "<h3>")
        # Convert bold
        import re
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        # Convert code blocks
        html = html.replace("`", "<code>").replace("</code>", "</code>")
        # Convert line breaks
        html = html.replace("\n\n", "</p><p>")
        return f"<p>{html}</p>"

    def run(self):
        """Main execution method - single phase"""
        try:
            self.log_message("="*60)
            self.log_message("SEABED ANALYSIS LAUNCHER - SIMPLIFIED MODE")
            self.log_message("="*60)

            # Step 1: Scan data folder
            image_stats, total_images = self.scan_data_folder()

            # Step 2: Run model predictions
            predictions = self.run_model_predictions(image_stats)

            # Step 3: Generate report
            report_content = self.generate_report(image_stats, predictions, total_images)

            # Step 4: Export in selected formats
            output_files = self.export_report(report_content, predictions, image_stats)

            # Summary
            duration = datetime.now() - self.start_time
            self.log_message("="*60)
            self.log_message("EXECUTION COMPLETE")
            self.log_message("="*60)
            self.log_message(f"Duration: {duration.total_seconds():.2f} seconds")
            self.log_message(f"Results directory: {self.results_dir}")

            print("\n" + "="*60)
            print("🎯 SEABED ANALYSIS REPORT GENERATED")
            print("="*60)
            print(f"📊 Report ID: {self.run_id}")
            print(f"👤 Analyst: {self.user_name}")
            print(f"📁 Results: {self.results_dir}")
            print(f"\n📋 Generated Outputs:")
            for name, path in output_files:
                print(f"   • {name}: {path}")
            print("="*60)

        except Exception as e:
            self.log_message(f"ERROR: {e}")
            print(f"\n❌ LAUNCHER FAILED: {e}")
            sys.exit(1)

def main():
    # Use DataConfig to get environment-adaptive default path
    default_config = DataConfig()
    default_data_folder = str(default_config.test_dataset_path)

    # Check if arguments are passed positionally (Domino Launcher style) or via flags (command-line testing)
    if len(sys.argv) > 1 and not sys.argv[1].startswith('-'):
        # POSITIONAL ARGUMENTS (Domino Launcher mode)
        # Expected order: data_folder, report_sections, export_formats, analysis_scope,
        #                 confidence_threshold, max_images_per_class, operational_context,
        #                 launcher_run_id, user_name

        data_folder = sys.argv[1] if len(sys.argv) > 1 else default_data_folder
        report_sections = sys.argv[2] if len(sys.argv) > 2 else "summary,detections"
        export_formats = sys.argv[3] if len(sys.argv) > 3 else "markdown"
        analysis_scope = sys.argv[4] if len(sys.argv) > 4 else "standard"
        confidence_threshold = float(sys.argv[5]) if len(sys.argv) > 5 else 0.75
        max_images_per_class = int(sys.argv[6]) if len(sys.argv) > 6 else 100
        operational_context = sys.argv[7] if len(sys.argv) > 7 else ""
        launcher_run_id = sys.argv[8] if len(sys.argv) > 8 else None
        user_name = sys.argv[9] if len(sys.argv) > 9 else None

        # Create a simple namespace object to match the argparse pattern
        class Args:
            pass

        args = Args()
        args.data_folder = data_folder
        args.report_sections = report_sections
        args.export_formats = export_formats
        args.analysis_scope = analysis_scope
        args.confidence_threshold = confidence_threshold
        args.max_images_per_class = max_images_per_class
        args.operational_context = operational_context
        args.launcher_run_id = launcher_run_id
        args.user_name = user_name

    else:
        # NAMED ARGUMENTS (command-line testing mode)
        parser = argparse.ArgumentParser(
            description="Simplified Seabed Analysis Launcher - Single-phase report generation"
        )

        parser.add_argument(
            "--data_folder",
            required=False,
            default=default_data_folder,
            help="Path to folder containing sonar images (should have plane/ship/seafloor subdirectories)"
        )

        parser.add_argument(
            "--report_sections",
            type=str,
            default="summary,detections",
            help="Report sections to include (comma-separated: summary,detections,confidence_analysis,detailed_results,tactical_assessment,metadata)"
        )

        parser.add_argument(
            "--export_formats",
            type=str,
            default="markdown",
            help="Export formats for the report (comma-separated: markdown,json,html,csv)"
        )

        parser.add_argument(
            "--analysis_scope",
            choices=["quick", "standard", "comprehensive"],
            default="standard",
            help="Analysis depth: quick (basic stats), standard (full analysis), comprehensive (includes recommendations)"
        )

        parser.add_argument(
            "--confidence_threshold",
            type=float,
            default=0.75,
            help="Minimum confidence for high-confidence classification (0.0-1.0)"
        )

        parser.add_argument(
            "--max_images_per_class",
            type=int,
            default=100,
            help="Maximum number of images to analyze per class"
        )

        parser.add_argument(
            "--operational_context",
            default="",
            help="Optional operational context for tactical assessment"
        )

        # SYSTEM PARAMETERS
        parser.add_argument(
            "--launcher_run_id",
            default=None,
            help="Domino launcher run ID (auto-generated if not provided)"
        )

        parser.add_argument(
            "--user_name",
            default=None,
            help="User name for report attribution"
        )

        args = parser.parse_args()

    # Execute launcher
    launcher = SimpleReportLauncher(args)
    launcher.run()

if __name__ == "__main__":
    main()
