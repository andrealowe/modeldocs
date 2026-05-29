"""Build the pre-built demo Word report for SBD-OBJ-VIT-2025-001 Seabed Object Classifier (ViT v1.0).

Sections follow the ModelDocs report template, overlaid on NIST AI RMF (GOVERN/MAP/MEASURE/MANAGE):
  1. Executive Summary
  2. Model Identification & Inventory
  3. NIST AI RMF Categorization & Risk Tiering
  4. Conceptual Soundness                       (MAP)
  5. Data Lineage & Quality                     (MAP)
  6. Independent Validation & Testing           (MEASURE)
  7. Ongoing Performance Monitoring             (MANAGE)
  8. Limitations & Compensating Controls        (MAP / MANAGE)
  9. Governance & Approvals                     (GOVERN)
  10. Appendix
"""

from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

# ---------------------------------------------------------------------------
# Brand colors (matching Domino design system used elsewhere in ModelDocs)
# ---------------------------------------------------------------------------
_BRAND_COLOR = RGBColor(0x1F, 0x4E, 0x79)
_ACCENT_COLOR = RGBColor(0x2E, 0x74, 0xB5)
_MUTED_COLOR  = RGBColor(0x59, 0x59, 0x59)

_CALLOUT_FINDINGS_BG     = "E8EBF9"
_CALLOUT_FINDINGS_BORDER = "1F4E79"
_CALLOUT_FINDINGS_TITLE  = RGBColor(0x1F, 0x4E, 0x79)
_CALLOUT_ACTIONS_BG      = "E2F0E8"
_CALLOUT_ACTIONS_BORDER  = "2E7D32"
_CALLOUT_ACTIONS_TITLE   = RGBColor(0x2E, 0x7D, 0x32)

OUTPUT_PATH = Path("/mnt/code/uploads/SBD-OBJ-VIT-2025-001_Compliance_Report_v1_0.docx")

BRAND_NAVY    = "#1F4E79"
BRAND_BLUE    = "#2E74B5"
BRAND_VIOLET  = "#3B3BD3"
BRAND_LIGHT   = "#E8EBF9"

CLASSIFICATION_BANNER = "UNCLASSIFIED // FOR OFFICIAL USE ONLY"


# ---------------------------------------------------------------------------
# Low-level helpers
# ---------------------------------------------------------------------------

def _shade_cell(cell, hex_color: str) -> None:
    tc = cell._tc
    tcPr = tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _add_heading_rule(para) -> None:
    pPr = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "6")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "1F4E79")
    pBdr.append(bottom)
    pPr.append(pBdr)


def _h1(doc: Document, title: str) -> None:
    para = doc.add_heading(title, level=1)
    for run in para.runs:
        run.font.color.rgb = _BRAND_COLOR
    _add_heading_rule(para)
    doc.add_paragraph()


def _h2(doc: Document, title: str) -> None:
    para = doc.add_heading(title, level=2)
    for run in para.runs:
        run.font.color.rgb = _ACCENT_COLOR
    doc.add_paragraph()


def _hint(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.italic = True
    run.font.size = Pt(10)
    run.font.color.rgb = _MUTED_COLOR
    p.paragraph_format.space_after = Pt(8)


def _body(doc: Document, text: str) -> None:
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.font.size = Pt(11)
    p.paragraph_format.space_after = Pt(6)


def _callout(
    doc: Document,
    title: str,
    items: list[str],
    is_numbered: bool = False,
    bg: str = _CALLOUT_FINDINGS_BG,
    border: str = _CALLOUT_FINDINGS_BORDER,
    title_color: RGBColor = _CALLOUT_FINDINGS_TITLE,
) -> None:
    table = doc.add_table(rows=1, cols=1)
    table.style = "Table Grid"
    cell = table.rows[0].cells[0]
    _shade_cell(cell, bg)

    tc, tcPr = cell._tc, cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement("w:tcBorders")
    left = OxmlElement("w:left")
    left.set(qn("w:val"), "thick"); left.set(qn("w:sz"), "24")
    left.set(qn("w:space"), "0"); left.set(qn("w:color"), border)
    tcBorders.append(left)
    for side in ("top", "right", "bottom", "insideH", "insideV"):
        b = OxmlElement(f"w:{side}")
        b.set(qn("w:val"), "none"); b.set(qn("w:sz"), "0"); b.set(qn("w:color"), "auto")
        tcBorders.append(b)
    tcPr.append(tcBorders)

    tcMar = OxmlElement("w:tcMar")
    for side, twips in (("top","72"),("left","144"),("bottom","72"),("right","144")):
        m = OxmlElement(f"w:{side}")
        m.set(qn("w:w"), twips); m.set(qn("w:type"), "dxa")
        tcMar.append(m)
    tcPr.append(tcMar)

    tp = cell.paragraphs[0]
    tr = tp.add_run(title.upper())
    tr.bold = True; tr.font.size = Pt(9); tr.font.color.rgb = title_color
    tp.paragraph_format.space_after = Pt(4)

    for i, item in enumerate(items):
        if not (item or "").strip():
            continue
        ip = cell.add_paragraph()
        if is_numbered:
            pr = ip.add_run(f"{i+1}.  ")
            pr.bold = True; pr.font.color.rgb = title_color; pr.font.size = Pt(10)
        else:
            br = ip.add_run("•  ")
            br.font.color.rgb = title_color; br.font.size = Pt(10)
        ip.add_run(item.strip()).font.size = Pt(10)
        ip.paragraph_format.space_after = Pt(2)
        ip.paragraph_format.left_indent = Pt(6)

    doc.add_paragraph()


def _table(
    doc: Document,
    headers: list[str],
    rows: list[list[str]],
    col_widths: list[float] | None = None,
) -> None:
    tbl = doc.add_table(rows=1 + len(rows), cols=len(headers))
    tbl.style = "Table Grid"
    for j, h in enumerate(headers):
        _shade_cell(tbl.rows[0].cells[j], "1F4E79")
        p = tbl.rows[0].cells[j].paragraphs[0]
        run = p.add_run(h); run.bold = True
        run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); run.font.size = Pt(10)
    for i, row_data in enumerate(rows):
        bg = "F2F5FC" if i % 2 == 0 else "FFFFFF"
        for j, val in enumerate(row_data):
            _shade_cell(tbl.rows[i+1].cells[j], bg)
            p = tbl.rows[i+1].cells[j].paragraphs[0]
            p.add_run(str(val)).font.size = Pt(10)
    if col_widths:
        for j, w in enumerate(col_widths):
            for row in tbl.rows:
                row.cells[j].width = Inches(w)
    doc.add_paragraph()


def _code_ref(doc: Document, filename: str, lines: str, description: str = "") -> None:
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Pt(18)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(f"[{filename}  lines {lines}]")
    run.font.size = Pt(9); run.font.name = "Courier New"
    run.font.color.rgb = _ACCENT_COLOR
    if description:
        d = p.add_run(f"  — {description}")
        d.font.size = Pt(9); d.font.color.rgb = _MUTED_COLOR


def _figure(doc: Document, fig: plt.Figure, caption: str, width: float = 5.5) -> None:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    buf.seek(0)
    plt.close(fig)
    doc.add_picture(buf, width=Inches(width))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cr = cap.add_run(caption)
    cr.italic = True; cr.font.size = Pt(9); cr.font.color.rgb = _MUTED_COLOR
    doc.add_paragraph()


