"""API routes: hardware tiers, datasets, etc."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Optional

from starlette.requests import Request
from starlette.responses import FileResponse, Response

from autodoc.core.models import DocumentSpec
from authorization import require_project_write

# Demo files live inside the package (studio/demo/) so they're always present
# regardless of which directory the app process started from.
_DEMO_DIR = Path(__file__).resolve().parent / "demo"

from .state import (
    _resolve_request_project_id,
    domino_client,
    domino_datasets,
)

logger = logging.getLogger(__name__)


def sanitize_dataset_subpath(raw: Optional[str]) -> str:
    if raw is None or not str(raw).strip():
        return ""
    parts: list[str] = []
    for seg in str(raw).replace("\\", "/").strip().strip("/").split("/"):
        if not seg or seg == ".":
            continue
        if seg == "..":
            raise ValueError("Invalid relativeDir")
        parts.append(seg)
    return "/".join(parts)


def register_api_routes(rt):
    """Register all /api/* routes on the given rt decorator."""

    async def api_hardware_tiers(req: Request):
        project_id = _resolve_request_project_id(req)
        tiers = domino_client.list_hardware_tiers(project_id=project_id)
        default_tier = domino_client.get_project_default_tier()
        result = []
        for t in tiers:
            tid = t.get("id", "")
            tname = t.get("name") or tid
            label = t.get("option_label") or tname
            is_default = t.get("isDefault", False) or tid == default_tier
            result.append({"id": tid, "label": label, "isDefault": is_default})
        return Response(json.dumps(result), media_type="application/json")

    rt("/api/hardware-tiers")(api_hardware_tiers)

    async def api_environment_revisions(req: Request):
        env_id = (req.query_params.get("environmentId") or "").strip()
        if not env_id:
            return Response(json.dumps([]), media_type="application/json")
        revs = domino_client.list_environment_revisions(env_id)
        result = []
        for i, r in enumerate(revs):
            rid = r.get("id", "")
            label = r.get("option_label") or rid
            result.append({"id": rid, "label": label, "isDefault": i == 0})
        return Response(json.dumps(result), media_type="application/json")

    rt("/api/environment-revisions")(api_environment_revisions)

    async def api_datasets(req: Request):
        """List writable datasets for the project.

        Each item includes datasetPath from Domino's datasets-v2 list response
        (see domino_datasets.list_datasets; includeStorageInfo on that API).
        """
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        try:
            datasets = domino_datasets.list_datasets(pid)
            return Response(json.dumps(datasets), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/datasets")(api_datasets)

    async def api_dataset_files(req: Request):
        """Browse files in a dataset (directories + yaml only)."""
        dataset_id = req.query_params.get("datasetId", "")
        snapshot_id = req.query_params.get("snapshotId", "")
        path = req.query_params.get("path", "")
        pid = _resolve_request_project_id(req)
        require_project_write(pid)

        if not dataset_id:
            return Response(
                json.dumps({"error": "datasetId required"}),
                status_code=400,
                media_type="application/json",
            )

        if not snapshot_id:
            snapshot_id = domino_datasets.get_rw_snapshot_id(dataset_id)
        if not snapshot_id:
            return Response(
                json.dumps({"error": "Could not resolve snapshot for dataset"}),
                status_code=400,
                media_type="application/json",
            )

        try:
            files = domino_datasets.list_files(snapshot_id, path)
            return Response(json.dumps(files), media_type="application/json")
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/dataset-files")(api_dataset_files)

    async def api_upload_spec_to_dataset(req: Request):
        """Upload a spec file to a dataset."""
        pid = _resolve_request_project_id(req)
        require_project_write(pid)
        form = await req.form()
        file_upload = form.get("file")
        dataset_id = form.get("datasetId", "")

        if not file_upload or not hasattr(file_upload, "read"):
            return Response(
                json.dumps({"error": "file is required"}),
                status_code=400,
                media_type="application/json",
            )
        if not dataset_id:
            return Response(
                json.dumps({"error": "datasetId is required"}),
                status_code=400,
                media_type="application/json",
            )

        raw_filename = getattr(file_upload, "filename", "spec.yaml")
        filename = raw_filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1] or "spec.yaml"
        content = await file_upload.read()

        try:
            rel_dir = sanitize_dataset_subpath(
                str(form.get("relativeDir", "") or "").strip()
            )
        except ValueError as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=400,
                media_type="application/json",
            )

        fn_low = filename.lower()
        if fn_low.endswith((".yaml", ".yml")):
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                return Response(
                    json.dumps({
                        "error": "Spec file must be valid UTF-8",
                        "valid": False,
                        "errors": ["File is not valid UTF-8"],
                    }),
                    status_code=400,
                    media_type="application/json",
                )
            val_errors = DocumentSpec.validate_spec(text)
            if val_errors:
                return Response(
                    json.dumps({
                        "error": "Spec validation failed",
                        "valid": False,
                        "errors": val_errors,
                    }),
                    status_code=400,
                    media_type="application/json",
                )

        try:
            from dataset_manager import DatasetManager
            upload_path = f"{rel_dir}/{filename}" if rel_dir else filename
            DatasetManager.write_file(dataset_id, upload_path, content)
            return Response(
                json.dumps({
                    "path": upload_path,
                    "fileName": filename,
                    "valid": True,
                }),
                media_type="application/json",
            )
        except Exception as exc:
            return Response(
                json.dumps({"error": str(exc)}),
                status_code=500,
                media_type="application/json",
            )

    rt("/api/upload-spec-to-dataset")(api_upload_spec_to_dataset)

    def api_download_template():
        template_path = Path(__file__).resolve().parent.parent / "doc_spec.yaml"
        if not template_path.exists():
            return Response("Template not found", status_code=404)
        return FileResponse(
            str(template_path),
            media_type="application/x-yaml",
            filename="doc_spec_template.yaml",
        )

    rt("/api/download-template")(api_download_template)

    _BUILTIN_TEMPLATES = {
        "compliance": ("compliance_report_spec.yaml", "compliance_report_spec.yaml"),
        "default": ("doc_spec.yaml", "doc_spec_template.yaml"),
    }

    async def api_template_content(req: Request):
        """Return the YAML text of a named built-in template."""
        name = req.query_params.get("name", "compliance").strip().lower()
        entry = _BUILTIN_TEMPLATES.get(name)
        if not entry:
            return Response(
                "Unknown template name",
                status_code=404,
                media_type="text/plain",
            )
        src_file, _ = entry
        tpl_path = Path(__file__).resolve().parent.parent / src_file
        if not tpl_path.exists():
            return Response("Template file not found", status_code=404, media_type="text/plain")
        return Response(tpl_path.read_text(encoding="utf-8"), media_type="text/plain")

    rt("/api/template-content")(api_template_content)

    async def api_download_compliance_template():
        tpl_path = Path(__file__).resolve().parent.parent / "compliance_report_spec.yaml"
        if not tpl_path.exists():
            return Response("Template not found", status_code=404)
        return FileResponse(
            str(tpl_path),
            media_type="application/x-yaml",
            filename="compliance_report_spec.yaml",
        )

    rt("/api/download-compliance-template")(api_download_compliance_template)

    # ── Demo output files — served from uploads/ for preview/demo mode ───

    _DEMO_DOCX = _DEMO_DIR / "NBT-CR-EL-007_Compliance_Report_v7_0.docx"
    _DEMO_IPYNB = _DEMO_DIR / "NBT-CR-EL-007_Compliance_Report.ipynb"
    logger.info("Demo files: docx=%s (exists=%s)  ipynb=%s (exists=%s)",
                _DEMO_DOCX, _DEMO_DOCX.exists(), _DEMO_IPYNB, _DEMO_IPYNB.exists())

    async def demo_report_docx():
        if not _DEMO_DOCX.exists():
            logger.error("Demo docx not found at %s", _DEMO_DOCX)
            return Response(f"Demo file not found: {_DEMO_DOCX}", status_code=404)
        return FileResponse(
            str(_DEMO_DOCX),
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename=_DEMO_DOCX.name,
        )

    rt("/demo/report-docx")(demo_report_docx)

    async def demo_report_ipynb():
        if not _DEMO_IPYNB.exists():
            logger.error("Demo ipynb not found at %s", _DEMO_IPYNB)
            return Response(f"Demo file not found: {_DEMO_IPYNB}", status_code=404)
        return FileResponse(
            str(_DEMO_IPYNB),
            media_type="application/x-ipynb+json",
            filename=_DEMO_IPYNB.name,
        )

    rt("/demo/report-ipynb")(demo_report_ipynb)

    async def demo_report_render(req: Request):
        """Render the pre-built demo .docx as HTML via mammoth."""
        if not _DEMO_DOCX.exists():
            logger.error("Demo docx not found at %s", _DEMO_DOCX)
            return Response(f"Demo file not found: {_DEMO_DOCX}", status_code=404)
        try:
            import mammoth
            with open(_DEMO_DOCX, "rb") as f:
                result = mammoth.convert_to_html(f)
            body_html = result.value
        except Exception as exc:
            logger.exception("mammoth conversion failed for demo docx")
            return Response(f"Could not render document: {exc}", status_code=500, media_type="text/plain")

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1.5rem 3rem; color: #1a1a1a; line-height: 1.65; font-size: 14px; font-weight: normal; }}
  h1, h2, h3 {{ font-family: inherit; color: #1F4E79; font-weight: 700; }}
  h1 {{ font-size: 1.35rem; border-bottom: 2px solid #1F4E79; padding-bottom: .4rem; margin-top: 2rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 1.5rem; color: #2E74B5; }}
  h3 {{ font-size: 1rem; margin-top: 1.2rem; }}
  p {{ margin: .5rem 0 .9rem; font-weight: normal; color: #1a1a1a; }}
  p strong, p b, p span {{ font-weight: normal !important; color: #1a1a1a !important; }}
  td p strong, td p b, th p strong, th p b {{ font-weight: 600 !important; color: inherit !important; }}
  em, i {{ font-style: italic; font-weight: normal; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .875rem; }}
  th {{ background: #1F4E79; color: #fff; font-weight: 600; padding: .4rem .7rem; text-align: left; }}
  td {{ border: 1px solid #ddd; padding: .4rem .7rem; color: #1a1a1a; }}
  tr:nth-child(even) td {{ background: #f7f8fc; }}
  ul, ol {{ margin: .4rem 0 .8rem 1.2rem; padding: 0; }}
  li {{ margin-bottom: .3rem; font-weight: normal; }}
  li strong, li b {{ font-weight: normal !important; color: #1a1a1a !important; }}
  img {{ max-width: 100%; display: block; margin: 1rem auto; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""
        return Response(html, media_type="text/html")

    rt("/demo/report-render")(demo_report_render)

    async def job_render(req: Request):
        """Convert the most recently generated .docx in a dataset to HTML for in-app display."""
        dataset_path = req.query_params.get("dataset_path", "").strip()
        if not dataset_path:
            return Response("dataset_path is required", status_code=400)

        docs_dir = Path(dataset_path) / "docs"
        if not docs_dir.exists():
            return Response("No documents found yet.", status_code=404, media_type="text/plain")

        docx_files = sorted(docs_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not docx_files:
            return Response("No documents found yet.", status_code=404, media_type="text/plain")

        docx_path = docx_files[0]
        try:
            import mammoth
            with open(docx_path, "rb") as f:
                result = mammoth.convert_to_html(f)
            body_html = result.value
        except Exception as exc:
            logger.exception("mammoth conversion failed for %s", docx_path)
            return Response(f"Could not render document: {exc}", status_code=500, media_type="text/plain")

        html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 860px; margin: 2rem auto; padding: 0 1.5rem 3rem; color: #1a1a1a; line-height: 1.65; font-size: 14px; font-weight: normal; }}
  h1, h2, h3 {{ font-family: inherit; color: #1F4E79; font-weight: 700; }}
  h1 {{ font-size: 1.35rem; border-bottom: 2px solid #1F4E79; padding-bottom: .4rem; margin-top: 2rem; }}
  h2 {{ font-size: 1.1rem; margin-top: 1.5rem; color: #2E74B5; }}
  h3 {{ font-size: 1rem; margin-top: 1.2rem; }}
  p {{ margin: .5rem 0 .9rem; font-weight: normal; color: #1a1a1a; }}
  p strong, p b, p span {{ font-weight: normal !important; color: #1a1a1a !important; }}
  td p strong, td p b, th p strong, th p b {{ font-weight: 600 !important; color: inherit !important; }}
  em, i {{ font-style: italic; font-weight: normal; color: #555; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; font-size: .875rem; }}
  th {{ background: #1F4E79; color: #fff; font-weight: 600; padding: .4rem .7rem; text-align: left; }}
  td {{ border: 1px solid #ddd; padding: .4rem .7rem; color: #1a1a1a; }}
  tr:nth-child(even) td {{ background: #f7f8fc; }}
  ul, ol {{ margin: .4rem 0 .8rem 1.2rem; padding: 0; }}
  li {{ margin-bottom: .3rem; font-weight: normal; }}
  li strong, li b {{ font-weight: normal !important; color: #1a1a1a !important; }}
  img {{ max-width: 100%; display: block; margin: 1rem auto; }}
</style>
</head>
<body>
{body_html}
</body>
</html>"""

        return Response(html, media_type="text/html")

    rt("/job-render")(job_render)

    async def job_notebook(req: Request):
        """Download the most recently generated .ipynb from a dataset."""
        dataset_path = req.query_params.get("dataset_path", "").strip()
        if not dataset_path:
            return Response("dataset_path is required", status_code=400)
        docs_dir = Path(dataset_path) / "docs"
        if not docs_dir.exists():
            return Response("No notebooks found yet.", status_code=404)
        ipynb_files = sorted(docs_dir.glob("*.ipynb"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not ipynb_files:
            return Response("No notebooks found yet.", status_code=404)
        return FileResponse(
            str(ipynb_files[0]),
            media_type="application/x-ipynb+json",
            filename=ipynb_files[0].name,
        )

    rt("/job-notebook")(job_notebook)

    async def job_markdown(req: Request):
        """Return the most recently generated report as Markdown text."""
        dataset_path = req.query_params.get("dataset_path", "").strip()
        if not dataset_path:
            return Response("dataset_path is required", status_code=400)
        docs_dir = Path(dataset_path) / "docs"
        if not docs_dir.exists():
            return Response("No documents found yet.", status_code=404, media_type="text/plain")
        docx_files = sorted(docs_dir.glob("*.docx"), key=lambda p: p.stat().st_mtime, reverse=True)
        if not docx_files:
            return Response("No documents found yet.", status_code=404, media_type="text/plain")
        try:
            import mammoth
            with open(docx_files[0], "rb") as f:
                result = mammoth.convert_to_markdown(f)
            return Response(result.value, media_type="text/plain; charset=utf-8")
        except Exception as exc:
            logger.exception("mammoth markdown conversion failed for %s", docx_files[0])
            return Response(f"Could not convert document: {exc}", status_code=500, media_type="text/plain")

    rt("/job-markdown")(job_markdown)

    async def api_code_root_options(req: Request):
        pid = (_resolve_request_project_id(req) or "").strip()

        def _error_payload(reason: str) -> dict:
            return {
                "isGitBasedProject": None,
                "defaultRoot": "",
                "options": [],
                "error": reason,
            }

        if not pid:
            return Response(
                json.dumps(_error_payload("missing_project_id")),
                media_type="application/json",
            )
        info = domino_client.resolve_project(pid)
        if not info:
            return Response(
                json.dumps(_error_payload("project_resolve_failed")),
                media_type="application/json",
            )
        try:
            raw = domino_client.browse_code(info.owner_username, info.name, path_string="")
            payload = domino_client.code_root_options_from_browse_response(raw)
            payload["error"] = None
            return Response(json.dumps(payload), media_type="application/json")
        except Exception as exc:
            detail = str(exc)
            if hasattr(exc, "response") and exc.response is not None:
                try:
                    detail = f"{exc} body={exc.response.text[:1500]!r}"
                except Exception:
                    pass
            logger.warning("browseCode for code-root-options failed: %s", detail)
            return Response(
                json.dumps(_error_payload("browse_code_failed")),
                media_type="application/json",
            )

    rt("/api/code-root-options")(api_code_root_options)
