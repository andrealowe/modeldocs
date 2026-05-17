#!/usr/bin/env python3
"""ModelDocs — FastHTML web app for Domino model documentation generation.

Serves as a Domino Extension mounted on the "Models" mount point. When opened
from a model's detail page, Domino passes modelId and modelVersionId as query
parameters; the app also expects projectId so it knows where to run jobs.
"""

from __future__ import annotations

import json
import os
import pathlib
from typing import Optional

from fasthtml.common import *
from starlette.requests import Request

from domino_auth import configure_auth, user_auth

configure_auth(user_auth)

# Inline SVG logo — white paths, designed for dark backgrounds
_LOGO_SVG = (pathlib.Path(__file__).parent.parent / "domino-logo.svg").read_text()

from default_consts import DEFAULT_OPENAI_MODEL

from studio.state import (
    _STARTUP_WARNINGS,
    _resolve_request_project_id,
    _resolve_request_model_id,
    _resolve_request_model_version_id,
    domino_client,
)
from studio.styles import STUDIO_CSS
from studio.scripts import MAIN_DOM_JS
from studio.ui_components import (
    _render_warnings_banner,
    _validate_environment,
    validate_studio_domino_compute_environment,
)
from studio.font_assets import (
    STUDIO_FONT_BASE_PATCH_JS,
    fontawesome_faces_css,
    register_font_assets,
)
from studio.routes_api import register_api_routes
from studio.routes_job import register_job_routes

from domino_job_store import ensure_database


# ---------------------------------------------------------------------------
# Template loader JS — injected per-request so the app URL prefix is correct
# ---------------------------------------------------------------------------