def _classification_banner(doc: Document) -> None:
    """Add UNCLASSIFIED // FOR OFFICIAL USE ONLY banner to header AND footer."""
    section = doc.sections[0]
    for region in (section.header, section.footer):
        p = region.paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run(CLASSIFICATION_BANNER)
        run.bold = True
        run.font.size = Pt(10)
        run.font.color.rgb = RGBColor(0x00, 0x00, 0x00)


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _fig_class_distribution() -> plt.Figure:
    """Figure 1 — Training set class distribution (unbalanced, 498 images)."""
    classes = ["Aircraft", "Vessel", "Seafloor"]
    counts  = [38, 82, 378]
    pcts    = [c / sum(counts) * 100 for c in counts]
    colors  = [BRAND_VIOLET, BRAND_BLUE, BRAND_NAVY]

    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    bars = ax.bar(classes, counts, color=colors, edgecolor="white", linewidth=0.8, width=0.55)
    for bar, c, p in zip(bars, counts, pcts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 8,
                f"{c}\n({p:.1f}%)", ha="center", va="bottom", fontsize=9, color="#333")
    ax.set_ylabel("Image Count", fontsize=10)
    ax.set_xlabel("Target Class", fontsize=10)
    ax.set_title("Training Set Class Distribution (Unbalanced, n=498)\n"
                 "Source: SeabedObjects dataset · s3://seabed-object-detection/",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylim(0, max(counts) * 1.20)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_confusion_matrix() -> plt.Figure:
    """Figure 2 — Confusion matrix on the 361-image test set."""
    import numpy as np
    cm = np.array([
        [17,   5,   2],   # Actual Aircraft (n=24)
        [11, 109,  18],   # Actual Vessel   (n=138)
        [ 3,   5, 191],   # Actual Seafloor (n=199)
    ])
    classes = ["Aircraft", "Vessel", "Seafloor"]
    row_totals = cm.sum(axis=1)
    cm_pct = cm / row_totals[:, None]

    fig, ax = plt.subplots(figsize=(6.0, 4.4))
    from matplotlib.colors import LinearSegmentedColormap
    cmap = LinearSegmentedColormap.from_list("navy", ["#FFFFFF", BRAND_LIGHT, "#A8B7E5", BRAND_BLUE, BRAND_NAVY])
    im = ax.imshow(cm_pct, cmap=cmap, vmin=0, vmax=1, aspect="auto")

    for i in range(len(classes)):
        for j in range(len(classes)):
            count = cm[i, j]
            pct = cm_pct[i, j]
            text_color = "white" if pct > 0.55 else "#1a1a1a"
            ax.text(j, i, f"{count}\n({pct:.0%})", ha="center", va="center",
                    fontsize=10, color=text_color, fontweight="bold" if i == j else "normal")

    ax.set_xticks(range(len(classes))); ax.set_xticklabels(classes, fontsize=10)
    ax.set_yticks(range(len(classes))); ax.set_yticklabels(classes, fontsize=10)
    ax.set_xlabel("Predicted Class", fontsize=10)
    ax.set_ylabel("Actual Class", fontsize=10)
    ax.set_title("Confusion Matrix — Test Set (n=361)\n"
                 "Diagonal = correct · per-row recall in parentheses",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    cbar = fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
    cbar.set_label("Row-normalized rate", fontsize=9)
    cbar.ax.tick_params(labelsize=8)
    fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_per_class_kpis() -> plt.Figure:
    """Figure 3 — Per-class F1 vs. KPI target thresholds."""
    classes = ["Aircraft", "Vessel", "Seafloor"]
    f1   = [0.73, 0.82, 0.96]
    prec = [0.78, 0.85, 0.95]
    rec  = [0.71, 0.79, 0.96]
    targets_f1 = [0.90, 0.80, 0.90]

    import numpy as np
    x = np.arange(len(classes))
    w = 0.26
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    b1 = ax.bar(x - w, prec, width=w, color=BRAND_LIGHT, edgecolor="white", label="Precision")
    b2 = ax.bar(x,     rec,  width=w, color=BRAND_BLUE,  edgecolor="white", label="Recall")
    b3 = ax.bar(x + w, f1,   width=w, color=BRAND_NAVY,  edgecolor="white", label="F1")

    for bars, vals in ((b1, prec), (b2, rec), (b3, f1)):
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.012,
                    f"{v:.2f}", ha="center", va="bottom", fontsize=8.5, color="#333")

    for xi, t in zip(x, targets_f1):
        ax.plot([xi + w - 0.13, xi + w + 0.13], [t, t],
                color="#D04A02", linewidth=2.0, linestyle="--",
                label="F1 target" if xi == 0 else None)

    ax.set_xticks(x); ax.set_xticklabels(classes, fontsize=10)
    ax.set_ylabel("Score", fontsize=10)
    ax.set_ylim(0, 1.10)
    ax.set_title("Per-Class Performance vs. KPI Targets — Test Set (n=361)\n"
                 "F1 targets: Aircraft 0.90 · Vessel 0.80 · Seafloor 0.90",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.legend(fontsize=8.5, loc="upper left", ncol=4, frameon=False)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_confidence_calibration() -> plt.Figure:
    """Figure 4 — Accuracy by confidence band (calibration check)."""
    bands = ["High (>80%)", "Medium (60–80%)", "Low (<60%)"]
    accuracy = [0.973, 0.831, 0.625]
    coverage = [0.72, 0.18, 0.10]
    colors   = ["#2E7D32", "#F0A500", "#D04A02"]

    import numpy as np
    x = np.arange(len(bands))
    fig, ax = plt.subplots(figsize=(7.0, 3.8))
    bars = ax.bar(x, accuracy, color=colors, edgecolor="white", linewidth=0.8, width=0.55)
    for bar, acc, cov in zip(bars, accuracy, coverage):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.015,
                f"{acc:.1%}\n{cov:.0%} of preds", ha="center", va="bottom",
                fontsize=9, color="#333")

    ax.axhline(0.90, color=BRAND_NAVY, linestyle="--", linewidth=1.0, alpha=0.6,
               label="Overall accuracy floor (90%)")
    ax.set_xticks(x); ax.set_xticklabels(bands, fontsize=10)
    ax.set_ylabel("Accuracy", fontsize=10)
    ax.set_ylim(0, 1.10)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("Accuracy by Confidence Band — Test Set (n=361)\n"
                 "Supports confidence-based routing in production deployment",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.legend(fontsize=8.5, frameon=False)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Title page & TOC
# ---------------------------------------------------------------------------

def _title_page(doc: Document) -> None:
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Seabed Object Classifier")
    r.bold = True; r.font.size = Pt(28); r.font.color.rgb = _BRAND_COLOR

    p_sub = doc.add_paragraph()
    p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = p_sub.add_run("Vision Transformer (ViT) v1.0")
    rs.bold = True; rs.font.size = Pt(18); rs.font.color.rgb = _ACCENT_COLOR

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Model Risk & Compliance Documentation  |  SBD-OBJ-VIT-2025-001")
    r2.font.size = Pt(13); r2.font.color.rgb = _ACCENT_COLOR

    rule = doc.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = rule.add_run("─" * 50)
    rr.font.color.rgb = _ACCENT_COLOR; rr.font.size = Pt(10)

    doc.add_paragraph()
    org = doc.add_paragraph()
    org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    or2 = org.add_run("Naval Oceanographic Office (NAVOCEANO)")
    or2.bold = True; or2.font.size = Pt(15); or2.font.color.rgb = _BRAND_COLOR

    dept = doc.add_paragraph()
    dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dept.add_run("Joint Maritime Object Recognition Program (JMORP)  |  Model Governance Office").font.size = Pt(11)

    framework = doc.add_paragraph()
    framework.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = framework.add_run("Aligned to NIST AI Risk Management Framework (AI RMF 1.0)")
    fr.italic = True; fr.font.size = Pt(10); fr.font.color.rgb = _MUTED_COLOR

    for _ in range(2):
        doc.add_paragraph()
    d = doc.add_paragraph()
    d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = d.add_run("Issued: May 2026  |  Version 1.0")
    dr.font.size = Pt(11); dr.font.color.rgb = _MUTED_COLOR

    for _ in range(2):
        doc.add_paragraph()
    notice = doc.add_paragraph()
    notice.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nr = notice.add_run("Generated by ModelDocs  |  UNCLASSIFIED // FOR OFFICIAL USE ONLY")
    nr.italic = True; nr.font.size = Pt(9); nr.font.color.rgb = _MUTED_COLOR
    doc.add_page_break()


def _toc(doc: Document) -> None:
    _h1(doc, "Table of Contents")
    toc_entries = [
        "1.   Executive Summary",
        "2.   Model Identification & Inventory",
        "3.   NIST AI RMF Categorization & Risk Tiering",
        "4.   Conceptual Soundness                  [MAP]",
        "5.   Data Lineage & Quality                [MAP]",
        "6.   Independent Validation & Testing      [MEASURE]",
        "7.   Ongoing Performance Monitoring        [MANAGE]",
        "8.   Limitations & Compensating Controls   [MAP / MANAGE]",
        "9.   Governance & Approvals                [GOVERN]",
        "10.  Appendix",
    ]
    for entry in toc_entries:
        p = doc.add_paragraph()
        p.add_run(entry).font.size = Pt(11)
        p.paragraph_format.space_after = Pt(3)
    doc.add_page_break()


# ---------------------------------------------------------------------------
# Section 1 — Executive Summary
# ---------------------------------------------------------------------------

def _s1_executive_summary(doc: Document) -> None:
    _h1(doc, "1.   Executive Summary")
    _hint(doc, "Purpose, current performance, and compliance posture of the Seabed Object Classifier.")

    _callout(doc, "Key Findings", [
        "SBD-OBJ-VIT-2025-001 (seabed-vit v1.0) is a Vision Transformer (ViT-Base-Patch16-224) fine-tuned to classify side-scan sonar imagery into three operational classes: Aircraft, Vessel, and Seafloor.",
        "Registered test-set performance (n=361, evaluation 18 April 2026): overall accuracy 91.4% · vessel F1 0.82 · aircraft F1 0.73 · seafloor F1 0.96 · macro-AUC 0.91 · log-loss 0.24 · inference latency 1.3s (GPU).",
        "Independent validation by the JMORP Model Validation Cell completed 22 April 2026 (Report MVC-2026-007): approved for limited operational deployment as decision-support for trained sonar analysts; one open finding (V-2026-007-A, Low) targeting Q3 2026.",
        "NIST AI RMF posture: Moderate impact (decision-support, human-in-the-loop); GOVERN/MAP/MEASURE/MANAGE coverage attested; no rights-impacting or safety-impacting use cases per OMB M-24-10 definitions.",
        "All eleven monitored sonar features show stable distributions over the trailing 30-day production window; daily ground-truth ingestion in place via Domino Model Monitor.",
    ])

    _body(doc,
        "The Seabed Object Classifier (SBD-OBJ-VIT-2025-001) provides automated triage of side-scan sonar "
        "imagery for the Joint Maritime Object Recognition Program. For each input image, the model emits a "
        "predicted class — Aircraft, Vessel, or Seafloor — along with a calibrated confidence vector "
        "and eleven derived sonar features used for downstream drift monitoring. Output is consumed by sonar "
        "analyst workstations in the test-mode UI and, via the Domino Model API, by downstream tasking "
        "systems for prioritization of subsequent human review."
    )
    _body(doc,
        "The model is a Vision Transformer (Google ViT-Base-Patch16-224-in21k) fine-tuned on 498 manually "
        "labeled side-scan sonar images covering the three target classes, with balanced sampling and "
        "augmentation employed to compensate for the natural class skew (75.9% seafloor in the source "
        "distribution). It is registered in the program's Domino Model Registry as seabed-vit-v1.0 and "
        "deployed via REST endpoint and an internal Streamlit annotation interface for analyst feedback "
        "capture. The model is explicitly scoped for decision-support and is not authorized for autonomous "
        "tasking, targeting, or any safety- or rights-impacting decision under OMB M-24-10."
    )

    _callout(doc, "Recommended Actions",
        [
            "Remediate open validation finding V-2026-007-A (acquire and label 50+ additional aircraft samples) by Q3 2026 to lift Aircraft F1 above the 0.90 macro-F1 target.",
            "Stand up a quarterly adversarial-robustness review covering sonar artifacts (shadows, multiples, ping-rate variation) before expanding to additional sonar platforms.",
            "Onboard at least one additional independent reviewer to support inter-annotator agreement studies on the minority classes for v2.0.",
        ],
        is_numbered=True, bg=_CALLOUT_ACTIONS_BG, border=_CALLOUT_ACTIONS_BORDER,
        title_color=_CALLOUT_ACTIONS_TITLE,
    )


# ---------------------------------------------------------------------------
# Section 2 — Model Identification & Inventory
# ---------------------------------------------------------------------------

def _s2_model_identification(doc: Document) -> None:
    _h1(doc, "2.   Model Identification & Inventory")
    _hint(doc, "Registered name, version, mission use, and impact classification metadata.")

    _callout(doc, "Key Findings", [
        "Classified Moderate Impact under the program's NIST AI RMF-aligned tiering: decision-support for trained analysts; not safety- or rights-impacting per OMB M-24-10.",
        "Approved uses are restricted to triage and confidence-ranking of side-scan sonar imagery in the test-mode UI and the analyst annotation workflow; outputs are advisory.",
        "The model is not approved for autonomous tasking, navigation decisions, weapons cueing, or any classification of imagery outside the side-scan modality it was trained on.",
        "Current version v1.0 was registered 18 April 2026 from training experiment exp-047; the operational baseline preceding v1.0 was a pure-manual analyst workflow.",
    ])

    _h2(doc, "2.1  Mission Purpose")
    _body(doc,
        "Manual review of side-scan sonar imagery is time-intensive and operator-dependent, with analyst "
        "throughput typically 8–12 images per hour for thorough adjudication. SBD-OBJ-VIT-2025-001 "
        "provides automated triage at approximately 30 images per minute, returning a calibrated class "
        "probability vector that analysts use to prioritize tiles, expand suspected-target regions, and "
        "discard high-confidence seafloor returns. The system is designed and trained as decision-support; "
        "analyst adjudication remains authoritative for all downstream tasking products."
    )
    _body(doc,
        "The model is consumed by: (i) the SonarTriage Streamlit application deployed as a Domino App "
        "(internal SSO, port 8888), (ii) the predict.py REST endpoint exposed via Domino Model API for "
        "programmatic ingestion by downstream catalog systems, and (iii) the Intelligence Report Generator "
        "Launcher used by command staff for batch dataset reporting. The model is not approved for use in "
        "autonomous platform tasking, navigation, weapons cueing, or any modality other than side-scan "
        "sonar imagery acquired at the trained frequency band."
    )

    _h2(doc, "2.2  Model Classification")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Model ID", "SBD-OBJ-VIT-2025-001"],
            ["Registered Name", "seabed-vit-v1.0"],
            ["Model Name", "Seabed Object Classifier — Side-Scan Sonar Imagery"],
            ["Modality", "Side-Scan Sonar (single frequency band)"],
            ["Model Type", "Vision Transformer fine-tuned via transfer learning"],
            ["Base Architecture", "google/vit-base-patch16-224-in21k (86M parameters)"],
            ["NIST AI RMF Impact Tier", "Moderate (decision-support, human-in-the-loop)"],
            ["OMB M-24-10 Designation", "Neither safety-impacting nor rights-impacting"],
            ["Approved Uses", "Sonar tile triage; analyst confidence ranking; batch reporting via Launcher"],
            ["Restricted Uses", "Autonomous tasking; navigation; weapons cueing; non-side-scan modalities"],
            ["Frequency of Use", "Continuous (analyst workstation); batch (Launcher); daily monitoring jobs"],
            ["Current Version", "v1.0 (registered 18 April 2026)"],
            ["Baseline Replaced", "Pure-manual analyst workflow (no prior deployed model)"],
            ["Next Required Review", "April 2027 (annual)"],
            ["Project / Repository", "JMORP / Seabed-Object-Classifier-master"],
            ["Primary Source File", "src/train_model.py (1067 lines)"],
            ["Inference Entry Point", "predict.py (462 lines)"],
        ],
        col_widths=[2.2, 4.6],
    )


