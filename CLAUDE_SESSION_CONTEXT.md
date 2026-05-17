# Claude Code Session Context — ModelDocs Demo Branch

**Branch:** `andrea-demo-video`
**Remote:** `andrea` → `https://github.com/andrealowe/modeldocs.git`
**Base repo:** `https://github.com/dominodatalab/AutoDocumentation_Extension.git` (origin, no write access)
**Domino project:** `https://fsi-demo.domino-eval.com/integration-test/ModelDocs`

---

## What this project is

**ModelDocs** — a Domino Extension app (FastHTML/Python) that generates model documentation (compliance reports, etc.) using Claude + Domino's full model context (code, experiment runs, governance evidence). It was forked/renamed from the "Auto Model Docs" app and customized for a demo video.

The app runs inside Domino as a notebook proxy app (port 8889) and submits Domino Jobs for actual document generation. In demo/preview mode it mocks the output.

---

## Key files changed in this branch

All changes live under `auto_model_docs/`:

| File | What changed |
|---|---|
| `web_app_studio.py` | Fully rebuilt as "ModelDocs" — model context banner, inline YAML template editor, output format selector (Word/Markdown/LaTeX), demo mock flow |
| `studio/styles.py` | ~600 lines of new CSS: model context banner, context pills, template editor panel, output format selector, demo progress card, demo output card |
| `studio/scripts.py` | `_AD_APP_BASE` detection updated for notebook proxy URLs; `runJobJsonPayloadFromMainForm()` includes `spec_content`; demo mode detection and mock flow JS |
| `studio/state.py` | Added `spec_content: str = ""` to `JobRequest`; added `_resolve_request_model_id()` and `_resolve_request_model_version_id()` helpers |
| `studio/job_engine.py` | `_validate_job_inputs()` accepts inline spec content as alternative to file path |
| `studio/routes_job.py` | Saves inline spec content to dataset as timestamped file before Domino job submission |
| `studio/routes_api.py` | Added `/api/template-content`, `/api/download-compliance-template`, `/demo/report-docx`, `/demo/report-ipynb` endpoints |
| `studio/ui_components.py` | `validate_studio_domino_compute_environment()` silently skips validation in dev/preview (no env vars set) |
| `compliance_report_spec.yaml` | New file — 10-section compliance report template, pre-loaded as default in the inline editor |

---

## Architecture overview

```
User browser
    │
    ├── FastHTML app (web_app_studio.py) — runs on port 8889 in Domino notebook proxy
    │       ├── Inline YAML template editor (textarea, pre-filled server-side)
    │       ├── Model context banner (modelId + modelVersionId from query params)
    │       ├── Output format selector (Word/Markdown/LaTeX — UI only, not yet wired)
    │       └── Generate Docs button → POST /run
    │
    ├── /run (routes_job.py)
    │       ├── In demo mode: skipped — JS intercepts and shows mock output
    │       ├── Saves inline spec YAML to Domino dataset (timestamped file)
    │       └── Submits Domino Job with spec_path pointing to saved file
    │
    └── /api/* (routes_api.py)
            ├── /api/hardware-tiers
            ├── /api/datasets
            ├── /api/template-content?name=compliance|default
            ├── /demo/report-docx  → serves uploads/NBT-CR-EL-007_Compliance_Report_v7_0.docx
            └── /demo/report-ipynb → serves uploads/NBT-CR-EL-007_Compliance_Report.ipynb
```

---

## Demo mode behavior

Demo mode activates when:
- URL pathname contains `/notebookSession` or `/proxy/` (Domino notebook proxy), OR
- Query param `?demo=` is present (and not `false`/`0`)

When active:
- The Generate Docs button is intercepted by a JS capture-phase listener (before the main HTMX handler)
- A 5-step progress animation plays (~10s total): "Scanning source code…", "Reading Domino experiment runs…", "Extracting governance evidence…", "Drafting compliance sections…", "Finalizing document…"
- Demo output card appears with COMPLETED badge and download buttons for `.docx` and `.ipynb`
- Download buttons hit `/demo/report-docx` and `/demo/report-ipynb` which serve files from `uploads/`

---

## How to run the app locally

```bash
cd /mnt/code
pip install -e auto_model_docs/  # if not already installed
python auto_model_docs/web_app_studio.py
# or via the shell script:
bash auto_model_docs/app_studio.sh
```

App starts on port 8889. Open `http://localhost:8889/?demo=1` to test demo mode.

To test as a Domino Extension opening from a Model context:
```
http://localhost:8889/?projectId=<id>&modelId=<id>&modelVersionId=<id>&demo=1
```

---

## Git workflow

```bash
# This repo has two remotes:
git remote -v
# andrea  https://github.com/andrealowe/modeldocs.git  ← push here
# origin  https://github.com/dominodatalab/AutoDocumentation_Extension.git  ← no write access

# Push changes:
git push andrea andrea-demo-video

# Pull from upstream (if needed):
git fetch origin
```

---

## Known gotchas

- **FastHTML router and dots in paths**: Routes like `/demo/report.docx` silently 404 — the router treats the dot as a file extension. Always use hyphens: `/demo/report-docx`.
- **Demo mode detection regex**: The URL in Domino looks like `/r/notebookSession/<id>/proxy/8889/`. The JS uses `.indexOf('/notebookSession')` (not a tight regex) to detect this reliably.
- **Inline spec flow**: When user edits the YAML inline (no file picker), JS sets `spec_path = "__inline__"` and sends `spec_content` in the POST body. `routes_job.py` saves it to the dataset as `_inline_spec_<timestamp>.yaml` before submitting the Domino job.
- **Environment validation**: `validate_studio_domino_compute_environment()` returns `[]` silently when `DOMINO_ENVIRONMENT_ID`/`DOMINO_ENVIRONMENT_REVISION_ID` aren't set (dev/preview context). Previously it was returning an error banner that blocked the app.
- **"Domino experiments" not "MLflow experiments"**: The UI intentionally says "Domino experiments" throughout — don't revert this.

---

## Styling notes

CSS lives in `auto_model_docs/studio/styles.py` as a Python string `STUDIO_CSS`.

The last session reviewed `felix-ui-improvements` branch and selectively incorporated:
- `--warning: #CCB718` (brighter yellow, matches felix)
- Select input padding `0 2rem 0 14px` + caret at `right 0.75rem` (felix values)
- `button.primary:disabled` uses `opacity: 0.4` (cleaner than explicit bg/color)
- Textarea padding `8px 14px`

**Not incorporated from felix** (intentional):
- Material Symbols Outlined font (we use Font Awesome)
- 3-column grid layout (ModelDocs uses 2-column)
- Language detection/override UI (not part of ModelDocs)

---

## Demo assets

`uploads/` directory contains:
- `NBT-CR-EL-007_Compliance_Report_v7_0.docx` — sample compliance report output (served at `/demo/report-docx`)
- `NBT-CR-EL-007_Compliance_Report.ipynb` — sample notebook output (served at `/demo/report-ipynb`)
- `doc_spec.yaml` — original spec template (reference)
- A Domino Extensions overview doc (reference)
- A model script the sample report was based on (reference)

---

## Pending / future work

- Wire up the output format selector (Word/Markdown/LaTeX) to actually affect generation
- Consider adding `modelId`/`modelVersionId` to the Domino Job submission payload so the generation script can fetch model-specific artifacts
- The demo context pills ("Source code", "Domino experiments", etc.) are static — could be made dynamic based on what's actually available for the given model