_TEMPLATE_EDITOR_JS = r"""
(function() {

    // ── Section list parser ────────────────────────────────────────────────
    // Reads "  - SectionName" lines from the sections: block in the YAML.
    function parseTemplateSections(yaml) {
        var sections = [];
        var inSections = false;
        var lines = (yaml || '').split('\n');
        for (var i = 0; i < lines.length; i++) {
            var line = lines[i];
            if (/^sections\s*:/.test(line)) { inSections = true; continue; }
            if (inSections) {
                // Stop when a new top-level key starts (no leading whitespace, not a list item)
                if (/^[a-zA-Z_]/.test(line)) { inSections = false; continue; }
                var m = line.match(/^\s+-\s+"?(.+?)"?\s*$/);
                if (m) sections.push(m[1].trim());
            }
        }
        return sections;
    }

    function renderSectionList(sections) {
        var list = document.getElementById('tpl-section-list');
        var counter = document.getElementById('tpl-sections-count');
        if (!list) return;
        list.innerHTML = sections.map(function(name, idx) {
            var isPerModel = name.indexOf(': per_model') >= 0;
            var displayName = name.replace(': per_model', '').trim();
            return '<div class="tpl-section-row">'
                + '<span class="tpl-section-num">' + (idx + 1) + '</span>'
                + '<span class="tpl-section-name">' + displayName + '</span>'
                + (isPerModel ? '<span class="tpl-section-badge">per model</span>' : '')
                + '</div>';
        }).join('');
        if (counter) counter.textContent = 'Sections\u00a0(' + sections.length + ')';
    }

    // Initial render from the textarea that was pre-filled server-side
    var tplTextarea = document.getElementById('field-spec_content');
    if (tplTextarea) {
        renderSectionList(parseTemplateSections(tplTextarea.value));
    }

    // ── Live update as user edits the textarea ─────────────────────────────
    var _debounceTimer = null;
    if (tplTextarea) {
        tplTextarea.addEventListener('input', function() {
            clearTimeout(_debounceTimer);
            _debounceTimer = setTimeout(function() {
                renderSectionList(parseTemplateSections(tplTextarea.value));
            }, 300);
        });
    }

    // ── Template selector: fetch from API and reload section list ──────────
    var tplSelect = document.getElementById('template-selector');
    var tplLoading = document.getElementById('template-loading-indicator');

    function setTemplateLoading(on) {
        if (tplLoading) tplLoading.style.display = on ? '' : 'none';
        if (tplTextarea) tplTextarea.disabled = !!on;
    }

    function loadTemplate(name) {
        if (!tplTextarea || !name) return;
        setTemplateLoading(true);
        fetch(_adUrl('api/template-content') + '?name=' + encodeURIComponent(name))
            .then(function(r) {
                if (!r.ok) { setTemplateLoading(false); return null; }
                return r.text();
            })
            .then(function(text) {
                if (!text) return;
                tplTextarea.value = text;
                renderSectionList(parseTemplateSections(text));
                setTemplateLoading(false);
            })
            .catch(function() { setTemplateLoading(false); });
    }

    if (tplSelect) {
        tplSelect.addEventListener('change', function() {
            loadTemplate(tplSelect.value);
        });
    }

    // ── Output format selector (UI-only) ──────────────────────────────────
    var fmtRadios = document.querySelectorAll('input[name="output_format"]');
    fmtRadios.forEach(function(r) {
        r.addEventListener('change', function() {
            var label = document.getElementById('generate-btn-label');
            if (label) {
                var fmt = r.value === 'word' ? 'Word' : r.value === 'markdown' ? 'Markdown' : 'LaTeX';
                label.textContent = 'Generate\u00a0' + fmt + '\u00a0Documentation';
            }
        });
    });

    // ── Demo mode — intercept Generate when ?demo=1 is in the URL ─────────
    var _demoParam = new URLSearchParams(window.location.search).get('demo');
    // Auto-enable demo when running via a notebook-session proxy (dev/preview),
    // or when ?demo= / ?demo=1 is in the URL. Disable with ?demo=0 or ?demo=false.
    var _isNotebookProxy = window.location.pathname.indexOf('/notebookSession') >= 0
        || window.location.pathname.indexOf('/proxy/') >= 0;
    var _isDemoMode = _isNotebookProxy
        || (_demoParam !== null && _demoParam !== 'false' && _demoParam !== '0');

    var _DEMO_STEPS = [
        'Scanning source code\u2026',
        'Reading Domino experiment runs\u2026',
        'Collecting model metrics and governance evidence\u2026',
        'Planning document sections\u2026',
        'Generating compliance report\u2026',
    ];

    function _demoOutputHtml(docxUrl, ipynbUrl) {
        return '<div class="demo-output-card">'
            + '<div class="demo-output-header">'
            +   '<span class="history-status history-status-succeeded">COMPLETED</span>'
            +   '<span class="demo-output-time">Generated just now</span>'
            + '</div>'
            + '<div class="demo-output-title">NBT-CR-EL-007 Compliance Report</div>'
            + '<div class="demo-output-subtitle">Expected Loss Model \u2014 Residential Mortgage Portfolio</div>'
            + '<div class="demo-output-meta">10\u00a0sections\u00a0\u00b7\u00a014\u00a0pages\u00a0\u00b7\u00a03\u00a0context sources</div>'
            + '<div class="demo-output-files">'
            +   '<a href="' + docxUrl + '" class="demo-file-btn" download>'
            +     '<span class="fa-icon fa-file-word demo-file-icon"></span>'
            +     '<span>Download .docx</span>'
            +   '</a>'
            +   '<a href="' + ipynbUrl + '" class="demo-file-btn demo-file-btn--nb" download>'
            +     '<span class="fa-icon fa-code demo-file-icon"></span>'
            +     '<span>Download .ipynb</span>'
            +   '</a>'
            + '</div>'
            + '<p class="demo-output-note">'
            +   'Tables and figures were generated programmatically. '
            +   'The notebook contains all the code to reproduce them.'
            + '</p>'
            + '</div>';
    }

    function _demoProgressHtml(stepText) {
        return '<div class="demo-progress-card">'
            + '<div class="demo-progress-spinner"></div>'
            + '<div class="demo-progress-steps">'
            +   '<span class="demo-progress-step-text" id="demo-step-text">' + stepText + '</span>'
            + '</div>'
            + '</div>';
    }

    if (_isDemoMode) {
        var mainForm = document.getElementById('main-form');
        if (mainForm) {
            mainForm.addEventListener('submit', function(e) {
                e.preventDefault();
                e.stopImmediatePropagation();

                var btn = document.getElementById('generate-btn');
                if (btn) btn.disabled = true;

                var historyEl = document.getElementById('job-history-content');
                if (historyEl) historyEl.innerHTML = _demoProgressHtml(_DEMO_STEPS[0]);

                var stepIdx = 0;
                var stepInterval = setInterval(function() {
                    stepIdx++;
                    if (stepIdx < _DEMO_STEPS.length) {
                        var el = document.getElementById('demo-step-text');
                        if (el) el.textContent = _DEMO_STEPS[stepIdx];
                    } else {
                        clearInterval(stepInterval);
                    }
                }, 2000);

                var totalDelay = (_DEMO_STEPS.length) * 2000;
                setTimeout(function() {
                    clearInterval(stepInterval);
                    var docxUrl = _adUrl('demo/report-docx');
                    var ipynbUrl = _adUrl('demo/report-ipynb');
                    if (historyEl) historyEl.innerHTML = _demoOutputHtml(docxUrl, ipynbUrl);
                    if (btn) btn.disabled = false;
                }, totalDelay);
            }, true); // capture phase — runs before MAIN_DOM_JS submit handler
        }
    }
})();
"""