# ---------------------------------------------------------------------------
# Section 3 — NIST AI RMF Categorization & Risk Tiering
# ---------------------------------------------------------------------------

def _s3_nist_rmf(doc: Document) -> None:
    _h1(doc, "3.   NIST AI RMF Categorization & Risk Tiering")
    _hint(doc, "Mapping to NIST AI RMF 1.0 functions, impact tiering rationale, and applicable federal AI guidance.")

    _callout(doc, "Key Findings", [
        "Categorized as Moderate Impact under the program's RMF tiering scheme; decision-support for trained personnel with human adjudication of every operational product.",
        "Mapped against all four NIST AI RMF functions: GOVERN (Section 9), MAP (Sections 4, 5, 8), MEASURE (Section 6), MANAGE (Sections 7, 8); no function left without an attested control.",
        "OMB M-24-10 review concluded: neither safety-impacting nor rights-impacting; no DOT, DHS, or DOJ rights-affecting use case is supported.",
        "DoD Responsible AI alignment confirmed: human-in-the-loop preserved, scope explicitly bounded, audit logging of every prediction enabled.",
    ])

    _h2(doc, "3.1  NIST AI RMF Function Mapping")
    _table(doc,
        ["AI RMF Function", "Scope", "Documented In"],
        [
            ["GOVERN", "Policy, roles, accountability, change control, training, third-party model risk.", "Section 9 (Governance & Approvals)"],
            ["MAP", "Context, intended use, stakeholders, data lineage, known limitations, residual risk.", "Sections 4, 5, 8"],
            ["MEASURE", "Quantitative evaluation: accuracy, calibration, robustness, bias, explainability.", "Section 6 (Independent Validation & Testing)"],
            ["MANAGE", "Monitoring, drift detection, incident response, retraining triggers, retirement criteria.", "Sections 7, 8"],
        ],
        col_widths=[1.4, 3.8, 2.0],
    )

    _h2(doc, "3.2  Impact Tiering Rationale")
    _body(doc,
        "The program's NIST AI RMF–aligned tiering scheme classifies AI systems on three dimensions: "
        "mission criticality, reversibility of downstream action, and the presence of human review. "
        "SBD-OBJ-VIT-2025-001 scores Moderate on the first (it supports priority tasking but does not "
        "drive any irreversible action by itself), Low on the second (every model output is a recommendation "
        "that can be discarded), and Low on the third (every prediction surfaces in an analyst workstation "
        "before any downstream use). The composite Moderate tier triggers annual independent revalidation, "
        "continuous performance monitoring with weekly drift reports, and Model Governance Office approval "
        "for any material methodological change."
    )

    _h2(doc, "3.3  Applicable Federal and Departmental Guidance")
    _table(doc,
        ["Framework", "Applicability"],
        [
            ["NIST AI RMF 1.0 (NIST AI 100-1)", "Primary framework. All four functions — GOVERN/MAP/MEASURE/MANAGE — attested in this document."],
            ["OMB M-24-10 (March 2024)", "Reviewed. System is neither safety-impacting nor rights-impacting; no minimum-practice obligations under §5 are triggered, but voluntary alignment is documented."],
            ["DoD Responsible AI Strategy (June 2022)", "Aligned. Human-in-the-loop preserved; scope explicitly bounded; audit logging enabled; quarterly Responsible AI review scheduled."],
            ["NIST AI 100-2 (Adversarial ML Taxonomy)", "Referenced. Quarterly adversarial-robustness review is in the recommended actions of this report."],
            ["Program Policy JMORP-POL-AI-001 v1.2", "Internal policy aligning the above frameworks to JMORP operations."],
        ],
        col_widths=[2.4, 4.4],
    )

    _h2(doc, "3.4  Trustworthy AI Characteristics (NIST AI RMF §2)")
    _table(doc,
        ["Characteristic", "Status", "Evidence"],
        [
            ["Valid & Reliable", "Met", "91.4% test-set accuracy; calibrated probabilities (log-loss 0.24); reproducible builds via Domino Experiments."],
            ["Safe", "Met", "Decision-support only; human adjudication required; no autonomous action."],
            ["Secure & Resilient", "Partial", "Authenticated endpoint, rate-limited (100 req/min/user); adversarial robustness review still scheduled."],
            ["Accountable & Transparent", "Met", "Full version, code, data, and decision lineage in Domino; this document is the public artifact."],
            ["Explainable & Interpretable", "Met", "Attention maps and Grad-CAM available per prediction; 11 sonar features surfaced to analysts."],
            ["Privacy-Enhanced", "N/A", "Training data is geophysical imagery; no PII present (verified via src/pii-detection.py)."],
            ["Fair — Managed Bias", "Met (scope)", "No protected demographic attributes in scope; minority class imbalance is treated as performance bias (see §6, §8)."],
        ],
        col_widths=[2.0, 1.0, 3.8],
    )


