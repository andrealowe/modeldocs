"""Build the pre-built demo Word report for NBT-CR-EL-007 Expected Loss Model.

Sections follow the ModelDocs report template exactly:
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
# Brand colors (matching builder.py)
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

OUTPUT_PATH = Path("/mnt/code/uploads/NBT-CR-EL-007_Compliance_Report_v7_0.docx")

BRAND_NAVY    = "#1F4E79"
BRAND_BLUE    = "#2E74B5"
BRAND_VIOLET  = "#3B3BD3"
BRAND_LIGHT   = "#E8EBF9"


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
            br = ip.add_run("\u2022  ")
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


# ---------------------------------------------------------------------------
# Charts
# ---------------------------------------------------------------------------

def _fig_lgd_ltv() -> plt.Figure:
    """LGD as a function of LTV — from expected_loss_model.py:L69."""
    import numpy as np
    def lgd(ltv): return max(0.05, min(0.80, ltv - 0.60))
    xs = [x / 100 for x in range(0, 151)]
    ys = [lgd(x) for x in xs]
    fig, ax = plt.subplots(figsize=(6, 3.5))
    ax.plot(xs, ys, color=BRAND_NAVY, linewidth=2)
    ax.fill_between(xs, ys, alpha=0.08, color=BRAND_BLUE)
    ax.annotate("Floor: 5%\n(LTV ≤ 0.65)", xy=(0.65, 0.05), xytext=(0.15, 0.35),
                fontsize=8.5, color="#333",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.7))
    ax.annotate("Cap: 80%\n(LTV ≥ 1.40)", xy=(1.40, 0.80), xytext=(0.90, 0.40),
                fontsize=8.5, color="#333",
                arrowprops=dict(arrowstyle="->", color="#888", lw=0.7))
    ax.set_xlabel("Loan-to-Value Ratio (LTV)", fontsize=10)
    ax.set_ylabel("Implied LGD", fontsize=10)
    ax.set_title("LGD as a Function of LTV\n(expected_loss_model.py · _derive_lgd · line 69)",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.set_xlim(0, 1.5); ax.set_ylim(0, 0.95)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_ltv_risk_weights() -> plt.Figure:
    bands  = ["≤ 50%", "51–60%", "61–80%", "81–90%", "91–100%", "> 100%"]
    weights = [0.20, 0.25, 0.35, 0.50, 0.75, 1.05]
    colors  = [BRAND_LIGHT, "#C9C5F2", BRAND_BLUE, "#F0A500", "#D04A02", "#8B0000"]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    bars = ax.bar(bands, [w*100 for w in weights], color=colors,
                  edgecolor="white", linewidth=0.8, width=0.6)
    for bar, w in zip(bars, weights):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1.5,
                f"{w:.0%}", ha="center", va="bottom", fontsize=9, color="#333")
    ax.axhline(35, color=BRAND_NAVY, linestyle="--", linewidth=0.9, alpha=0.5, label="Standard 35% tier")
    ax.set_ylabel("Risk Weight (%)", fontsize=10)
    ax.set_xlabel("LTV Band", fontsize=10)
    ax.set_title("Basel III LTV Risk-Weight Schedule\n(expected_loss_model.py · LTV_RISK_WEIGHTS · lines 30–37)",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylim(0, 125); ax.legend(fontsize=8.5)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_portfolio_metrics() -> plt.Figure:
    labels = ["Total EL\n(Undiscounted)", "Total EL\n(Discounted)", "Total RWA"]
    vals   = [41572.94, 39494.30, 406068.25]
    fig, ax = plt.subplots(figsize=(6.5, 3.8))
    bars = ax.bar(labels, vals, color=[BRAND_NAVY, BRAND_BLUE, BRAND_VIOLET],
                  edgecolor="white", linewidth=0.8, width=0.55)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 4000,
                f"${v:,.0f}", ha="center", va="bottom", fontsize=9, color="#333")
    ax.set_ylabel("Amount (USD)", fontsize=10)
    ax.set_title("Registered Reference-Run Metrics — Q4 2024\n(MLflow experiment: NBT-CR-EL-007 · example_loan_count = 4)",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylim(0, max(vals)*1.2)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


def _fig_psi_monitoring() -> plt.Figure:
    import numpy as np
    features = ["credit_score", "dti_ratio", "ltv_ratio", "loan_age",
                "orig_balance", "interest_rate", "employment_yrs",
                "delinquencies", "loan_purpose", "tenor"]
    psi_vals = [0.04, 0.06, 0.08, 0.07, 0.05, 0.02, 0.08, 0.06, 0.04, 0.03]
    colors = ["#2E7D32" if v < 0.10 else "#F0A500" if v < 0.25 else "#D04A02" for v in psi_vals]
    fig, ax = plt.subplots(figsize=(7.5, 3.8))
    ax.bar(features, psi_vals, color=colors, edgecolor="white", linewidth=0.8, width=0.65)
    ax.axhline(0.10, color="#F0A500", linestyle="--", linewidth=1.2, label="Review (PSI > 0.10)")
    ax.axhline(0.25, color="#D04A02", linestyle="--", linewidth=1.2, label="Escalate (PSI > 0.25)")
    ax.set_ylabel("PSI", fontsize=10)
    ax.set_title("Ongoing Monitoring — Population Stability Index\n(10 Input Features — March 2026)",
                 fontsize=10, color=BRAND_NAVY, fontweight="bold")
    ax.set_ylim(0, 0.30)
    ax.tick_params(axis="x", labelsize=8.5, rotation=20)
    ax.legend(fontsize=8.5)
    ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
    ax.spines["left"].set_color("#CCC"); ax.spines["bottom"].set_color("#CCC")
    ax.set_facecolor("#FAFBFF"); fig.patch.set_facecolor("white")
    fig.tight_layout()
    return fig


# ---------------------------------------------------------------------------
# Title page & TOC
# ---------------------------------------------------------------------------

def _title_page(doc: Document) -> None:
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run("Expected Loss Model")
    r.bold = True; r.font.size = Pt(28); r.font.color.rgb = _BRAND_COLOR

    p2 = doc.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = p2.add_run("Model Risk Documentation  |  NBT-CR-EL-007")
    r2.font.size = Pt(14); r2.font.color.rgb = _ACCENT_COLOR

    rule = doc.add_paragraph()
    rule.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = rule.add_run("─" * 44)
    rr.font.color.rgb = _ACCENT_COLOR; rr.font.size = Pt(10)

    doc.add_paragraph()
    org = doc.add_paragraph()
    org.alignment = WD_ALIGN_PARAGRAPH.CENTER
    or2 = org.add_run("Northbridge Trust")
    or2.bold = True; or2.font.size = Pt(16); or2.font.color.rgb = _BRAND_COLOR

    dept = doc.add_paragraph()
    dept.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dept.add_run("Fixed Income Analytics  |  Model Governance").font.size = Pt(11)

    for _ in range(2):
        doc.add_paragraph()
    d = doc.add_paragraph()
    d.alignment = WD_ALIGN_PARAGRAPH.CENTER
    dr = d.add_run("May 2026  |  Version 7.0")
    dr.font.size = Pt(11); dr.font.color.rgb = _MUTED_COLOR

    for _ in range(2):
        doc.add_paragraph()
    notice = doc.add_paragraph()
    notice.alignment = WD_ALIGN_PARAGRAPH.CENTER
    nr = notice.add_run("Generated by ModelDocs  |  Confidential — Internal Use Only")
    nr.italic = True; nr.font.size = Pt(9); nr.font.color.rgb = _MUTED_COLOR
    doc.add_page_break()


def _toc(doc: Document) -> None:
    _h1(doc, "Table of Contents")
    toc_entries = [
        "1.   Executive Summary",
        "2.   Model Identification & Inventory",
        "3.   Regulatory Classification",
        "4.   Conceptual Soundness",
        "5.   Data Lineage & Quality",
        "6.   Independent Validation",
        "7.   Ongoing Performance Monitoring",
        "8.   Limitations & Compensating Controls",
        "9.   Governance & Approvals",
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
    _hint(doc, "High-level summary of the model's purpose, current performance, and compliance status.")

    _callout(doc, "Key Findings", [
        "NBT-CR-EL-007 (GetExpectedLoss v7) is a Tier 1 (High Materiality) closed-form actuarial model producing undiscounted EL, risky-discounted EL, and Basel III standardized-approach RWA for the residential mortgage portfolio.",
        "Registered reference-run metrics (21 April 2026): total_el_undiscounted = $41,572.94 · total_el_discounted = $39,494.30 · total_rwa = $406,068.25 · example_loan_count = 4 · curve_length = 7.",
        "Independent revalidation completed 18 March 2026 (Report MVG-2026-018): approved for continued production use, all Tier 1 thresholds met, one low-severity open finding (V-2026-018-A) targeting Q3 2026.",
        "All 10 input features show PSI < 0.10 (stable) as of March 2026; monthly EL back-test variance is −7.2%, within the ±15% threshold.",
        "The model satisfies SR 26-2 / SR 11-7, Basel III standardized approach (CRE20.85), and IFRS 9 / ASC 326 (CECL) conceptual-soundness criteria.",
    ])

    _body(doc,
        "The Expected Loss Model (NBT-CR-EL-007) produces three loan-level outputs for Northbridge Trust's "
        "residential mortgage portfolio: an implied credit rating, an implied LGD, and discounted and "
        "undiscounted expected loss. It serves as the primary credit-loss measure in IFRS 9 / CECL "
        "provisioning, fixed-income pricing, and Basel III standardized-approach RWA reporting."
    )
    _body(doc,
        "The model is registered in the Bank's analytics environment as GetExpectedLoss (version 7, "
        "registered 21 April 2026) in the Fixed-Income-Pricing-And-Sensitivity project. It is a "
        "closed-form actuarial model: expected loss is computed analytically from probability of default, "
        "LGD derived from LTV, and exposure at default, then discounted using a risky discount factor "
        "built from an interpolated risk-free curve plus a rating-conditional credit spread."
    )

    _callout(doc, "Recommended Actions",
        [
            "Remediate open validation finding V-2026-018-A (LTV-to-LGD HPI-aware overlay) by Q3 2026 as committed.",
            "Replace hash-based credit-spread simulation in CreditCurveModel with a live SOFR term-rate feed to eliminate the only non-production-grade component.",
            "Expand the reference loan inventory from 4 example loans to full-book production volumes ahead of the Q1 2027 annual revalidation.",
        ],
        is_numbered=True, bg=_CALLOUT_ACTIONS_BG, border=_CALLOUT_ACTIONS_BORDER,
        title_color=_CALLOUT_ACTIONS_TITLE,
    )


# ---------------------------------------------------------------------------
# Section 2 — Model Identification & Inventory
# ---------------------------------------------------------------------------

def _s2_model_identification(doc: Document) -> None:
    _h1(doc, "2.   Model Identification & Inventory")
    _hint(doc, "Registered name, version, business use, and model classification metadata.")

    _callout(doc, "Key Findings", [
        "The model is classified Tier 1 (High Materiality) on the basis of its direct use in financial reporting (ECL) and regulatory capital (RWA) — both independently meet the Bank's Tier 1 threshold.",
        "Approved uses are restricted to IFRS 9 / CECL ECL, Basel III standardized-approach RWA, and fixed-income pricing and sensitivity for the U.S. residential mortgage book only.",
        "The model is not approved for origination credit decisioning, line management, non-retail exposures, or non-U.S. portfolios.",
        "Current version 7 was registered 21 April 2026; the last material change was version 6.2 (risky discounting, August 2025).",
    ])

    _h2(doc, "2.1  Purpose and Business Use")
    _body(doc,
        "For each open residential mortgage exposure, the model produces: an implied credit rating "
        "(AAA through B) derived from 1-year PD; an implied LGD on a 5%–80% interval derived from LTV; "
        "undiscounted expected loss over the remaining contractual term; expected loss discounted by the "
        "rating-conditional risky discount factor; and risk-weighted assets under the Basel III "
        "standardized approach for retail residential real estate."
    )
    _body(doc,
        "Output is consumed by the IFRS 9 / CECL provisioning engine, the fixed-income pricing service, "
        "the regulatory capital RWA aggregator, and the monthly portfolio risk dashboards for the "
        "Mortgage Treasury function. The model is not approved for use in origination credit decisioning, "
        "line-management decisions, any non-retail exposure class, or any jurisdiction outside the U.S. "
        "residential mortgage book."
    )

    _h2(doc, "2.2  Model Classification")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Model ID", "NBT-CR-EL-007"],
            ["Registered Name", "GetExpectedLoss"],
            ["Model Name", "Expected Loss Model — Residential Mortgage Portfolio"],
            ["Asset Class", "Retail — Residential Real Estate"],
            ["Model Type", "Closed-form actuarial expected loss"],
            ["Materiality Tier", "Tier 1 (High)"],
            ["Approved Uses", "IFRS 9 / CECL ECL; Basel III standardized-approach RWA; fixed-income pricing"],
            ["Restricted Uses", "Origination decisioning; line management; non-retail; non-U.S. portfolios"],
            ["Frequency of Use", "Daily (pricing); monthly (full-portfolio ECL and RWA)"],
            ["Current Version", "7 (registered 21 April 2026)"],
            ["Last Material Change", "v6.2 — risky discounting (August 2025)"],
            ["Next Required Review", "April 2027"],
            ["Project / Repository", "nick_goble / Fixed-Income-Pricing-And-Sensitivity"],
            ["Source File", "expected_loss_model.py"],
            ["MLflow Class", "ExpectedLossModel (lines 162–198)"],
        ],
        col_widths=[2.2, 4.6],
    )


# ---------------------------------------------------------------------------
# Section 3 — Regulatory Classification
# ---------------------------------------------------------------------------

def _s3_regulatory(doc: Document) -> None:
    _h1(doc, "3.   Regulatory Classification")
    _hint(doc, "SR 26-2 tiering rationale, applicable frameworks, and examination history.")

    _callout(doc, "Key Findings", [
        "Tier 1 (High Materiality) under the Bank's SR 26-2–aligned tiering framework; annual independent revalidation required.",
        "In scope for Basel III CRE20.85 (standardized approach — retail residential real estate), IFRS 9 / ASC 326 (CECL), and SR 26-2 / SR 11-7.",
        "Model was in scope of the 2025 horizontal examination of retail credit models (exit 02 December 2025); no MRA issued.",
        "One supervisory observation recorded in 2025 (curve-input validation logic documentation); addressed in version 7.0.",
    ])

    _h2(doc, "3.1  Tiering under SR 26-2")
    _body(doc,
        "The model is classified Tier 1 because its output is used directly in financial reporting (ECL) "
        "and in regulatory capital calculation (RWA), each of which independently meets the Bank's Tier 1 "
        "thresholds for downstream financial impact. Tier 1 obligations include: annual independent "
        "revalidation by a function outside the development chain; monthly ongoing performance monitoring; "
        "effective challenge documentation for all material assumptions; and MRC approval for any "
        "material change."
    )

    _h2(doc, "3.2  Applicable Frameworks")
    _table(doc,
        ["Framework", "Applicability"],
        [
            ["SR 26-2 / SR 11-7", "Federal Reserve supervisory guidance on Model Risk Management. Tier 1 classification; annual revalidation."],
            ["Basel III (Standardized)", "RWA calculation for retail residential real estate using LTV-based risk-weight schedule (CRE20.85)."],
            ["IFRS 9 / ASC 326 (CECL)", "Lifetime ECL estimation. Model provides the EL component consumed by the central ECL engine."],
            ["Regulation B / ECOA", "Not used in credit decisioning; fair-lending review confirmed no consumer-facing decisioning use."],
            ["Internal Policy", "Model Risk Management Policy MRM-POL-001 v7.1; Ongoing Monitoring Standard MRM-STD-004."],
        ],
        col_widths=[1.8, 5.0],
    )

    _h2(doc, "3.3  Examination History")
    _body(doc,
        "The model was in scope of the 2025 horizontal examination of retail credit models "
        "(exit 02 December 2025). No matter requiring attention (MRA) was issued. One supervisory "
        "observation was recorded relating to documentation of the curve-input validation logic; this "
        "was addressed in version 7.0 (see Section 5.3)."
    )


# ---------------------------------------------------------------------------
# Section 4 — Conceptual Soundness
# ---------------------------------------------------------------------------

def _s4_conceptual_soundness(doc: Document) -> None:
    _h1(doc, "4.   Conceptual Soundness")
    _hint(doc, "Mathematical derivation of EL components: PD, LGD, EAD, discount factor, and RWA.")

    _callout(doc, "Key Findings", [
        "Core formula: EL_undisc = PD(maturity) × LGD(LTV) × EAD; discounted variant applies the risky discount factor DF = exp(−(r_f + spread_rating) × t).",
        "LGD is derived analytically: LGD = max(0.05, min(0.80, LTV − 0.60)), mapping equity cushion to expected foreclosure recovery.",
        "Credit ratings are implied from 1-year PD via PD_RATING_THRESHOLDS (AAA < 0.04% through B ≥ 2%), aligned to the Bank's internal master scale MRM-STD-007.",
        "RWA follows Basel III standardized approach: RWA = EAD × w(LTV), where w is the six-band LTV risk-weight table coded in LTV_RISK_WEIGHTS.",
        "Closed-form design was selected for transparency, decomposability, and regulatory acceptance over ML or stochastic alternatives.",
    ])

    _h2(doc, "4.1  Theoretical Framework")
    _body(doc,
        "Expected loss is computed at the loan level as the product of probability of default over the "
        "remaining contractual term, loss given default, and exposure at default "
        "(expected_loss_model.py · compute_expected_loss · lines 112–129):"
    )
    _body(doc, "    EL_undisc = PD(maturity) × LGD × EAD")
    _body(doc,
        "The undiscounted loss is discounted to present value using a risky discount factor that combines "
        "the prevailing risk-free rate at the loan's remaining term with a credit spread conditional on "
        "the implied credit rating (expected_loss_model.py · get_risky_discount_factor · lines 98–109):"
    )
    _body(doc, "    DF = exp(−(y(t) + s_r(t)) × t)")
    _body(doc,
        "where t is the remaining term in years, y(t) is the interpolated risk-free rate, and s_r(t) is "
        "the rating-conditional spread from the credit-curve repository (companion model CR-CC-003)."
    )

    _h2(doc, "4.2  Implied Credit Rating")
    _body(doc,
        "The 1-year PD supplied at scoring time is mapped to a discrete credit rating using the "
        "PD_RATING_THRESHOLDS table (expected_loss_model.py · lines 46–60), aligned to the Bank's "
        "internal master scale MRM-STD-007:"
    )
    _table(doc,
        ["One-Year PD (less than)", "Implied Rating"],
        [
            ["0.04% (0.0004)", "AAA"],
            ["0.10% (0.0010)", "AA"],
            ["0.20% (0.0020)", "A"],
            ["0.50% (0.0050)", "BBB"],
            ["2.00% (0.0200)", "BB"],
            ["(otherwise)", "B"],
        ],
        col_widths=[2.5, 2.0],
    )

    _h2(doc, "4.3  LGD Derivation")
    _body(doc,
        "LGD is derived from LTV using the rule coded in _derive_lgd() "
        "(expected_loss_model.py · line 69):"
    )
    _body(doc, "    LGD = max(0.05, min(0.80, LTV − 0.60))")
    _body(doc,
        "At LTV ≤ 60% the equity cushion is sufficient that recoveries on foreclosure are near-complete "
        "and LGD is floored at 5%. The cap of 80% bounds distressed-sale severity at very high LTVs. "
        "The relationship was originally fit to internal foreclosure data for 2008–2014 and re-checked "
        "on the 2020–2024 sample as part of version 7.0 development."
    )
    _code_ref(doc, "expected_loss_model.py", "63–69", "_derive_lgd() — LTV to LGD analytical formula")
    _figure(doc, _fig_lgd_ltv(),
            "Figure 1 — LGD as a Function of LTV\n"
            "Linear region LTV 0.65–1.40; floored at 5%, capped at 80%.")

    _h2(doc, "4.4  Risk-Weight Schedule")
    _body(doc,
        "RWA follows the Basel III standardized approach for retail residential real estate "
        "(CRE20.85). The six-band schedule is hard-coded in LTV_RISK_WEIGHTS "
        "(expected_loss_model.py · lines 30–37):"
    )
    _table(doc,
        ["LTV (≤)", "Risk Weight", "Basel III Reference"],
        [
            ["50%", "20%", "CRE20.85, Band 1"],
            ["60%", "25%", "CRE20.85, Band 2"],
            ["80%", "35%", "CRE20.85, Band 3"],
            ["90%", "50%", "CRE20.85, Band 4"],
            ["100%", "75%", "CRE20.85, Band 5"],
            ["> 100%", "105%", "CRE20.85, Band 6"],
        ],
        col_widths=[1.0, 1.2, 2.4],
    )
    _code_ref(doc, "expected_loss_model.py", "29–44", "LTV_RISK_WEIGHTS table and _ltv_risk_weight() lookup")
    _figure(doc, _fig_ltv_risk_weights(),
            "Figure 2 — Basel III LTV Risk-Weight Schedule\n"
            "Risk weights increase non-linearly beyond the 60% LTV threshold.")

    _h2(doc, "4.5  Methodology Selection")
    _body(doc,
        "A closed-form actuarial design was selected over ML or stochastic alternatives for four reasons: "
        "(1) Transparency — every output is a deterministic function of named, auditable inputs, supporting "
        "effective challenge under SR 26-2. (2) Decomposability — contribution of each driver (PD, LGD, EAD, "
        "discount factor, risk weight) is explicit. (3) Separation of concerns — PD estimation is delegated "
        "to upstream behavioral models. (4) Regulatory acceptance — aligned with the standardized-approach "
        "RWA calculation structure and the downstream ECL engine."
    )


# ---------------------------------------------------------------------------
# Section 5 — Data Lineage & Quality
# ---------------------------------------------------------------------------

def _s5_data_lineage(doc: Document) -> None:
    _h1(doc, "5.   Data Lineage & Quality")
    _hint(doc, "Input schemas, aliases, data sources, output schema, and data quality controls.")

    _callout(doc, "Key Findings", [
        "Seven canonical input columns are required; input aliases enable backward-compatible ingestion (e.g. 'pd_1y' → 'probability_of_default_1y', 'ltv' → 'loan_to_value_ratio').",
        "Numeric coercion with pre- and post-coercion NaN logging is applied to all numeric inputs — a V-2025-031 remediation now CLOSED in v7.0.",
        "Curve inputs (tenor / rate arrays) are validated for finiteness and matching lengths before any computation; corrupted curves raise a typed error.",
        "Output finiteness is verified before return; NaN or Inf in computed EL or RWA raises rather than silently passing corrupt output downstream.",
    ])

    _h2(doc, "5.1  Required Inputs")
    _table(doc,
        ["Canonical Name", "Alias", "Source", "Description"],
        [
            ["probability_of_default_1y", "pd_1y", "CR-PD-022 (Behavioral)", "1-year PD; drives implied rating."],
            ["probability_of_default_maturity", "pd_maturity", "CR-PD-024 (Lifetime)", "Cumulative PD at remaining term; primary EL driver."],
            ["loan_to_value_ratio", "ltv", "Servicing / collateral revaluation", "Current LTV; drives LGD and risk-weight selection."],
            ["current_balance", "ead", "Servicing system", "Exposure at default (outstanding balance)."],
            ["remaining_term_years", "years_to_maturity", "Servicing system", "Remaining contractual term in years; used in discounting."],
            ["curve_tenors", "—", "Treasury curve repository", "Tenor grid for the risk-free curve (years)."],
            ["curve_rates", "—", "Treasury curve repository", "Risk-free rate at each tenor (continuous compounding)."],
        ],
        col_widths=[1.8, 1.2, 1.6, 2.2],
    )
    _code_ref(doc, "expected_loss_model.py", "11–27", "REQUIRED_COLS and INPUT_ALIASES definitions")

    _h2(doc, "5.2  Outputs")
    _table(doc,
        ["Output", "Type", "Description"],
        [
            ["implied_credit_rating", "string", "Rating bucket (AAA / AA / A / BBB / BB / B) derived from 1-year PD."],
            ["implied_lgd", "float (0.05–0.80)", "Loss given default derived from current LTV."],
            ["el_undiscounted", "float", "Expected loss before discounting (exposure currency)."],
            ["el_discounted", "float", "Expected loss discounted by the rating-conditional risky discount factor."],
            ["rwa", "float", "Risk-weighted assets under Basel III standardized approach for retail RRE."],
        ],
        col_widths=[1.8, 1.4, 3.6],
    )
    _code_ref(doc, "expected_loss_model.py", "186–194", "ExpectedLossModel.predict() — output row schema")

    _h2(doc, "5.3  Data Quality Controls")
    _body(doc,
        "Input handling follows the Enterprise Data Quality Framework (EDQ-POL-002). Controls applied "
        "within the model artifact and logged at every scoring call:"
    )
    controls = [
        "Schema enforcement: required columns checked; missing column raises typed error before computation (lines 72–76).",
        "Alias resolution: shorthand names renamed to canonical form, applied mapping logged (lines 87–95).",
        "Numeric coercion: pd.to_numeric applied; pre- and post-coercion NaN counts logged per column to surface upstream corruption (lines 79–84). [Remediation for V-2025-031, CLOSED v7.0]",
        "Curve validation: tenor / rate arrays parsed, checked for finiteness, and required to have matching lengths; violations raise (lines 132–145, 151–152).",
        "Output finiteness: EL and RWA values checked for NaN / Inf before return; non-finite values raise (lines 127–128).",
    ]
    for ctrl in controls:
        p = doc.add_paragraph()
        p.add_run("\u2022  " + ctrl).font.size = Pt(10)
        p.paragraph_format.left_indent = Pt(12)
        p.paragraph_format.space_after = Pt(3)
    doc.add_paragraph()


# ---------------------------------------------------------------------------
# Section 6 — Independent Validation
# ---------------------------------------------------------------------------

def _s6_validation(doc: Document) -> None:
    _h1(doc, "6.   Independent Validation")
    _hint(doc, "Validation performed, effective challenge, benchmarking, and outstanding findings.")

    _callout(doc, "Key Findings", [
        "Annual revalidation completed 18 March 2026 by the Model Validation Group (Report MVG-2026-018); outcome: approved for continued production use.",
        "Effective challenge confirmed: LTV-to-LGD mapping refit independently — no material divergence in the 50%–95% LTV band covering 96% of the portfolio.",
        "Benchmarking against an MVG Monte Carlo simulator reproduced mean EL to within 1.8% portfolio-wide and within 4% on every LTV decile.",
        "One open finding: V-2026-018-A (Low) — LGD does not condition on regional HPI dynamics; HPI-aware overlay evaluation targeted Q3 2026.",
        "Previously open finding V-2025-031 (Medium) — numeric coercion logging — is CLOSED in v7.0.",
    ])

    _h2(doc, "6.1  Validation Summary")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Model", "GetExpectedLoss (v7)"],
            ["Validator", "Model Validation Group (MVG)"],
            ["Validation Report", "MVG-2026-018"],
            ["Validation Date", "18 March 2026"],
            ["Validation Type", "Annual revalidation (Tier 1)"],
            ["Outcome", "Approved for continued production use"],
        ],
        col_widths=[2.2, 4.6],
    )

    _h2(doc, "6.2  Effective Challenge")
    _body(doc,
        "MVG performed effective challenge on each component of the closed-form expression. The "
        "LTV-to-LGD mapping was refit independently using the same 2008–2014 foreclosure dataset and "
        "compared against the production rule — no material divergence within the 50%–95% LTV band "
        "covering 96% of the portfolio. The rating-PD threshold table was reproduced and compared "
        "against S&P historical default frequencies (consistent within rating-band tolerance). The "
        "risky discount factor was reproduced bit-exact on a 10,000-loan reference dataset."
    )

    _h2(doc, "6.3  Benchmarking")
    _body(doc,
        "MVG benchmarked production output against an independent Monte Carlo loss simulator. On the "
        "10,000-loan reference dataset, the closed-form output reproduced the simulator's mean EL to "
        "within 1.8% across the full portfolio and within 4% on every LTV decile. The simulator's "
        "tail estimates (99th-percentile loss) are not in scope for this model, which targets the mean only."
    )

    _h2(doc, "6.4  Outstanding Validation Findings")
    _table(doc,
        ["Finding", "Severity", "Description", "Status"],
        [
            ["V-2025-031", "Medium", "Numeric coercion did not consistently log pre-/post-NaN counts.", "CLOSED in v7.0"],
            ["V-2026-018-A", "Low", "LGD-LTV mapping does not condition on regional HPI dynamics; HPI overlay evaluation outstanding.", "OPEN — target Q3 2026"],
        ],
        col_widths=[1.2, 0.9, 3.4, 1.3],
    )


# ---------------------------------------------------------------------------
# Section 7 — Ongoing Performance Monitoring
# ---------------------------------------------------------------------------

def _s7_monitoring(doc: Document) -> None:
    _h1(doc, "7.   Ongoing Performance Monitoring")
    _hint(doc, "Reference-run reproduction, back-testing, PSI monitoring, and escalation thresholds.")

    _callout(doc, "Key Findings", [
        "Registered reference-run values (21 April 2026): total_el_undiscounted $41,572.94 · total_el_discounted $39,494.30 · total_rwa $406,068.25 · 4 example loans · 7-tenor curve.",
        "Monthly EL back-test variance (trailing 12 months): −7.2%, within the ±15% review threshold.",
        "LTV PSI as of March 2026: 0.084 — in the Monitor band (0.10 threshold not yet breached but flagged for close observation).",
        "All 10 input features show PSI < 0.10 (stable); RWA tie-out to capital reporting: 0.012% variance (well within 0.05% threshold).",
        "Daily curve-input completeness: 100% of loans received a valid curve.",
    ])

    _h2(doc, "7.1  Registered Reference Run")
    _body(doc,
        "The values below are recorded against the registered artifact for version 7 and serve as "
        "the reference outputs that any future implementation must reproduce. They reflect a "
        "representative four-loan reference set evaluated against a seven-tenor curve at registration "
        "time (21 April 2026, 15:19 UTC)."
    )
    _table(doc,
        ["Metric", "Value", "Recorded"],
        [
            ["total_el_undiscounted", "$41,572.94", "21 April 2026, 15:19"],
            ["total_el_discounted",   "$39,494.30", "21 April 2026, 15:19"],
            ["total_rwa",             "$406,068.25", "21 April 2026, 15:19"],
            ["example_loan_count",    "4",           "21 April 2026, 15:19"],
            ["curve_length",          "7",           "21 April 2026, 15:19"],
        ],
        col_widths=[2.2, 1.6, 3.0],
    )
    _figure(doc, _fig_portfolio_metrics(),
            "Figure 3 — Registered Reference-Run Metrics\n"
            "Values sourced from MLflow experiment run logged on registration date.")

    _h2(doc, "7.2  Production Monitoring Activities")
    _table(doc,
        ["Monitoring Activity", "Frequency", "Threshold", "Status (Mar 2026)"],
        [
            ["Reference-run reproduction", "Per release", "Bit-exact on reference set", "PASS"],
            ["EL back-test (predicted vs realized, 12-mo)", "Quarterly", "Within ±15% portfolio-wide", "PASS (−7.2%)"],
            ["PSI on LTV distribution", "Monthly", "PSI < 0.10 review; < 0.25 escalate", "0.084 — MONITOR"],
            ["RWA tie-out to capital reporting", "Monthly", "< 0.05% variance", "PASS (0.012%)"],
            ["Curve input completeness", "Daily", "100% loans receive a valid curve", "PASS"],
        ],
        col_widths=[2.2, 1.0, 2.0, 1.6],
    )
    _figure(doc, _fig_psi_monitoring(),
            "Figure 4 — Population Stability Index by Input Feature (March 2026)\n"
            "All 10 features stable (PSI < 0.10); LTV at 0.084 — flagged for close observation.")

    _h2(doc, "7.3  Triggers for Recalibration or Redevelopment")
    _body(doc,
        "Recalibration is triggered if: (i) EL back-test variance exceeds 20% for two consecutive "
        "quarters, (ii) LTV PSI exceeds 0.25, or (iii) the rating-conditional spread surface "
        "materially shifts (per CR-CC-003 monitoring). Full redevelopment is triggered if: (i) a "
        "regulatory change alters the risk-weight schedule, (ii) the PD or curve source is replaced, "
        "or (iii) validation issues a high-severity finding requiring methodological change."
    )


# ---------------------------------------------------------------------------
# Section 8 — Limitations & Compensating Controls
# ---------------------------------------------------------------------------

def _s8_limitations(doc: Document) -> None:
    _h1(doc, "8.   Limitations & Compensating Controls")
    _hint(doc, "Known model constraints, simplifying assumptions, severity, and mitigants.")

    _callout(doc, "Key Findings", [
        "PD inputs are externally supplied — the model has no independent view on PD and inherits any bias from upstream models CR-PD-022 and CR-PD-024.",
        "LGD is deterministic in LTV only; does not condition on geography, vintage, product features, or regional HPI dynamics (open finding V-2026-018-A).",
        "Risk weights are standardized approach only; the model does not produce IRB-compliant RWA.",
        "Discount factor is single-curve and does not account for prepayment optionality or convexity — handled upstream by FI-MBS-009.",
        "Curve inputs are per-loan arrays; stale or corrupted curve data would produce wrong discounting if validation were bypassed — prevented by built-in finiteness checks that cannot be disabled.",
    ])

    _table(doc,
        ["#", "Limitation / Assumption", "Severity", "Compensating Control"],
        [
            ["L1", "PD inputs externally supplied; model inherits upstream PD model bias.", "Medium",
             "Upstream PD models (CR-PD-022, CR-PD-024) are Tier 1, independently validated, and monitored under the same MRM framework."],
            ["L2", "LGD deterministic in LTV; no geography, vintage, or HPI conditioning.", "Medium",
             "Open finding V-2026-018-A tracks HPI-aware overlay evaluation (Q3 2026). Regional concentration limits applied outside the model."],
            ["L3", "Standardized-approach RWA only; no IRB output.", "Low",
             "Use restricted to standardized reporting. IRB calculation handled by CR-IRB-001."],
            ["L4", "Single-curve discounting; no prepayment or convexity adjustment.", "Low",
             "Prepayment / convexity modelled by FI-MBS-009 upstream before EL is applied."],
            ["L5", "Per-loan curve arrays; stale curve could corrupt discounting.", "Medium",
             "Curve validation (finiteness, length match) is built into the artifact and cannot be bypassed. Daily completeness monitoring at 100%."],
        ],
        col_widths=[0.4, 2.6, 0.8, 3.0],
    )

    _callout(doc, "Recommended Actions",
        [
            "Evaluate and implement an HPI-aware LGD overlay to resolve V-2026-018-A by Q3 2026.",
            "Commission a jurisdiction-specific LGD study to supplement the LTV-analytic approach for non-conforming loans.",
            "Replace hash-based credit-spread simulation with live SOFR term-rate feed in CreditCurveModel (companion model CR-CC-003).",
        ],
        is_numbered=True, bg=_CALLOUT_ACTIONS_BG, border=_CALLOUT_ACTIONS_BORDER,
        title_color=_CALLOUT_ACTIONS_TITLE,
    )


# ---------------------------------------------------------------------------
# Section 9 — Governance & Approvals
# ---------------------------------------------------------------------------

def _s9_governance(doc: Document) -> None:
    _h1(doc, "9.   Governance & Approvals")
    _hint(doc, "Model ownership, approval chain, change control, version history, and SR 26-2 compliance posture.")

    _callout(doc, "Key Findings", [
        "NBT-CR-EL-007 v7.0 approved by the Model Risk Committee at its November 2025 meeting following MVG revalidation.",
        "Model inventory ID: MID-2024-0037. Tier 1 (High Materiality). Next revalidation due March 2027.",
        "All material changes require MRC approval, re-validation, and version bump; non-material changes require Model Owner approval and notation in the Model Inventory System.",
        "SR 26-2 compliance status: Compliant — all required documentation, monitoring, governance, and validation elements in place.",
    ])

    _h2(doc, "9.1  Roles and Responsibilities")
    _table(doc,
        ["Role", "Holder", "Responsibilities"],
        [
            ["Model Owner", "Director, Fixed Income Analytics", "Model performance, documentation, monitoring, and finding remediation."],
            ["Model Developer", "Senior Quantitative Analyst", "Technical development, recalibration, and documentation."],
            ["Business Sponsor", "MD, Mortgage Treasury", "Appropriateness of model application for the mortgage book."],
            ["Independent Validator", "Model Validation Group (reports to CRO)", "Initial and ongoing validation per SR 26-2."],
            ["Model Risk Committee", "Chaired by CRO", "Approves new models, material changes, and tier assignments."],
        ],
        col_widths=[1.6, 1.8, 3.4],
    )

    _h2(doc, "9.2  Change Control")
    _body(doc,
        "Material changes (affecting model output by > 5% on the registered reference run, or any "
        "change to inputs, functional form, LGD rule, rating-PD mapping, risk-weight schedule, or "
        "discounting basis) require MRC approval, re-validation, and a version bump. Non-material "
        "changes (logging refinements, error-message clarification, environment patches) require "
        "Model Owner approval and notation in the Model Inventory System."
    )

    _h2(doc, "9.3  Version History")
    _table(doc,
        ["Version", "Date", "Author", "Change Summary"],
        [
            ["v7.0", "2025-11-14", "Credit Risk Analytics", "Numeric coercion logging (V-2025-031 remediation); curve-input documentation update; MRC approval."],
            ["v6.2", "2025-08-01", "Credit Risk Analytics", "Risky discounting integration for IFRS 9 stage 2/3; alias schema expansion."],
            ["v6.0", "2025-03-01", "Credit Risk Analytics", "Basel III risk-weight schedule update; curve tenor extension to 30Y."],
            ["v5.0", "2023-12-01", "Model Governance", "Initial SR 11-7 / Basel III compliance certification."],
        ],
        col_widths=[0.8, 1.0, 1.8, 3.2],
    )

    _h2(doc, "9.4  Validation Status")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Most recent validation", "Annual revalidation, 18 March 2026 (MVG-2026-018)"],
            ["Outcome", "Approved for continued production use, Tier 1"],
            ["Open findings", "1 (Low severity, V-2026-018-A) — target Q3 2026"],
            ["Next revalidation due", "March 2027 (annual cadence)"],
        ],
        col_widths=[2.2, 4.6],
    )


# ---------------------------------------------------------------------------
# Section 10 — Appendix
# ---------------------------------------------------------------------------

def _s10_appendix(doc: Document) -> None:
    _h1(doc, "10.  Appendix")
    _hint(doc, "Registered artifact references, source code index, glossary, and bibliography.")

    _callout(doc, "Key Findings", [
        "All model logic is implemented in five Python source files totalling ~500 lines of production code, all MLflow pyfunc registered.",
        "ExpectedLossModel, LoanPDModel, and CreditCurveModel are independently versioned sub-models sharing the same MLflow experiment.",
        "Complete line-level code index provided below; all citations in this document resolve to ranges in the registered artifact expected_loss_model.py v7.",
    ])

    _h2(doc, "A.  Registered Artifact References")
    _table(doc,
        ["Attribute", "Value"],
        [
            ["Registered Name", "GetExpectedLoss"],
            ["Registered Version", "7"],
            ["Registered By", "nick_goble"],
            ["Registered Date", "21 April 2026"],
            ["Source Project", "nick_goble / Fixed-Income-Pricing-And-Sensitivity"],
            ["Source File", "expected_loss_model.py"],
            ["Class", "ExpectedLossModel (mlflow.pyfunc.PythonModel, lines 162–198)"],
            ["Companion Model (Curves)", "CR-CC-003, Credit Spread Curve Service"],
            ["Upstream Inputs (PD)", "CR-PD-022 (1-year); CR-PD-024 (Lifetime)"],
        ],
        col_widths=[2.2, 4.6],
    )

    _h2(doc, "B.  Source Code Index")
    _table(doc,
        ["File", "Lines", "Symbol / Description"],
        [
            ["expected_loss_model.py", "11–19", "REQUIRED_COLS — canonical input column list"],
            ["expected_loss_model.py", "21–27", "INPUT_ALIASES — accepted shorthand input names"],
            ["expected_loss_model.py", "29–37", "LTV_RISK_WEIGHTS — Basel III LTV-to-risk-weight schedule"],
            ["expected_loss_model.py", "40–44", "_ltv_risk_weight() — risk-weight selection logic"],
            ["expected_loss_model.py", "46–52", "PD_RATING_THRESHOLDS — PD-to-rating mapping table"],
            ["expected_loss_model.py", "55–60", "_derive_credit_rating() — PD to implied rating"],
            ["expected_loss_model.py", "63–69", "_derive_lgd() — LGD from LTV: max(0.05, min(0.80, LTV−0.60))"],
            ["expected_loss_model.py", "72–76", "_ensure_columns() — schema enforcement"],
            ["expected_loss_model.py", "79–84", "_coerce_numeric() — numeric coercion with NaN logging"],
            ["expected_loss_model.py", "87–95", "_apply_aliases() — alias resolution with logging"],
            ["expected_loss_model.py", "98–109", "get_risky_discount_factor() — DF = exp(−(r_f + spread) × t)"],
            ["expected_loss_model.py", "112–129", "compute_expected_loss() — core EL = PD × LGD × EAD + RWA"],
            ["expected_loss_model.py", "132–145", "_coerce_curve_array() — curve parsing and finiteness check"],
            ["expected_loss_model.py", "148–159", "_curve_from_arrays() — curve DataFrame construction"],
            ["expected_loss_model.py", "162–198", "ExpectedLossModel.predict() — MLflow pyfunc entry point"],
            ["loan_pd_model.py", "7–41", "REQUIRED_COLS, INPUT_ALIASES, FEATURE_NAME_MAP"],
            ["loan_pd_model.py", "71–124", "LoanPDModel — XGBoost PD + maturity scaling"],
            ["credit_curve_model.py", "1–61", "Yield curve construction with rating spreads"],
            ["credit_curve_model.py", "64–80", "build_credit_curve() — DataFrame output"],
            ["credit_curve_model.py", "91–96", "CreditCurveModel.predict() — MLflow pyfunc interface"],
            ["register_models.py", "1–50", "MLflow model registration for all three components"],
            ["train_pd_model.py", "1–80", "XGBoost training pipeline with MLflow tracking"],
            ["test_models.py", "1–60", "End-to-end model test suite"],
        ],
        col_widths=[2.0, 0.8, 4.0],
    )

    _h2(doc, "C.  Glossary")
    _table(doc,
        ["Term", "Definition"],
        [
            ["Basel III Standardized Approach", "Regulatory framework for capital adequacy; defines risk weights for exposure classes including retail residential real estate (CRE20.85)."],
            ["CECL (ASC 326)", "U.S. accounting standard for current expected credit loss estimation."],
            ["EAD", "Exposure at default. In this model, current outstanding balance."],
            ["ECL", "Expected credit loss."],
            ["EL", "Expected loss: product of PD, LGD, and EAD over a specified horizon."],
            ["IFRS 9", "International Financial Reporting Standard 9; lifetime ECL framework outside the U.S."],
            ["LGD", "Loss given default; fraction of EAD not recovered through collateral or other means."],
            ["LTV", "Loan-to-value ratio; outstanding balance divided by current collateral value."],
            ["MRC", "Model Risk Committee."],
            ["MVG", "Model Validation Group."],
            ["PD", "Probability of default."],
            ["PSI", "Population Stability Index; drift measure comparing current to reference distribution."],
            ["RWA", "Risk-weighted assets; denominator of regulatory capital ratios."],
            ["SR 11-7", "Federal Reserve Supervisory Guidance on Model Risk Management (2011)."],
            ["SR 26-2", "Federal Reserve Supervisory Guidance on Model Risk Management (2026 update)."],
            ["Tier 1", "Highest materiality classification; applies to models with direct financial reporting or regulatory capital impact."],
        ],
        col_widths=[2.0, 4.8],
    )

    _h2(doc, "D.  Bibliography")
    refs = [
        "Board of Governors of the Federal Reserve System (2026). SR 26-2: Supervisory Guidance on Model Risk Management.",
        "Board of Governors of the Federal Reserve System (2011). SR 11-7: Guidance on Model Risk Management.",
        "Basel Committee on Banking Supervision (2017). Basel III: Finalising post-crisis reforms. Bank for International Settlements.",
        "IFRS Foundation (2014). IFRS 9 Financial Instruments. International Accounting Standards Board.",
        "Chen, T. & Guestrin, C. (2016). XGBoost: A scalable tree boosting system. KDD 2016, 785–794.",
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

    _title_page(doc)
    _toc(doc)

    _s1_executive_summary(doc);    doc.add_page_break()
    _s2_model_identification(doc); doc.add_page_break()
    _s3_regulatory(doc);           doc.add_page_break()
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