# ---------------------------------------------------------------------------
# FastHTML app
# ---------------------------------------------------------------------------

app, rt = fast_app(
    pico=False,
    hdrs=(
        Style(STUDIO_CSS),
        Script(MAIN_DOM_JS),
    )
)

ensure_database()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _model_context_banner(model_id: Optional[str], model_version_id: Optional[str]) -> Optional[object]:
    """Render the model context pill/banner when opened via a Models Extension."""
    if not model_id:
        return None
    version_label = f"v{model_version_id}" if model_version_id else "latest"
    return Div(
        Div(
            Span(cls="fa-icon fa-cube model-banner-icon"),
            Div(
                Span("Model context", cls="model-banner-eyebrow"),
                Div(
                    Span(model_id, cls="model-banner-name", id="model-banner-name"),
                    Span(version_label, cls="model-banner-version"),
                    cls="model-banner-title-row",
                ),
                cls="model-banner-text",
            ),
            Div(
                Span(cls="fa-icon fa-circle-check model-banner-check"),
                Span("Loaded", cls="model-banner-loaded-label"),
                cls="model-banner-loaded",
            ),
            cls="model-banner-inner",
        ),
        # Hidden inputs so JS can pick up modelId / modelVersionId
        Input(type="hidden", id="field-model_id", value=model_id or ""),
        Input(type="hidden", id="field-model_version_id", value=model_version_id or ""),
        cls="model-context-banner",
    )


def _parse_sections_from_yaml(yaml_text: str) -> list[str]:
    """Extract section names from a doc_spec YAML string."""
    sections = []
    in_sections = False
    for line in yaml_text.splitlines():
        if line.startswith("sections:"):
            in_sections = True
            continue
        if in_sections:
            if line and line[0].isalpha():
                break  # new top-level key
            stripped = line.strip()
            if stripped.startswith("- "):
                name = stripped[2:].strip().strip('"').strip("'")
                if name:
                    sections.append(name)
    return sections