# ---------------------------------------------------------------------------
# Section 4 — Conceptual Soundness  (MAP)
# ---------------------------------------------------------------------------

def _s4_conceptual_soundness(doc: Document) -> None:
    _h1(doc, "4.   Conceptual Soundness  [NIST AI RMF: MAP]")
    _hint(doc, "Architecture, theoretical basis, training procedure, and design-choice justification.")

    _callout(doc, "Key Findings", [
        "Architecture is a 12-layer Vision Transformer with 16×16 patch tokenization, [CLS] token classification head, and 86M total parameters; the head is a single dense layer mapping the 768-dim [CLS] representation to three logits.",
        "Selected over ResNet-50 (84.2% accuracy, 0.61 vessel F1) and EfficientNet-B3 (86.7% accuracy, 0.68 vessel F1) based on superior minority-class performance and explainability via attention maps.",
        "Training uses AdamW with cosine learning-rate decay (peak 2e-5, 10% warmup), label smoothing 0.1, gradient clipping at max-norm 1.0, and FP16 mixed precision; balanced batch sampling guarantees equal class representation in each step.",
        "Pre-trained on ImageNet-21k (14M images, 21k classes) and fine-tuned end-to-end on the 498-image SeabedObjects training set; transfer learning is essential given training-set size.",
    ])

    _h2(doc, "4.1  Architecture")
    _body(doc,
        "SBD-OBJ-VIT-2025-001 is a Vision Transformer (ViT-Base) fine-tuned for three-class side-scan sonar "
        "classification. The 224×224×3 input image is partitioned into 196 non-overlapping 16×16 patches; "
        "each patch is linearly projected to a 768-dimensional embedding. Learnable positional encodings and "
        "a [CLS] classification token are concatenated, and the sequence is passed through 12 transformer "
        "encoder layers (12-head multi-head self-attention, 64 dimensions per head, 3072-unit GELU feed-forward "
        "blocks, pre-norm layer normalization, residual connections, dropout 0.1). The [CLS] token output is "
        "passed through a layer-norm and a single dense layer that maps to three logits (Aircraft, Vessel, "
        "Seafloor), which are softmax-normalized to probabilities at inference time."
    )
    _code_ref(doc, "src/train_model.py", "78–144", "BalancedImageDataset — PyTorch dataset with balanced class sampling")
    _code_ref(doc, "src/train_model.py", "235–263", "setup_transforms() — train/eval image transforms incl. augmentation")
    _code_ref(doc, "src/train_model.py", "553–820", "train_model() — fine-tuning loop with mixed precision and cosine LR")

    _h2(doc, "4.2  Training Procedure")
    _table(doc,
        ["Hyperparameter", "Value", "Rationale"],
        [
            ["Optimizer", "AdamW (betas 0.9 / 0.999, weight decay 0.01)", "Decoupled weight decay; standard for transformer fine-tuning."],
            ["Peak Learning Rate", "2e-5", "Selected via Optuna sweep across 1e-6 → 1e-3 (objective(): src/train_model.py L372)."],
            ["LR Schedule", "Cosine decay, 10% linear warmup, min 1e-6", "Smooth convergence; standard for transformer fine-tuning on small datasets."],
            ["Batch Size", "16", "Memory-bound by single-GPU FP16 budget; sufficient for stable gradient estimates."],
            ["Loss", "Cross-entropy with label smoothing 0.1", "Improves calibration; mitigates overconfidence in the minority classes."],
            ["Gradient Clipping", "Max norm 1.0", "Prevents exploding gradients during early warmup."],
            ["Precision", "FP16 mixed precision (Automatic Mixed Precision)", "40% training-time reduction; no measurable accuracy impact."],
            ["Class Balancing", "Balanced sampling (equal classes per batch)", "Selected over focal loss after ablation (§4.4)."],
        ],
        col_widths=[2.0, 2.4, 2.4],
    )

    _h2(doc, "4.3  Training Set Composition")
    _body(doc,
        "Training uses the unbalanced 498-image dataset — 38 aircraft (7.6%), 82 vessels (16.5%), 378 "
        "seafloor (75.9%) — with balanced sampling at the batch level. The natural skew toward seafloor "
        "reflects the deployment distribution; balanced sampling forces the optimizer to attend equally to "
        "the minority classes during training without altering the prior at inference."
    )
    _figure(doc, _fig_class_distribution(),
            "Figure 1 — Training Set Class Distribution (Unbalanced, n=498)\n"
            "Source distribution: aircraft 7.6%, vessel 16.5%, seafloor 75.9%.")

    _h2(doc, "4.4  Architecture Selection — Effective Challenge")
    _body(doc,
        "Three architectures were evaluated in head-to-head experiments tracked in Domino Experiments. The "
        "Vision Transformer achieved superior minority-class performance and was selected:"
    )
    _table(doc,
        ["Architecture", "Overall Acc.", "Vessel F1", "Aircraft F1", "Notes"],
        [
            ["ResNet-50 (CNN baseline)", "84.2%", "0.61", "0.45", "Collapses to majority class; rigid receptive field unsuited to long-range sonar patterns."],
            ["EfficientNet-B3 (CNN)", "86.7%", "0.68", "0.55", "Better than ResNet but still struggles with vessels and aircraft."],
            ["ViT-Base-Patch16-224 (selected)", "91.4%", "0.82", "0.73", "Best across all metrics; attention maps support explainability."],
        ],
        col_widths=[2.6, 1.0, 0.9, 0.9, 1.6],
    )
    _body(doc,
        "Strategy ablations were also conducted: training on the unbalanced 498-image dataset alone produced "
        "an aircraft F1 of 0.32 and a vessel F1 of 0.45 (model degenerates to majority-class predictions). "
        "Focal loss (γ=2.0) yielded marginal improvement over balanced sampling alone (+0.03 vessel F1, "
        "+0.02 aircraft F1) at the cost of additional tuning complexity; balanced sampling was retained "
        "as the primary class-imbalance treatment."
    )


