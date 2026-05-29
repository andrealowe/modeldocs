# SIMPLIFIED SEABED ANALYSIS LAUNCHER
## Single-Phase Report Generation

### OVERVIEW

This simplified launcher generates intelligence reports from pre-existing sonar images in a specified folder. It's a **single-phase** workflow that scans images, runs predictions, and generates customizable reports in multiple formats.

---

## DOMINO LAUNCHER CONFIGURATION

### **Launcher Setup**
1. **Go to**: Deployments > Launchers > New Launcher
2. **Title**: "Seabed Sonar Report Generator"
3. **Description**: "Generate intelligence reports from sonar image folders with customizable sections and formats"
4. **Command**:
```bash
python /mnt/src/launchers/simple_report_launcher.py --data_folder "${data_folder}" --report_sections ${report_sections} --export_formats ${export_formats} --analysis_scope ${analysis_scope} --confidence_threshold ${confidence_threshold} --max_images_per_class ${max_images_per_class} --operational_context "${operational_context}" --launcher_run_id ${DOMINO_RUN_ID} --user_name ${DOMINO_STARTING_USERNAME}
```

---

## FORM CONTROLS

### 1. **DATA FOLDER** *(Text Input)*
- **Parameter**: `--data_folder`
- **Type**: Text
- **Required**: Yes
- **Label**: "Data Folder Path"
- **Description**: "Path to folder containing sonar images"
- **Default**: Uses `DataConfig.test_dataset_path` (environment-adaptive: `/domino/datasets/local/Seabed-Object-Detection/test_set` or `/mnt/data/Seabed-Object-Detection/test_set`)
- **Help Text**: "Folder should contain plane/, ship/, and seafloor/ subdirectories with PNG/JPG images"

### 2. **REPORT SECTIONS** *(Text Input)*
- **Parameter**: `--report_sections`
- **Type**: Text (Comma-separated values)
- **Label**: "Report Sections to Include"
- **Description**: "Comma-separated list of report sections"
- **Options**: `summary,detections,confidence_analysis,detailed_results,tactical_assessment,metadata`
  - `summary` - Executive Summary (image counts, classes detected)
  - `detections` - Detection Results (counts, confidence by class)
  - `confidence_analysis` - Confidence Analysis (ranges, statistics)
  - `detailed_results` - Detailed Detection List (individual files)
  - `tactical_assessment` - Tactical Assessment (threat level, recommendations)
  - `metadata` - Analysis Metadata (execution details)
- **Default**: `summary,detections`
- **Example**: `summary,detections,tactical_assessment`

### 3. **EXPORT FORMATS** *(Text Input)*
- **Parameter**: `--export_formats`
- **Type**: Text (Comma-separated values)
- **Label**: "Export Formats"
- **Description**: "Comma-separated list of export formats"
- **Options**: `markdown,json,html,csv`
  - `markdown` - Markdown Report (.md)
  - `json` - JSON Data (.json)
  - `html` - HTML Report (.html)
  - `csv` - CSV Summary (.csv)
- **Default**: `markdown`
- **Example**: `markdown,html,json`

### 4. **ANALYSIS SCOPE** *(Dropdown)*
- **Parameter**: `--analysis_scope`
- **Type**: Select (Dropdown)
- **Label**: "Analysis Depth"
- **Options**: `quick, standard, comprehensive`
  - `quick` - Quick Analysis (basic statistics only)
  - `standard` - Standard Analysis (full detection results)
  - `comprehensive` - Comprehensive Analysis (includes tactical recommendations)
- **Default**: `standard`

### 5. **CONFIDENCE THRESHOLD** *(Number Slider)*
- **Parameter**: `--confidence_threshold`
- **Type**: Select
- **Label**: "High-Confidence Threshold"
- **Options**: `0.75, 0.85, 0.95`
- **Description**: "Minimum confidence score to classify as 'high confidence'"

### 6. **MAX IMAGES PER CLASS** *(Number Input)*
- **Parameter**: `--max_images_per_class`
- **Type**: Number
- **Label**: "Max Images Per Class"
- **Min**: 10
- **Max**: 500
- **Default**: 100
- **Description**: "Limit analysis to first N images per class (for faster execution)"

### 7. **OPERATIONAL CONTEXT** *(Text Area)*
- **Parameter**: `--operational_context`
- **Type**: Text Area
- **Label**: "Operational Context (Optional)"
- **Placeholder**: "Mission details, search area coordinates, objectives..."
- **Description**: "Optional context for tactical assessment section"

## ALTERNATIVE SETUP METHOD

Select `Switch to JSON Edit Mode` in the top right corner. Then paste the following into the cell, making sure to change the `"DATA_FOLDER` `defaultValue` to the location of your dataset. 