def _template_editor_section(default_content: str) -> object:
    """Inline YAML template editor — sections shown visually, YAML text editable."""
    sections = _parse_sections_from_yaml(default_content)

    section_rows = []
    for i, name in enumerate(sections, 1):
        is_per_model = ": per_model" in name
        display_name = name.replace(": per_model", "").strip()
        section_rows.append(
            Div(
                Span(str(i), cls="tpl-section-num"),
                Span(display_name, cls="tpl-section-name"),
                Span("per model", cls="tpl-section-badge") if is_per_model else "",
                cls="tpl-section-row",
            )
        )

    return Div(
        H4("Template", cls="spec-section-heading"),
        # Template selector dropdown
        Div(
            Select(
                Option("Compliance Report", value="compliance", selected=True),
                Option("Default (model doc)", value="default"),
                Option("Model Validation Report", value="validation"),
                Option("Fair Lending Assessment", value="fair-lending"),
                Option("Stress Testing Summary", value="stress-test"),
                id="template-selector",
                cls="template-selector-select",
            ),
            Span("Loading…", id="template-loading-indicator", cls="template-loading-indicator", style="display:none;"),
            cls="template-selector-row",
        ),
        # Section outline — updates live as user edits the YAML
        Div(
            Div(
                Span(f"Sections\u00a0({len(sections)})", cls="tpl-sections-label", id="tpl-sections-count"),
                cls="tpl-sections-header",
            ),
            Div(*section_rows, id="tpl-section-list", cls="tpl-section-list"),
            cls="tpl-sections-panel",
        ),
        # Editable YAML textarea — pre-filled server-side, no async flicker
        Div(
            Span("Edit template", cls="tpl-editor-label"),
            Textarea(
                default_content,
                id="field-spec_content",
                name="spec_content",
                cls="template-editor-textarea",
                spellcheck="false",
                autocomplete="off",
            ),
            cls="template-editor-wrap",
        ),
        Div(
            A(
                Span(cls="fa-icon fa-download"),
                " Download",
                href="api/download-compliance-template",
                data_app_rel="api/download-compliance-template",
                download="compliance_report_spec.yaml",
                cls="app-link template-action-link",
                id="template-download-link",
            ),
            A(
                Span(cls="fa-icon fa-upload"),
                " Upload custom",
                href="#",
                id="spec-upload-trigger",
                cls="app-link template-action-link",
            ),
            Input(type="file", accept=".yaml,.yml", id="spec-machine-upload", cls="hidden-upload"),
            cls="template-action-row",
        ),
        Input(name="spec_path", id="field-spec_path", type="hidden", value="__inline__"),
        cls="field studio-spec-block",
    )


def _output_format_selector() -> object:
    return Div(
        H4("Output format", cls="spec-section-heading"),
        Div(
            Label(
                Input(type="radio", name="output_format", value="word", checked=True),
                Div(
                    Span(cls="fa-icon fa-file-word output-fmt-icon"),
                    Span("Word (.docx)", cls="output-fmt-label"),
                    cls="output-fmt-inner",
                ),
                cls="output-fmt-option output-fmt-option--active",
                id="fmt-word",
            ),
            Label(
                Input(type="radio", name="output_format", value="markdown"),
                Div(
                    Span(cls="fa-icon fa-file-lines output-fmt-icon"),
                    Span("Markdown (.md)", cls="output-fmt-label"),
                    cls="output-fmt-inner",
                ),
                cls="output-fmt-option",
                id="fmt-markdown",
            ),
            Label(
                Input(type="radio", name="output_format", value="latex"),
                Div(
                    Span(cls="fa-icon fa-file-code output-fmt-icon"),
                    Span("LaTeX (.tex)", cls="output-fmt-label"),
                    cls="output-fmt-inner",
                ),
                cls="output-fmt-option",
                id="fmt-latex",
            ),
            cls="output-fmt-group",
        ),
        cls="output-format-section",
    )


# ---------------------------------------------------------------------------
# index() — ModelDocs 2-Column Layout
# ---------------------------------------------------------------------------