# ---------------------------------------------------------------------------
# Section 5 — Data Lineage & Quality  (MAP)
# ---------------------------------------------------------------------------

def _s5_data_lineage(doc: Document) -> None:
    _h1(doc, "5.   Data Lineage & Quality  [NIST AI RMF: MAP]")
    _hint(doc, "Input/output schemas, data sources, derived sonar features, and data-quality controls.")

    _callout(doc, "Key Findings", [
        "Single primary data source: SeabedObjects on AWS S3 (s3://seabed-object-detection/, us-west-2), accessed through a Domino Data Source connector with role-based access; no external or third-party data is used.",
        "859 manually labeled images across training (498), balanced training (138), and held-out test (361) splits; ground-truth labels validated by domain experts prior to inclusion.",
        "PII review (src/pii-detection.py) confirms no identifying information in the imagery; data is geophysical and not subject to privacy controls.",
        "Eleven derived sonar features (size, brightness, contrast, edge density, dark/bright pixel ratios, SNR) are extracted at every prediction and persisted for drift monitoring.",
    ])

    _h2(doc, "5.1  Required Inputs")
    _table(doc,
        ["Input", "Type", "Source", "Description"],
        [
            ["image", "PNG (8-bit RGB)", "Sonar acquisition system", "Side-scan sonar tile; typical native size 183×190 px; resized to 224×224 for inference."],
            ["acquisition_metadata", "JSON (optional)", "Sonar acquisition system", "Optional timestamp, geocoordinates, sensor ID; logged but not used by the model."],
        ],
        col_widths=[2.0, 1.6, 1.6, 2.8],
    )
    _code_ref(doc, "predict.py", "234–348", "predict() — image ingestion, preprocessing, inference, response shaping")

    _h2(doc, "5.2  Outputs")
    _table(doc,
        ["Output", "Type", "Description"],
        [
            ["predicted_class", "string", "argmax over softmax: one of {aircraft, vessel, seafloor}."],
            ["class_probabilities", "object", "{aircraft, vessel, seafloor} — softmax probabilities summing to 1.0."],
            ["confidence", "float (0–1)", "Maximum of the class-probability vector; used for analyst routing."],
            ["sonar_features", "object (11 fields)", "Brightness mean/std, contrast, edge density, dark/bright pixel ratios, SNR estimate, width, height, size, filename."],
            ["model_version", "string", "Pinned to the model registry version (seabed-vit-v1.0)."],
            ["event_id", "string (UUID)", "Per-prediction event identifier for correlation with ground-truth ingestion."],
        ],
        col_widths=[2.0, 1.4, 3.6],
    )
    _code_ref(doc, "predict.py", "145–232", "extract_sonar_features() — 11-feature extraction for drift monitoring")

    _h2(doc, "5.3  Data Sources")
    _table(doc,
        ["Source Name", "Backing Store", "Purpose", "Access Control"],
        [
            ["seabed-object-detection", "AWS S3 (us-west-2)", "Primary training and test imagery", "Domino Data Source; role-based IAM"],
            ["ground-truth-seabed", "AWS S3 (us-west-2)", "Daily ground-truth labels for production monitoring", "Domino Data Source; role-based IAM"],
            ["Domino Dataset (mounted)", "Domino-managed volume", "Local cache of training tiles for the training job container", "Project-scoped mount"],
        ],
        col_widths=[1.8, 1.6, 2.2, 1.8],
    )

    _h2(doc, "5.4  Data Quality Controls")
    _body(doc,
        "Data-quality enforcement is applied at three stages of the pipeline: ingestion (notebook "
        "01_create_dataset.ipynb), the optional ETL stage (flow.py Domino Flows pipeline), and at "
        "inference time (predict.py):"
    )
    controls = [
        "Schema and modality enforcement — inputs to predict.py are typed-checked (PNG bytes), shape-validated (square or aspect-tolerant resize), and rejected at the API boundary if not a valid image (predict.py L234–270).",
        "PII screen — src/pii-detection.py is run against the source bucket on every monthly refresh and on any new data ingest; no detections to date.",
        "Optional ETL hardening — flow.py provides a 4-stage Domino Flows preprocessing pipeline (normalization, denoising, CLAHE enhancement, packaging) that can be applied to ingest batches for consistency.",
        "Output finiteness — the softmax output is checked for NaN/Inf before being returned; a non-finite probability vector raises rather than silently returning corrupt output.",
        "Drift features — the 11 sonar features extracted at inference time are persisted to the monitoring TrainingSet baseline and to live production predictions for Population-Stability-Index style drift tracking (see §7).",
    ]
    for ctrl in controls:
        p = doc.add_paragraph()
        p.add_run("•  " + ctrl).font.size = Pt(10)
        p.paragraph_format.left_indent = Pt(12)
        p.paragraph_format.space_after = Pt(3)
    doc.add_paragraph()


# ---------------------------------------------------------------------------
# Section 6 — Independent Validation & Testing  (MEASURE)
# ---------------------------------------------------------------------------

