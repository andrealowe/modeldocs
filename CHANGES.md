# ModelDocs — Session Changes

Changes made during this working session, grouped by area.

---

## 1. UI Polish

### Domino Logo & Template Label
- Increased Domino logo height from `32px` to `40px` in the top-left header
- Matched the **Template** label font style (size, weight, color) to the **Context sources** label for visual consistency
- Added additional top margin to the Template heading for better spacing

### Model Banner
- Updated model banner background from teal to the Domino design system colors:
  `#EDECFB` (lavender background), `#C9C5F2` (border), `#3B3BD3` (left accent)

### Notebook / Workspace Buttons
- Changed both notebook buttons from a vertical stack to a horizontal `flex-direction: row` layout
- Shortened label from "View in Workspace" to "Workspace"
- Added `type="button"` to both buttons to prevent accidental form submission
- Changed the Refresh button from `primary` to `secondary` style

### Output Panel & History Table
- Increased output panel padding
- Tightened history table font size to `12px` with a `2px` bottom border on headers
- Aligned status badges using `inline-flex` with `border-radius: 3px`
- Set history action bar to `justify-content: space-between` with a top border separator

### Context Sources Label
- Updated **Experiments** description from "MLflow runs and logged metrics" to "Domino experiment runs and logged metrics"

---

## 2. Report Generation Fixes

### Bold Body Text (Mammoth)
- Fixed all report body text rendering as bold in the HTML viewer
- Root cause: Word Normal-style `<w:b>` elements cause mammoth to treat all runs as bold
- Fix: added CSS overrides — `p strong, p b, p span { font-weight: normal !important }` — with a carve-out to keep table cell bold text (`td p strong { font-weight: 600 !important }`)

### Section Title Prefix Appearing in Body
- Fixed section titles leaking into body paragraphs
- The builder now checks both `result.plan.title` and `result.plan.name`, and handles multiple separator patterns (`:`, ` —`, ` -`, `\n`)

### Key Findings Order & Callout Styling
- Enforced section ordering in the LLM prompt: Key Findings bullet list first, then narrative, then visuals, then tables, then Recommended Actions
- Callout boxes use a 1-column table with:
  - **Key Findings:** lavender `#E8EBF9` background, `#1F4E79` navy left border
  - **Recommended Actions:** green `#E2F0E8` background, `#2E7D32` left border

### Shorter Paragraphs
- Updated prompt instructions to enforce "EXACTLY 1–2 paragraphs per section — NO MORE. Each paragraph: 2–3 sentences max."

### Charts When No MLflow Metrics
- Fixed reports generating with no figures when there are no MLflow experiment runs
- `_generate_chart()` now falls back to: (1) numeric hyperparameters from code as a bar chart, or (2) feature group counts from code-scanned features

### Code Line Numbers in Report
- Code evidence citations now include `lines N–M` in the Source line when `start_line` / `end_line` are available from the scanner

---

## 3. Demo Report — Pre-Built Word Document

Built a complete, statically-generated compliance report (`NBT-CR-EL-007_Compliance_Report_v7_0.docx`) based on the real Northbridge Trust Expected Loss Model source materials.

### Content
All 10 sections matching the ModelDocs report template:
1. Executive Summary
2. Model Identification & Inventory
3. Regulatory Classification
4. Conceptual Soundness
5. Data Lineage & Quality
6. Independent Validation
7. Ongoing Performance Monitoring
8. Limitations & Compensating Controls
9. Governance & Approvals
10. Appendix

### Styling
- Navy headings with underline border rules (matching `builder.py` patterns)
- Key Findings callout boxes (lavender) and Recommended Actions (green) in every section
- Data tables with navy headers and alternating row shading
- Code reference lines with `[filename  lines N–M]` format throughout
- Title page for Northbridge Trust

### Figures (4 embedded matplotlib charts)
- **Figure 1:** LGD as a function of LTV (annotated curve)
- **Figure 2:** Basel III LTV Risk-Weight Schedule (bar chart)
- **Figure 3:** Portfolio Reference-Run Metrics (EL undiscounted / discounted / RWA)
- **Figure 4:** Population Stability Index by input feature (bar chart)

### Generation Script
`auto_model_docs/build_demo_report.py` — standalone script that regenerates the `.docx` from scratch. Run with `python auto_model_docs/build_demo_report.py`.