@rt("/")
async def index(req: Request):
    host = req.headers.get("x-forwarded-host") or req.headers.get("host") or ""
    scheme = req.headers.get("x-forwarded-proto", "https")
    domino_client.set_ui_host(host, scheme)

    project_id = _resolve_request_project_id(req)
    model_id = _resolve_request_model_id(req)
    model_version_id = _resolve_request_model_version_id(req)

    # Bootstrap page when projectId is missing (Extension passes it separately)
    if not project_id:
        return (
            Title("ModelDocs — Domino"),
            Style(fontawesome_faces_css()),
            Script(STUDIO_FONT_BASE_PATCH_JS),
            Style(STUDIO_CSS),
            Script(r"""
                (function() {
                    var pid = null;

                    if (window.location.hash) {
                        var h = window.location.hash.substring(1);
                        if (h.charAt(0) === '?') h = h.substring(1);
                        pid = new URLSearchParams(h).get('projectId');
                    }

                    if (!pid && window.parent !== window) {
                        try {
                            var pLoc = window.parent.location;
                            pid = new URLSearchParams(pLoc.search).get('projectId');
                            if (!pid && pLoc.hash) {
                                var ph = pLoc.hash.substring(1);
                                if (ph.charAt(0) === '?') ph = ph.substring(1);
                                pid = new URLSearchParams(ph).get('projectId');
                            }
                        } catch(e) { /* cross-origin */ }
                    }

                    if (!pid && document.referrer) {
                        try {
                            pid = new URL(document.referrer).searchParams.get('projectId');
                        } catch(e) {}
                    }

                    if (pid) {
                        var url = new URL(window.location.href);
                        url.searchParams.set('projectId', pid);
                        window.location.replace(url.toString());
                        return;
                    }

                    var allowedOrigin = window.location.origin;
                    window.addEventListener('message', function(e) {
                        if (e.origin !== allowedOrigin) return;
                        if (e.data && typeof e.data === 'object' && e.data.projectId) {
                            var url = new URL(window.location.href);
                            url.searchParams.set('projectId', e.data.projectId);
                            window.location.replace(url.toString());
                        }
                    });

                    setTimeout(function() {
                        var el = document.getElementById('project-id-error');
                        if (el) el.style.display = '';
                    }, 2000);
                })();
            """),
            Div(
                Div(NotStr(_LOGO_SVG), cls="domino-header-inner"),
                cls="domino-header",
            ),
            Div(
                Div(
                    Div(
                        Span("Resolving project…", cls="bootstrap-status-text"),
                    ),
                    cls="bootstrap-status-wrap",
                ),
                Div(
                    Div(
                        H2("Project ID required"),
                        P(
                            "This app must be launched with a ",
                            Code("projectId"),
                            " query parameter. If you're opening it as a Domino Extension, "
                            "make sure both ",
                            Code("projectId"),
                            " and ",
                            Code("modelId"),
                            " are passed.",
                        ),
                        cls="bootstrap-error-card",
                    ),
                    id="project-id-error",
                    cls="bootstrap-error-wrap",
                    style="display: none;",
                ),
                cls="page",
            ),
        )

    # Resolve project display name
    project_display_name: Optional[str] = None
    if project_id:
        info = domino_client.resolve_project(project_id)
        if info:
            project_display_name = f"{info.owner_username}/{info.name}"

    try:
        from autodoc.core.config import Settings as _StudioSettings
        _ss = _StudioSettings()
        _default_openai_base_url = _ss.openai_base_url or "https://api.openai.com/v1"
        _default_anthropic_base_url = _ss.anthropic_base_url or "https://api.anthropic.com"
    except Exception:
        _default_openai_base_url = "https://api.openai.com/v1"
        _default_anthropic_base_url = "https://api.anthropic.com"

    import auth_context
    try:
        owner_id = auth_context.get_viewing_user().id
    except Exception:
        owner_id = ""

    tier_options = []
    try:
        tier_rows = domino_client.list_hardware_tiers(project_id=project_id) or []
        default_tier = domino_client.get_project_default_tier()
        for t in tier_rows:
            tid = t.get("id", "")
            label = t.get("option_label") or t.get("name") or tid
            is_default = t.get("isDefault", False) or tid == default_tier
            tier_options.append(Option(label, value=tid, selected=is_default))
    except Exception:
        tier_options = []
    if not tier_options:
        tier_options = [Option("(default)", value="")]

    compute_env_errors = validate_studio_domino_compute_environment(domino_client)
    studio_errors_panel = Div(id="studio-errors-panel", cls="studio-errors-panel")

    # ── Advanced settings modal ───────────────────────────────────────────
    advanced_modal_fields = [
        Div(
            Div(
                Label("API key", for_="field-api_key"),
                Span("\u24d8", cls="info-tooltip", data_tooltip="Overrides the ANTHROPIC_API_KEY / OPENAI_API_KEY environment variable for this run."),
                cls="label-row",
            ),
            Input(
                name="api_key",
                id="field-api_key",
                type="password",
                placeholder="Paste key here if not set in environment",
                autocomplete="off",
            ),
            cls="field",
        ),
        Div(
            Div(
                Label("Hardware tier", for_="field-hardware_tier"),
                Span("\u24d8", cls="info-tooltip", data_tooltip="Compute tier for the Domino job."),
                cls="label-row",
            ),
            Select(
                *tier_options,
                name="hardware_tier",
                id="field-hardware_tier",
                cls="hw-tier-select",
            ),
            cls="field",
        ),
        Div(
            Label("Source code root path", for_="code-root-prefix"),
            Div(
                Select(
                    Option("Loading...", value="", selected=True, disabled=True),
                    id="code-root-prefix",
                    cls="code-root-prefix code-root-loading",
                    aria_label="Code root base path",
                ),
                Input(
                    id="code-root-suffix",
                    type="text",
                    placeholder="subdirectory (optional)",
                    cls="code-root-suffix",
                ),
                Input(
                    name="code_root",
                    id="field-code_root",
                    type="hidden",
                    value="",
                ),
                cls="code-root-wrap",
            ),
            cls="field",
        ),
        Div(
            Label("Provider", for_="field-provider"),
            Select(
                Option("Anthropic", value="anthropic"),
                Option("OpenAI (Compatible)", value="openai", selected=True),
                name="provider",
                id="field-provider",
            ),
            cls="field",
        ),
        Div(
            Div(
                Label("Provider API base URL", for_="field-provider_base_url"),
                Span(
                    "\u24d8",
                    cls="info-tooltip",
                    data_tooltip="HTTP base URL for the selected provider.",
                ),
                cls="label-row",
            ),
            Input(
                name="provider_base_url",
                id="field-provider_base_url",
                type="text",
                value=_default_openai_base_url,
                placeholder=_default_openai_base_url,
                data_default_openai=_default_openai_base_url,
                data_default_anthropic=_default_anthropic_base_url,
            ),
            cls="field",
            id="provider-base-url-field",
        ),
        Div(
            Div(
                Label("Model", for_="field-model"),
                Span("\u24d8", cls="info-tooltip", data_tooltip="Provider model name."),
                cls="label-row",
            ),
            Input(
                name="model",
                id="field-model",
                type="text",
                value=DEFAULT_OPENAI_MODEL,
                placeholder=DEFAULT_OPENAI_MODEL,
            ),
            cls="field",
            id="model-name-field",
        ),
        Div(
            H4("Filters", cls="spec-section-heading advanced-filters-heading"),
            Div(
                Div(
                    Div(
                        Label("Domino model names", for_="field-filtered_model_names"),
                        Span("\u24d8", cls="info-tooltip", data_tooltip="Comma-separated. Supports wildcards: * and ?"),
                        cls="label-row",
                    ),
                    Input(
                        name="filtered_model_names",
                        id="field-filtered_model_names",
                        type="text",
                        placeholder="model1, churn*, fraud-*",
                    ),
                    cls="field",
                ),
                Div(
                    Div(
                        Label("Domino experiment names", for_="field-filtered_experiment_names"),
                        Span("\u24d8", cls="info-tooltip", data_tooltip="Comma-separated. Supports wildcards: * and ?"),
                        cls="label-row",
                    ),
                    Input(
                        name="filtered_experiment_names",
                        id="field-filtered_experiment_names",
                        type="text",
                        placeholder="exp1, exp2, my-experiment*",
                    ),
                    cls="field",
                ),
                Label(
                    Input(type="checkbox", name="latest_only", id="field-latest_only", checked=True),
                    Span("Latest version only"),
                    cls="checkbox-field",
                ),
                cls="advanced-content",
            ),
            cls="field",
        ),
    ]

    advanced_modal = Div(
        Div(
            Div(
                H3("Advanced settings", id="studio-advanced-modal-title", cls="studio-modal-title"),
                cls="studio-modal-header",
            ),
            Div(*advanced_modal_fields, cls="studio-modal-body advanced-content"),
            Div(
                Button(
                    "Close",
                    type="button",
                    id="studio-advanced-close",
                    cls="primary",
                    aria_label="Close advanced settings",
                ),
                cls="studio-modal-footer",
            ),
            cls="studio-modal",
            role="dialog",
            aria_modal="true",
            aria_labelledby="studio-advanced-modal-title",
        ),
        id="studio-advanced-modal",
        cls="studio-modal-overlay",
        aria_hidden="true",
    )

    # ── Model context banner ───────────────────────────────────────────────
    banner = _model_context_banner(model_id, model_version_id)

    # ── Left column: model banner + template editor + generate ────────────
    left_col_children = [
        Div(H2("Generate documentation"), cls="col-header"),
    ]

    configure_card_children = []

    # Project header row
    configure_card_children.append(
        H3(
            Span("Project: ", cls="target-project-label-prefix"),
            Span(
                project_display_name or project_id or "",
                cls="target-project-display",
            ),
            cls="target-project-row",
        ),
    )

    # Model context banner (only when opened from a Model Extension)
    if banner:
        configure_card_children.append(banner)

    # Context sources section
    configure_card_children.append(
        Div(
            Div(
                Span("Context sources", cls="ctx-section-label"),
                Span("Select which data sources the report generator will use.", cls="ctx-section-desc"),
                cls="ctx-section-header",
            ),
            Div(
                Label(
                    Input(type="checkbox", id="ctx-code", checked=True, cls="ctx-checkbox"),
                    Div(
                        Span(cls="fa-icon fa-code ctx-item-icon"),
                        Div(
                            Span("Code", cls="ctx-item-title"),
                            Span("Repository files and ML pipeline logic", cls="ctx-item-desc"),
                            cls="ctx-item-text",
                        ),
                        cls="ctx-item-body",
                    ),
                    cls="ctx-item",
                ),
                Label(
                    Input(type="checkbox", id="ctx-experiments", checked=True, cls="ctx-checkbox"),
                    Div(
                        Span(cls="fa-icon fa-flask ctx-item-icon"),
                        Div(
                            Span("Experiments", cls="ctx-item-title"),
                            Span("Domino experiment runs and logged metrics", cls="ctx-item-desc"),
                            cls="ctx-item-text",
                        ),
                        cls="ctx-item-body",
                    ),
                    cls="ctx-item",
                ),
                Label(
                    Input(type="checkbox", id="ctx-data", checked=True, cls="ctx-checkbox"),
                    Div(
                        Span(cls="fa-icon fa-database ctx-item-icon"),
                        Div(
                            Span("Data", cls="ctx-item-title"),
                            Span("Data sources and feature definitions", cls="ctx-item-desc"),
                            cls="ctx-item-text",
                        ),
                        cls="ctx-item-body",
                    ),
                    cls="ctx-item",
                ),
                Label(
                    Input(type="checkbox", id="ctx-metrics", checked=True, cls="ctx-checkbox"),
                    Div(
                        Span(cls="fa-icon fa-chart-line ctx-item-icon"),
                        Div(
                            Span("Model metrics", cls="ctx-item-title"),
                            Span("Performance and evaluation results", cls="ctx-item-desc"),
                            cls="ctx-item-text",
                        ),
                        cls="ctx-item-body",
                    ),
                    cls="ctx-item",
                ),
                Label(
                    Input(type="checkbox", id="ctx-governance", checked=True, cls="ctx-checkbox"),
                    Div(
                        Span(cls="fa-icon fa-shield-halved ctx-item-icon"),
                        Div(
                            Span("Governance evidence", cls="ctx-item-title"),
                            Span("Artifacts, approvals, and audit trail", cls="ctx-item-desc"),
                            cls="ctx-item-text",
                        ),
                        cls="ctx-item-body",
                    ),
                    cls="ctx-item",
                ),
                cls="ctx-grid",
            ),
            cls="ctx-section",
        )
    )

    # Template editor — load default content server-side to avoid async flicker
    _default_tpl_path = pathlib.Path(__file__).parent / "compliance_report_spec.yaml"
    try:
        _default_tpl_content = _default_tpl_path.read_text(encoding="utf-8")
    except Exception:
        _default_tpl_content = ""
    configure_card_children.append(_template_editor_section(_default_tpl_content))

    # Output format selector
    configure_card_children.append(_output_format_selector())

    # Advanced settings link
    configure_card_children.append(
        Div(
            A(
                "Advanced settings",
                href="#",
                id="studio-advanced-open",
                name="studio-advanced-open",
                cls="app-link studio-advanced-open",
            ),
            cls="advanced-settings-row",
        )
    )

    configure_card_children.append(Div(cls="card-content-spacer"))

    # Generate button
    configure_card_children.append(
        Div(
            Button(
                Span("Generate Documentation", id="generate-btn-label"),
                type="submit",
                id="generate-btn",
                cls="primary generate-btn-full",
            ),
            P("", id="generate-run-message", cls="generate-run-message"),
            cls="card-footer generate-actions",
        )
    )

    left_col_children.append(Div(*configure_card_children, cls="bp-card"))

    # ── Right column: how it works + errors + history ─────────────────────
    right_col_children = [
        Div(H2("Output"), cls="col-header"),
    ]

    _error_children = [studio_errors_panel]
    if compute_env_errors:
        _error_children.append(
            Script(
                json.dumps(compute_env_errors),
                id="studio-compute-env-json",
                type="application/json",
            )
        )

    right_col_children.append(Div(*_error_children, cls="studio-page-insight"))

    right_col_children.append(
        Div(
            Div(
                Div(
                    Span(cls="fa-icon fa-file-lines spec-file-empty-icon"),
                    Span("No documents generated yet.", cls="spec-file-list-empty"),
                    cls="spec-file-empty",
                ),
                id="job-history-content",
            ),
            cls="output-panel",
        )
    )

    return (
        Title("ModelDocs — Domino"),
        Style(fontawesome_faces_css()),
        Script(STUDIO_FONT_BASE_PATCH_JS),
        # Header
        Div(
            Div(
                NotStr(_LOGO_SVG),
                Span("ModelDocs", cls="app-header-title"),
                cls="domino-header-inner",
            ),
            cls="domino-header",
        ),
        # Page
        Div(
            *_render_warnings_banner(_STARTUP_WARNINGS),
            Form(
                Div(
                    Div(*left_col_children, cls="studio-col-main"),
                    Div(*right_col_children, cls="studio-col-right"),
                    cls="studio-grid",
                ),
                id="main-form",
                data_execution_mode="domino",
                data_app_rel="run",
                enctype="multipart/form-data",
            ),
            advanced_modal,
            # Document viewer modal
            Div(
                Div(
                    Div(
                        Span("Generated Document", cls="doc-viewer-title"),
                        Div(
                            Button("Edit", id="doc-viewer-edit-btn", cls="doc-viewer-edit-btn", type="button"),
                            Button("✕", id="doc-viewer-close", cls="doc-viewer-close", type="button"),
                            cls="doc-viewer-header-actions",
                        ),
                        cls="doc-viewer-header",
                    ),
                    Iframe(id="doc-viewer-frame", src="about:blank", cls="doc-viewer-iframe"),
                    Textarea(id="doc-viewer-editor", cls="doc-viewer-editor", style="display:none;", spellcheck="false"),
                    Div(
                        Button("Download Word", cls="doc-dl-btn", type="button"),
                        Button("Download PDF", cls="doc-dl-btn", type="button"),
                        Button("Download Markdown", cls="doc-dl-btn", type="button"),
                        id="doc-viewer-toolbar",
                        cls="doc-viewer-toolbar",
                        style="display:none;",
                    ),
                    cls="doc-viewer-inner",
                ),
                id="doc-viewer-modal",
                cls="doc-viewer-modal",
                style="display:none;",
            ),
            # Template editor + format selector JS
            Script(_TEMPLATE_EDITOR_JS),
            cls="page",
        ),
    )