def _s6_validation(doc: Document) -> None:
    _h1(doc, "6.   Independent Validation & Testing  [NIST AI RMF: MEASURE]")
    _hint(doc, "Independent revalidation, effective challenge, per-class performance, and outstanding findings.")

    _callout(doc, "Key Findings", [
        "Independent validation completed 22 April 2026 by the JMORP Model Validation Cell (Report MVC-2026-007); outcome: approved for limited operational deployment.",
        "Per-class F1 on the 361-image held-out test set: Aircraft 0.73 · Vessel 0.82 · Seafloor 0.96; macro F1 0.82; weighted F1 0.89.",
        "Confidence calibration: high-confidence predictions (>80%, 72% of volume) achieve 97.3% accuracy; low-confidence predictions (<60%, 10% of volume) achieve 62.5% accuracy and are routed to mandatory human review.",
        "One open finding: V-2026-007-A (Low) — Aircraft class F1 below the 0.90 macro target due to limited training samples (38); remediation by data collection sprint targeted Q3 2026.",
    ])

    _h2(doc, "6.1  Validation Summary")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Model", "seabed-vit-v1.0"],
            ["Validator", "JMORP Model Validation Cell (MVC)"],
            ["Validation Report", "MVC-2026-007"],
            ["Validation Date", "22 April 2026"],
            ["Validation Type", "Initial validation (NIST AI RMF MEASURE)"],
            ["Outcome", "Approved for limited operational deployment as decision-support"],
        ],
        col_widths=[2.2, 4.6],
    )

    _h2(doc, "6.2  Per-Class Performance — Test Set (n=361)")
    _table(doc,
        ["Class", "Support", "Precision", "Recall", "F1", "Target F1", "Status"],
        [
            ["Aircraft", "24",  "0.78", "0.71", "0.73", "0.90", "Below target (open finding)"],
            ["Vessel",   "138", "0.85", "0.79", "0.82", "0.80", "Met"],
            ["Seafloor", "199", "0.95", "0.96", "0.96", "0.90", "Met"],
            ["Macro avg", "361", "0.86", "0.82", "0.82", "0.90", "Near target"],
        ],
        col_widths=[1.2, 0.7, 0.9, 0.7, 0.6, 0.8, 1.9],
    )
    _figure(doc, _fig_confusion_matrix(),
            "Figure 2 — Confusion Matrix on the Held-Out Test Set (n=361)\n"
            "Diagonal cells show correct classifications; row totals = actual class support.")

    _figure(doc, _fig_per_class_kpis(),
            "Figure 3 — Per-Class Performance vs. KPI Targets\n"
            "Primary operational target (Vessel F1 ≥ 0.80) is met; Aircraft F1 below target (see V-2026-007-A).")

    _h2(doc, "6.3  Calibration & Confidence Routing")
    _body(doc,
        "The model was evaluated for probability calibration as part of validation. Test-set log-loss is "
        "0.24 (target < 0.30), and accuracy varies cleanly with predicted confidence: high-confidence "
        "predictions (>80%, accounting for 72% of test-set volume) are correct 97.3% of the time, while "
        "low-confidence predictions (<60%, 10% of volume) are correct only 62.5% of the time. This monotonic "
        "relationship supports the production confidence-routing policy: predictions above 80% are "
        "auto-staged for analyst review, 60–80% are flagged for prompt review, and below 60% are subject "
        "to mandatory adjudication before any downstream use."
    )
    _figure(doc, _fig_confidence_calibration(),
            "Figure 4 — Accuracy by Confidence Band (Test Set, n=361)\n"
            "Supports confidence-based routing: 80% auto-stage · 60–80% prompt review · <60% mandatory adjudication.")

    _h2(doc, "6.4  Robustness & Perturbation Testing")
    _body(doc,
        "Validation included synthetic perturbation testing against three common sonar artifacts: additive "
        "Gaussian noise (σ = 0.10 of dynamic range), in-plane rotation (±15°), and brightness shift (±30%). "
        "Accuracy degraded gracefully: −2.9% (rotation), −2.5% (brightness), −13.4% (Gaussian noise at 20%). "
        "Noise sensitivity at high levels motivates the recommendation in §1 for a scheduled adversarial "
        "robustness review against sonar-specific artifacts (shadows, multiples, ping-rate variation)."
    )

    _h2(doc, "6.5  Outstanding Validation Findings")
    _table(doc,
        ["Finding", "Severity", "Description", "Status"],
        [
            ["V-2026-007-A", "Low",
             "Aircraft F1 of 0.73 below the 0.90 macro-F1 target due to limited training samples (38 aircraft images). Recommendation: data collection sprint for 50+ additional aircraft tiles.",
             "OPEN — target Q3 2026"],
            ["V-2026-007-B", "Low",
             "Adversarial-robustness assessment scoped to noise/rotation/brightness only; full sonar-artifact adversarial review (shadows, multiples) not yet performed.",
             "OPEN — target Q4 2026"],
        ],
        col_widths=[1.2, 0.9, 3.4, 1.3],
    )


# ---------------------------------------------------------------------------
# Section 7 — Ongoing Performance Monitoring  (MANAGE)
# ---------------------------------------------------------------------------

def _s7_monitoring(doc: Document) -> None:
    _h1(doc, "7.   Ongoing Performance Monitoring  [NIST AI RMF: MANAGE]")
    _hint(doc, "Production monitoring activities, drift thresholds, and recalibration triggers.")

    _callout(doc, "Key Findings", [
        "Daily ground-truth ingestion is operational via Domino Model Monitor (ground-truth bucket s3://domino-monitoring/ground_truth/).",
        "All 11 sonar features are tracked for distribution drift on a weekly cadence; review threshold PSI > 0.10, escalate threshold PSI > 0.25.",
        "Production accuracy (rolling 30 days against returned ground truth): 90.7% — within the −1.0% drift tolerance of the registered baseline (91.4%).",
        "Confidence-routing policy is enforced at the API boundary: predictions with confidence < 60% are returned with a 'mandatory_review = true' flag for downstream consumers.",
    ])

    _h2(doc, "7.1  Registered Reference Performance")
    _body(doc,
        "The values below are recorded against the registered artifact for v1.0 and are the reference "
        "performance figures any future deployment must reproduce on the held-out test set."
    )
    _table(doc,
        ["Metric", "Value", "Recorded"],
        [
            ["overall_accuracy",    "0.914", "18 April 2026"],
            ["macro_f1",            "0.82",  "18 April 2026"],
            ["weighted_f1",         "0.89",  "18 April 2026"],
            ["vessel_f1",           "0.82",  "18 April 2026"],
            ["aircraft_f1",         "0.73",  "18 April 2026"],
            ["seafloor_f1",         "0.96",  "18 April 2026"],
            ["macro_auc_roc",       "0.91",  "18 April 2026"],
            ["log_loss",            "0.24",  "18 April 2026"],
            ["inference_latency_gpu_s", "1.3", "18 April 2026"],
            ["test_set_size",       "361",   "18 April 2026"],
        ],
        col_widths=[2.6, 1.4, 2.8],
    )

    _h2(doc, "7.2  Production Monitoring Activities")
    _table(doc,
        ["Monitoring Activity", "Frequency", "Threshold", "Status (Mar 2026)"],
        [
            ["Ground-truth ingestion",                "Daily",   "100% of prediction events matched within 7 days", "PASS (99.6%)"],
            ["Accuracy back-test (rolling 30 days)",  "Weekly",  "Within −1.0% of registered 91.4%",              "PASS (90.7%)"],
            ["PSI on 11 sonar features",              "Weekly",  "PSI < 0.10 review; < 0.25 escalate",              "ALL STABLE"],
            ["Aircraft F1 (open finding tracker)",    "Monthly", "Trend toward 0.90 over remediation window",       "MONITOR (0.74)"],
            ["Endpoint latency (p95)",                "Daily",   "< 2s per prediction (GPU)",                       "PASS (1.4s)"],
            ["Endpoint availability",                 "Daily",   "≥ 99.5% over 30 days",                        "PASS (99.8%)"],
        ],
        col_widths=[2.4, 1.0, 2.0, 1.4],
    )

    _h2(doc, "7.3  Triggers for Recalibration or Redevelopment")
    _body(doc,
        "Recalibration is triggered if: (i) rolling 30-day accuracy drops below 88.0% (more than 3.4 "
        "percentage points below the registered baseline), (ii) PSI on any of the 11 sonar features "
        "exceeds 0.25, (iii) Aircraft F1 fails to trend upward over two consecutive monthly reviews "
        "after the planned data-collection sprint, or (iv) inter-annotator agreement on a sampled batch "
        "of analyst adjudications falls below 0.85. Full redevelopment is triggered if: (i) the sonar "
        "acquisition platform changes, (ii) a new target class is added to operational requirements, "
        "or (iii) validation issues a High-severity finding requiring methodological change."
    )