### Companion Notebook
`uploads/NBT-CR-EL-007_Compliance_Report.ipynb` — rewritten to contain only section headers, tables (as `pd.DataFrame` cells), and the four figures as runnable matplotlib code. No prose narrative.

---

## 4. Demo Mode — App Integration

### Simulated Job Flow
When `MODELDOCS_DEMO_MODE=true` (the current default), clicking **Generate Documentation**:
1. Immediately shows a **RUNNING** row in the job history panel
2. After 15 seconds transitions to **SUCCEEDED** with View and Download buttons
3. No real job is submitted; no LLM calls are made

Controlled by `MODELDOCS_DEMO_MODE` environment variable. Set to `false` to re-enable real job submission.

**Files changed:** `studio/scripts.py`
- `var DEMO_MODE = __DEMO_MODE__` injected at JS top
- Form submit handler short-circuits when `DEMO_MODE` is true
- `_demoJob` variable persists the fake job state so the 10-second polling interval cannot overwrite it

### Demo Output Routes (`studio/routes_api.py`)
Four new server routes serving the pre-built demo files:

| Route | Purpose |
|---|---|
| `/demo/report-render` | Renders pre-built `.docx` as HTML via mammoth |
| `/demo/report-markdown` | Returns pre-built `.docx` as Markdown for the Edit pane |
| `/demo/report-docx` | Downloads the pre-built `.docx` |
| `/demo/report-ipynb` | Downloads the pre-built `.ipynb` |

`openDocViewer()` in the JS checks for the `__demo__` sentinel dataset path and routes to these endpoints instead of the real `job-render` / `job-notebook` / `job-markdown` routes.

### Demo File Location
Files live at `auto_model_docs/studio/demo/` (inside the package, committed to git) so they are always present regardless of which container or environment the app runs in.

`_ensure_demo_files()` runs at app startup (`web_app_studio.py`) and regenerates the files from `build_demo_report.py` if they are somehow missing.

`_DEMO_DIR` is resolved at module import time (not inside a function) so the path is stable across all deployment contexts.

### Callout Box Colors in HTML Viewer
A JavaScript post-processor runs in the rendered HTML page after load. It finds all single-column tables, checks the first paragraph's text against the known callout titles, and applies inline background and border styles:
- Key Findings → `#E8EBF9` background, `#1F4E79` left border
- Recommended Actions → `#E2F0E8` background, `#2E7D32` left border

This applies to both the demo report and any real generated report (both routes use the shared `_docx_to_html_response()` helper).

---

## Files Changed

| File | What changed |
|---|---|
| `auto_model_docs/build_demo_report.py` | New — standalone script to generate the demo `.docx` |
| `auto_model_docs/studio/demo/NBT-CR-EL-007_Compliance_Report_v7_0.docx` | New — pre-built demo Word report |
| `auto_model_docs/studio/demo/NBT-CR-EL-007_Compliance_Report.ipynb` | New — pre-built demo notebook |
| `uploads/NBT-CR-EL-007_Compliance_Report.ipynb` | Rewritten — tables and figures only, no prose |
| `auto_model_docs/studio/routes_api.py` | Added 4 demo routes, `_docx_to_html_response()` helper, `_DEMO_DIR` at module level, callout JS post-processor |
| `auto_model_docs/studio/scripts.py` | Added `DEMO_MODE` flag, demo job simulation, `_demoJob` state, demo URL routing in `openDocViewer` and `_setViewerMode` |
| `auto_model_docs/web_app_studio.py` | Added `_ensure_demo_files()` startup hook |
| `auto_model_docs/studio/styles.py` | Logo size, Template label, model banner colors, button and table styles |
| `auto_model_docs/autodoc/generation/builder.py` | Section title stripping, bibliography line numbers |
| `auto_model_docs/autodoc/generation/generator.py` | Chart fallback when no MLflow metrics, code evidence line numbers |
| `auto_model_docs/autodoc/llm/prompts.py` | Section ordering (Key Findings first), paragraph length limits |
| `auto_model_docs/domino_client.py` | Code root defaults to first repo instead of `/mnt/code` |
| `auto_model_docs/web_app_studio.py` | Experiments label wording |
| `PRODUCTION_GAPS.md` | New — production readiness gap analysis |
| `CHANGES.md` | New — this document |