```
{
  "name" : "Seabed Sonar Report Generator",
  "description" : "Generate intelligence reports from sonar image folders with customizable sections and formats",
  "command" : "src/launchers/simple_report_launcher.py ${DATA_FOLDER} ${REPORT_SECTIONS} ${EXPORT_FORMAT} ${ANALYSIS} ${THRESHOLD} ${MAX_IMAGES} ${CONTEXT}",
  "valuePassType" : "CommandLineSubstitutionPass",
  "parameters" : [ {
    "name" : "DATA_FOLDER",
    "shouldQuoteValue" : true,
    "parameterType" : "Text",
    "defaultValue" : "/domino/datasets/local/Seabed-Object-Detection/test_set",
    "description" : "Path to folder containing sonar images (e.g., /mnt/data/Seabed-Object-Detection/test_set)",
    "allowedValues" : [ ]
  }, {
    "name" : "REPORT_SECTIONS",
    "shouldQuoteValue" : true,
    "parameterType" : "MultiSelect",
    "defaultValue" : "",
    "description" : "Report Sections to Include",
    "allowedValues" : [ {
      "value" : "summary"
    }, {
      "value" : "detections"
    }, {
      "value" : "detailed_results"
    }, {
      "value" : "tactical_assessment"
    }, {
      "value" : "metadata"
    } ]
  }, {
    "name" : "EXPORT_FORMAT",
    "shouldQuoteValue" : true,
    "parameterType" : "MultiSelect",
    "defaultValue" : "markdown,json,html,csv",
    "description" : "format for report",
    "allowedValues" : [ {
      "value" : "markdown"
    }, {
      "value" : "json"
    }, {
      "value" : "html"
    }, {
      "value" : "csv"
    } ]
  }, {
    "name" : "ANALYSIS",
    "shouldQuoteValue" : true,
    "parameterType" : "MultiSelect",
    "defaultValue" : "quick, standard, comprehensive",
    "description" : "Analysis Depth",
    "allowedValues" : [ {
      "value" : "quick"
    }, {
      "value" : "standard"
    }, {
      "value" : "comprehensive"
    } ]
  }, {
    "name" : "THRESHOLD",
    "shouldQuoteValue" : true,
    "parameterType" : "Select",
    "defaultValue" : "",
    "description" : "Minimum confidence score to classify as 'high confidence",
    "allowedValues" : [ {
      "value" : "0.75"
    }, {
      "value" : "0.85"
    }, {
      "value" : "0.95"
    } ]
  }, {
    "name" : "MAX_IMAGES",
    "shouldQuoteValue" : true,
    "parameterType" : "Text",
    "defaultValue" : "100",
    "description" : "Limit analysis to first N images per class (for faster execution)",
    "allowedValues" : [ ]
  }, {
    "name" : "CONTEXT",
    "shouldQuoteValue" : true,
    "parameterType" : "Text",
    "defaultValue" : "Mission details, search area coordinates, objectives",
    "description" : "Optional context for tactical assessment section",
    "allowedValues" : [ ]
  } ],
  "environmentId" : "68db0d0f7db7d9606c3d5c11",
  "hardwareTierId" : "small-k8s",
  "externalVolumeMountIds" : null,
  "netAppVolumeIds" : null
}
```

---

## COMMAND EXECUTION

```bash
python /mnt/launcher_scripts/simple_report_launcher.py \
  --data_folder "${data_folder}" \
  --report_sections ${report_sections} \
  --export_formats ${export_formats} \
  --analysis_scope ${analysis_scope} \
  --confidence_threshold ${confidence_threshold} \
  --max_images_per_class ${max_images_per_class} \
  --operational_context "${operational_context}" \
  --launcher_run_id ${DOMINO_RUN_ID} \
  --user_name ${DOMINO_STARTING_USERNAME}
```

---

## WORKFLOW

### **Single Phase: Generate Report**

1. **Scan Data Folder** - Discovers images in plane/ship/seafloor subdirectories
2. **Run Predictions** - Executes ViT model inference on discovered images
3. **Generate Report** - Creates report with selected sections
4. **Export** - Saves report in selected formats (MD/JSON/HTML/CSV)

**Total Execution Time**: ~1-3 minutes (depending on image count and max_images_per_class)

---

## OUTPUT STRUCTURE

```
cleaned_data/launcher_results/{DOMINO_RUN_ID}/
├── intelligence_report.md        # Markdown report (if selected)
├── intelligence_report.html      # HTML report (if selected)
├── analysis_results.json         # JSON data (if selected)
├── detection_summary.csv         # CSV summary (if selected)
└── execution_log.txt             # Execution log
```

---