# ---------------------------------------------------------------------------
# Section 8 — Limitations & Compensating Controls  (MAP / MANAGE)
# ---------------------------------------------------------------------------

def _s8_limitations(doc: Document) -> None:
    _h1(doc, "8.   Limitations & Compensating Controls  [NIST AI RMF: MAP / MANAGE]")
    _hint(doc, "Known constraints, simplifying assumptions, severity, and mitigants.")

    _callout(doc, "Key Findings", [
        "Aircraft class has only 38 training samples — the single largest constraint on overall macro-F1; mitigated by balanced sampling, augmentation, and a confidence-routing policy that flags low-confidence aircraft predictions for mandatory review.",
        "Trained on a single sonar modality (side-scan) at a single frequency band; generalization to multibeam, synthetic-aperture, or off-band side-scan is not validated.",
        "Geographic coverage of the training set is limited; deployment to a meaningfully different operating environment requires a drift assessment before use.",
        "No certified safety-of-flight or safety-of-navigation use case; output is decision-support only and is not authorized for autonomous action.",
    ])

    _table(doc,
        ["#", "Limitation / Assumption", "Severity", "Compensating Control"],
        [
            ["L1", "Aircraft class undertrained (38 samples) — F1 of 0.73 below 0.90 target.", "Medium",
             "Confidence-routing policy flags low-confidence aircraft predictions for mandatory analyst review; data-collection sprint targeted Q3 2026 (V-2026-007-A)."],
            ["L2", "Trained on side-scan sonar only; not validated on multibeam, synthetic aperture, or off-band side-scan.", "Medium",
             "Approved-use scope (§2.1) is explicit; out-of-modality requests are rejected at the analyst-workstation UI layer."],
            ["L3", "Geographic and platform coverage of the training set is limited.", "Low",
             "Deployment to a new operating environment requires a documented drift assessment using the 11-feature PSI battery."],
            ["L4", "Fixed 224×224 input resolution; original sonar tiles vary in size (typical 183×190).", "Low",
             "Aspect-tolerant resize implemented at the API boundary; resampling artifacts characterized in §6.4 robustness testing."],
            ["L5", "Adversarial robustness assessed only against generic perturbations (noise, rotation, brightness); sonar-artifact adversarial cases not exhaustively tested.", "Medium",
             "Open finding V-2026-007-B tracks remediation; quarterly review scheduled."],
            ["L6", "No inter-annotator agreement study for ground-truth labels; assumes 100% label correctness.", "Low",
             "v2.0 plan adds a dual-annotator workflow on the next training data sprint; analyst feedback in the test-mode UI surfaces likely-mislabeled tiles."],
            ["L7", "Model is not approved for, and provides no certification for, safety-of-navigation or weapons-cueing use.", "Hard scope boundary",
             "Scope explicitly bounded in §2.1 and JMORP-POL-AI-001 §3.4; API audit logging records every prediction's consumer for posthoc review."],
        ],
        col_widths=[0.4, 2.6, 0.9, 2.9],
    )

    _callout(doc, "Recommended Actions",
        [
            "Execute the Q3 2026 aircraft data-collection sprint to lift Aircraft F1 above the 0.90 macro target (closes V-2026-007-A).",
            "Stand up a quarterly sonar-artifact adversarial review (shadows, multiples, ping-rate variation) to close V-2026-007-B.",
            "Initiate a dual-annotator inter-rater agreement study against a 200-tile balanced sample before opening the v2.0 training cycle.",
        ],
        is_numbered=True, bg=_CALLOUT_ACTIONS_BG, border=_CALLOUT_ACTIONS_BORDER,
        title_color=_CALLOUT_ACTIONS_TITLE,
    )


# ---------------------------------------------------------------------------
# Section 9 — Governance & Approvals  (GOVERN)
# ---------------------------------------------------------------------------

def _s9_governance(doc: Document) -> None:
    _h1(doc, "9.   Governance & Approvals  [NIST AI RMF: GOVERN]")
    _hint(doc, "Ownership, accountability, change control, and NIST AI RMF GOVERN posture.")

    _callout(doc, "Key Findings", [
        "SBD-OBJ-VIT-2025-001 v1.0 approved for limited operational deployment by the JMORP AI Governance Board on 28 April 2026 following independent validation MVC-2026-007.",
        "Model inventory ID: JMORP-MID-2026-014. Impact tier: Moderate. Next required revalidation: April 2027.",
        "All material changes (model architecture, training data composition, scope of approved uses) require AI Governance Board approval, re-validation, and a version bump.",
        "NIST AI RMF GOVERN posture: Compliant — documented owner, validator independence, change-control process, training records, and incident-response runbook all in place.",
    ])

    _h2(doc, "9.1  Roles and Responsibilities")
    _table(doc,
        ["Role", "Holder", "Responsibilities"],
        [
            ["Model Owner",              "Director, JMORP Analytics",                       "Model performance, documentation, and finding remediation."],
            ["Model Developer",          "Senior Data Scientist, JMORP Analytics",          "Architecture, training, recalibration, and developer documentation."],
            ["Operational Sponsor",      "Chief of Maritime Domain Awareness, NAVOCEANO",   "Appropriateness of model application; analyst workflow integration."],
            ["Independent Validator",    "JMORP Model Validation Cell (reports to Program Manager)", "Initial and ongoing validation per NIST AI RMF MEASURE."],
            ["AI Governance Board",      "Chaired by JMORP Program Manager",                "Approves new models, material changes, impact-tier assignments."],
            ["Responsible AI Officer",   "JMORP RAIO, per DoD Responsible AI Strategy",     "Cross-cutting trustworthy-AI attestations; human-in-the-loop verification."],
        ],
        col_widths=[1.8, 2.4, 2.6],
    )

    _h2(doc, "9.2  Change Control")
    _body(doc,
        "Material changes (any modification to model architecture, base checkpoint, training data composition, "
        "approved-use scope, or output schema) require AI Governance Board approval, independent re-validation, "
        "and a version bump. Non-material changes (logging refinements, environment patches, hyperparameter "
        "tuning that does not move test-set metrics by more than 1.0 percentage point) require Model Owner "
        "approval and notation in the Model Inventory System (JMORP-MIS)."
    )

    _h2(doc, "9.3  Version History")
    _table(doc,
        ["Version", "Date", "Author", "Change Summary"],
        [
            ["v1.0", "2026-04-18", "JMORP Analytics", "Initial registered version: ViT-Base fine-tune with balanced sampling and mixed precision. Initial NIST AI RMF attestation."],
            ["v0.9", "2026-03-15", "JMORP Analytics", "Pre-validation candidate (used in MVC dry-run only; not deployed)."],
            ["v0.5", "2026-02-01", "JMORP Analytics", "First end-to-end training run; baseline architecture-comparison experiments."],
        ],
        col_widths=[0.8, 1.0, 1.8, 3.2],
    )

    _h2(doc, "9.4  Validation & Approval Status")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Most recent validation", "Initial validation, 22 April 2026 (MVC-2026-007)"],
            ["Outcome", "Approved for limited operational deployment as decision-support"],
            ["Open findings", "2 (Low severity, V-2026-007-A and V-2026-007-B) — targets Q3/Q4 2026"],
            ["Governance Board approval", "28 April 2026"],
            ["Next revalidation due", "April 2027 (annual cadence)"],
        ],
        col_widths=[2.2, 4.6],
    )

    _h2(doc, "9.5  Training & Awareness")
    _body(doc,
        "All analysts cleared to use the SonarTriage workstation complete a one-hour onboarding module that "
        "covers: (i) the model's approved-use scope, (ii) interpretation of confidence scores and the "
        "confidence-routing policy, (iii) the analyst-feedback workflow for surfacing likely-mislabeled tiles, "
        "and (iv) the prohibition on use of model output for autonomous tasking or safety-of-navigation. "
        "Completion is tracked in the program LMS and is a prerequisite for endpoint access."
    )


# ---------------------------------------------------------------------------
# Section 10 — Appendix
# ---------------------------------------------------------------------------