# ---------------------------------------------------------------------------
# Register route modules
# ---------------------------------------------------------------------------

register_font_assets(rt)
register_api_routes(rt)
register_job_routes(rt)


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------

from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from autodoc.core.config import Settings as _AppSettings

HOST = os.environ.get("APP_HOST", "0.0.0.0")
PORT = int(os.environ.get("APP_PORT", "8888"))

try:
    _app_settings = _AppSettings()
    _cors_origins = _app_settings.cors_origins
    _allowed_hosts = _app_settings.allowed_hosts
except Exception:
    _cors_origins = ["*"]
    _allowed_hosts = ["*"]

app.add_middleware(TrustedHostMiddleware, allowed_hosts=_allowed_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.middleware("http")
async def capture_auth_context(request, call_next):
    from studio.state import auth_context as _auth_context

    forwarded = request.headers.get("authorization")
    _auth_context.set_request_auth_header(forwarded)
    try:
        response = await call_next(request)
    finally:
        _auth_context.set_request_auth_header(None)
    return response


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

@app.on_event("startup")
async def _on_startup():
    import studio.state as _state
    from artifact_layout import init_layout

    init_layout()
    _state._STARTUP_WARNINGS = _validate_environment()


# ---------------------------------------------------------------------------
# Serve
# ---------------------------------------------------------------------------

serve(host=HOST, port=PORT, access_log=False)