## USE CASE EXAMPLES

### **Example 1: Quick Executive Briefing**
**User**: Naval intelligence officer needing quick summary
**Configuration**:
- Data Folder: `/mnt/data/Seabed-Object-Detection/test_set`
- Report Sections: `summary`, `detections`, `tactical_assessment`
- Export Formats: `markdown`, `html`
- Analysis Scope: `quick`
- Max Images: 50

**Result**: Fast 1-minute execution with executive summary and threat assessment in readable formats

---

### **Example 2: Comprehensive Analysis for Research**
**User**: Marine archaeologist analyzing survey data
**Configuration**:
- Data Folder: `/mnt/data/Seabed-Object-Detection/unbalanced_training_validation_set`
- Report Sections: `summary`, `detections`, `confidence_analysis`, `detailed_results`, `metadata`
- Export Formats: `markdown`, `json`, `csv`
- Analysis Scope: `comprehensive`
- Max Images: 200

**Result**: Detailed 3-minute analysis with full statistics, individual file results, and structured data exports

---

### **Example 3: API Integration Report**
**User**: Port security system requiring JSON data feed
**Configuration**:
- Data Folder: `/mnt/data/Seabed-Object-Detection/balanced_training_validation_set`
- Report Sections: `summary`, `detections`
- Export Formats: `json`, `csv`
- Analysis Scope: `standard`
- Confidence Threshold: 0.85

**Result**: Structured JSON and CSV outputs for system integration with strict confidence filtering

---

### **Example 4: All-Inclusive Intelligence Package**
**User**: Search & rescue coordinator needing complete documentation
**Configuration**:
- Data Folder: `/mnt/data/emergency_search_area`
- Report Sections: *[ALL SELECTED]*
- Export Formats: *[ALL SELECTED]*
- Analysis Scope: `comprehensive`
- Operational Context: "Emergency search operation, Mediterranean Sea, coordinates 35.5°N 14.5°E"

**Result**: Complete intelligence package with all report sections in all formats for multi-audience distribution

---

## MULTI-SELECT PARAMETER BENEFITS

### **Report Sections Multi-Select**
✅ **Flexibility**: Users choose only relevant sections
✅ **Performance**: Fewer sections = faster execution
✅ **Customization**: Different audiences need different details
✅ **Scalability**: Easy to add new sections without UI changes

**Example Use Cases**:
- **Executive**: `summary` + `tactical_assessment` only
- **Analyst**: `detections` + `confidence_analysis` + `detailed_results`
- **Researcher**: `summary` + `detections` + `metadata`

### **Export Formats Multi-Select**
✅ **Multi-Audience**: One execution serves multiple consumers
✅ **Integration**: JSON for APIs, CSV for Excel, HTML for presentations
✅ **Documentation**: Markdown for version control, HTML for sharing
✅ **Efficiency**: Generate all needed formats in single run

**Example Use Cases**:
- **Command Briefing**: `markdown` + `html` for presentation
- **System Integration**: `json` + `csv` for data pipelines
- **Archive**: `markdown` + `json` for long-term storage

---

## TECHNICAL NOTES

### **Data Folder Requirements**:
- Must exist and be accessible
- Should contain class subdirectories: `plane/`, `ship/`, `seafloor/`
- Supports PNG, JPG, JPEG image formats
- Can also scan root directory for uncategorized images

### **Model Integration**:
- Uses existing `predict.py` for inference
- Falls back to mock predictions if model unavailable
- Respects `max_images_per_class` limit for performance

### **Report Customization**:
- Modular section generation (easy to add new sections)
- Multi-format export from single execution
- Professional HTML styling with CSS
- CSV exports for Excel integration

### **Error Handling**:
- Validates data folder existence
- Graceful degradation if model fails
- Comprehensive logging to execution_log.txt
- User-friendly error messages

---

## BUSINESS VALUE

### **For Non-Technical Users**
- ✅ **Simplicity**: Point to folder, select options, get report
- ✅ **Speed**: Results in minutes, not hours
- ✅ **Flexibility**: Choose exactly what you need
- ✅ **Multi-Format**: Single execution serves all needs

### **For Organizations**
- ✅ **Self-Service**: Reduces analyst bottlenecks
- ✅ **Standardization**: Consistent report format
- ✅ **Auditability**: Complete execution logs
- ✅ **Scalability**: Analyze any dataset without code changes

### **For Maritime Operations**
- ✅ **Rapid Intelligence**: Quick threat assessments
- ✅ **Tactical Insights**: Automated recommendations
- ✅ **Flexible Reporting**: Adapt to mission needs
- ✅ **Data Portability**: Multiple export formats for different systems

---

**CLASSIFICATION**: UNCLASSIFIED