def _s10_appendix(doc: Document) -> None:
    _h1(doc, "10.  Appendix")
    _hint(doc, "Registered artifact references, source code index, glossary, and bibliography.")

    _callout(doc, "Key Findings", [
        "Model logic is implemented across two primary source files — src/train_model.py (training, 1067 lines) and predict.py (inference, 462 lines) — supported by sampling, monitoring, and ETL modules.",
        "ViT base checkpoint is google/vit-base-patch16-224-in21k (Hugging Face); only the classification head and embedding adapter are randomly initialized prior to fine-tuning.",
        "All citations in this document resolve to line ranges in the registered v1.0 artifact tree under the JMORP/Seabed-Object-Classifier-master project.",
    ])

    _h2(doc, "A.  Registered Artifact References")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Registered Name", "seabed-vit-v1.0"],
            ["Registered Version", "1.0"],
            ["Registered By", "JMORP Analytics"],
            ["Registered Date", "18 April 2026"],
            ["Source Project", "JMORP / Seabed-Object-Classifier-master"],
            ["Base Checkpoint", "google/vit-base-patch16-224-in21k (Hugging Face Transformers)"],
            ["Training Entry Point", "src/train_model.py — train_model() (line 553)"],
            ["Inference Entry Point", "predict.py — predict() (line 234)"],
            ["Monitoring Baseline", "Domino TrainingSet: seabed-sonar-training-baseline"],
            ["Streamlit App", "src/streamlit-app.py (port 8888 in production, 8501 in workspace)"],
            ["Launcher", "src/launchers/simple_report_launcher.py"],
            ["ETL Pipeline", "flow.py — seabed_etl_pipeline_balanced / _unbalanced (Domino Flows)"],
        ],
        col_widths=[2.2, 4.6],
    )

    _h2(doc, "B.  Source Code Index")
    _table(doc,
        ["File", "Lines", "Symbol / Description"],
        [
            ["src/train_model.py",    "78–144",  "BalancedImageDataset — PyTorch Dataset with class-balanced sampling"],
            ["src/train_model.py",    "146–233", "compute_metrics() — per-class and macro F1, precision, recall, AUC"],
            ["src/train_model.py",    "235–263", "setup_transforms() — train/eval augmentation and normalization"],
            ["src/train_model.py",    "266–354", "register_best_model() — MLflow model registry registration"],
            ["src/train_model.py",    "356–370", "suggest_hyperparameters() — Optuna search-space definition"],
            ["src/train_model.py",    "372–497", "objective() — Optuna training/eval objective with mixed precision"],
            ["src/train_model.py",    "499–551", "optimize_hyperparameters() — Optuna study driver"],
            ["src/train_model.py",    "553–820", "train_model() — production fine-tuning loop"],
            ["src/train_model.py",    "823–905", "run_optimization() — wrapper around Optuna with logging"],
            ["src/train_model.py",    "907–1037", "train_model_with_params() — training entry with explicit params"],
            ["src/train_model.py",    "1039–1067", "main() — CLI dispatch"],
            ["predict.py",            "8–98",     "ensure_numpy_compatibility() — runtime compatibility shim"],
            ["predict.py",            "100–143",  "get_model_path() — model artifact resolution from registry"],
            ["predict.py",            "145–232",  "extract_sonar_features() — 11-feature sonar feature extraction"],
            ["predict.py",            "234–348",  "predict() — image → class/confidence/features response"],
            ["predict.py",            "349–462",  "main() — CLI inference entry"],
            ["src/demo_train_vit_model.py", "20–127", "simulate_vit_training() — deterministic training simulation for demo runs"],
            ["src/demo_register_champion_model.py", "56–196", "select_champion_model() — ViT vs CNN vs ensemble champion selection"],
            ["src/pii-detection.py",  "1–153",    "PII screen for training-data buckets (no detections to date)"],
            ["src/monitoring/setup_monitoring.py", "—", "Interactive monitoring configuration (Domino Model Monitor)"],
            ["flow.py",               "1–733",    "Domino Flows ETL pipeline (4 stages: normalize, denoise, enhance, package)"],
        ],
        col_widths=[2.3, 0.9, 3.6],
    )

    _h2(doc, "C.  Glossary")
    _table(doc,
        ["Term", "Definition"],
        [
            ["AI RMF", "NIST AI Risk Management Framework (NIST AI 100-1)."],
            ["AUC-ROC", "Area under the receiver-operating-characteristic curve; per-class discrimination metric."],
            ["CLAHE", "Contrast-Limited Adaptive Histogram Equalization; image-enhancement technique used in the ETL pipeline."],
            ["Domino Model Monitor", "Domino product surface for drift and performance monitoring of deployed models."],
            ["Effective Challenge", "Independent reproduction or counter-modeling of a production model's mechanism; an AI RMF MEASURE outcome."],
            ["F1", "Harmonic mean of precision and recall; primary class-balanced performance metric."],
            ["GOVERN / MAP / MEASURE / MANAGE", "The four NIST AI RMF 1.0 functions (NIST AI 100-1 §5)."],
            ["JMORP", "Joint Maritime Object Recognition Program."],
            ["MVC", "Model Validation Cell — the program's independent validation function."],
            ["NAVOCEANO", "Naval Oceanographic Office."],
            ["OMB M-24-10", "Office of Management and Budget Memorandum M-24-10 (March 2024), “Advancing Governance, Innovation, and Risk Management for Agency Use of AI.”"],
            ["PSI", "Population Stability Index; distribution-drift measure comparing live to baseline."],
            ["Responsible AI", "DoD term for the cross-cutting attestations of fairness, accountability, traceability, reliability, and governability."],
            ["SNR", "Signal-to-noise ratio; one of the 11 sonar features extracted at inference."],
            ["ViT", "Vision Transformer (Dosovitskiy et al., 2021)."],
        ],
        col_widths=[2.0, 4.8],
    )

    _h2(doc, "D.  Bibliography")
    refs = [
        "National Institute of Standards and Technology (2023). Artificial Intelligence Risk Management Framework (AI RMF 1.0). NIST AI 100-1.",
        "National Institute of Standards and Technology (2024). Adversarial Machine Learning: A Taxonomy and Terminology of Attacks and Mitigations. NIST AI 100-2 E2023.",
        "Office of Management and Budget (March 2024). Advancing Governance, Innovation, and Risk Management for Agency Use of Artificial Intelligence. M-24-10.",
        "U.S. Department of Defense (June 2022). Responsible AI Strategy and Implementation Pathway.",
        "Dosovitskiy, A. et al. (2021). An Image is Worth 16x16 Words: Transformers for Image Recognition at Scale. ICLR 2021.",
        "Deng, J. et al. (2009). ImageNet: A Large-Scale Hierarchical Image Database. CVPR 2009.",
    ]
    for i, ref in enumerate(refs, 1):
        p = doc.add_paragraph()
        p.add_run(f"[{i}]  {ref}").font.size = Pt(9.5)
        p.paragraph_format.left_indent  = Pt(18)
        p.paragraph_format.first_line_indent = Pt(-18)
        p.paragraph_format.space_after = Pt(4)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def build() -> None:
    doc = Document()
    section = doc.sections[0]
    section.left_margin   = Inches(1.0)
    section.right_margin  = Inches(1.0)
    section.top_margin    = Inches(1.0)
    section.bottom_margin = Inches(1.0)

    _classification_banner(doc)
    _title_page(doc)
    _toc(doc)

    _s1_executive_summary(doc);    doc.add_page_break()
    _s2_model_identification(doc); doc.add_page_break()
    _s3_nist_rmf(doc);             doc.add_page_break()
    _s4_conceptual_soundness(doc); doc.add_page_break()
    _s5_data_lineage(doc);         doc.add_page_break()
    _s6_validation(doc);           doc.add_page_break()
    _s7_monitoring(doc);           doc.add_page_break()
    _s8_limitations(doc);          doc.add_page_break()
    _s9_governance(doc);           doc.add_page_break()
    _s10_appendix(doc)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUTPUT_PATH))
    print(f"Saved: {OUTPUT_PATH}")


if __name__ == "__main__":
    build()
