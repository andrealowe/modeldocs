# ModelDocs — Production Readiness Gaps

This document lists what needs to be fixed before ModelDocs can run in production.
The demo mode skeleton is intentional; the gaps below are the delta to a real deployment.

---

## 1. Demo Mode Default

**Problem:** `MODELDOCS_DEMO_MODE` defaults to `"true"` in `studio/scripts.py:1163`.
In demo mode the frontend entirely fakes the job lifecycle — no LLM calls, no code scanning,
no document generation. A mis-configured production deployment would silently serve fake output.

**Fix:** Change the default to `false`. Add a visible startup warning (banner or log line)
if the var is not explicitly set.

---

## 2. Real Job Submission

**Problem:** The web UI calls `_submit_local_job()` (`job_engine.py:270`), which spawns a
local `asyncio` subprocess inside the App container. This is not a Domino job — no isolation,
no hardware tier enforcement, no tracking, and no restart on container crash.

A complete `submit_job()` implementation already exists in `domino_client.py:520` and calls
`POST /v4/jobs/start`, but it is never invoked from the web UI.

**Fix:** Replace `_submit_local_job()` with a call to `domino_client.submit_job()`, passing:
- Command string from `_build_job_command()` (`job_engine.py:177`)
- `overrideHardwareTierId` from `job_request.hardware_tier` (currently accepted but ignored)
- `environmentId` / `environmentRevisionId` from `job_request` (currently accepted but ignored)
- `mainRepoGitRef` for the target project branch

---

## 3. Output Storage — `/tmp/modeldocs`

**Problem:** Job outputs are written to `/tmp/modeldocs/{project_id}/` (`routes_job.py:97`).
`/tmp` is per-container and ephemeral — outputs are lost on any App restart, inaccessible
to other containers, and shared across all projects with no isolation.

**Fix:** Write outputs to a real Domino Dataset mount path. The app already has
`domino_datasets.list_datasets()` wired; the dataset path should be resolved from
`DOMINO_DATASETS_DIR` and scoped per project. The `AUTODOC_DATASET_NAME` constant
(`dataset_manager.py`) already names the target dataset.

---

## 4. Code Root Resolution

**Problem:** When `browse_code` returns no repositories, `code_root_options_from_browse_response()`
(`domino_client.py:214`) falls back to `/mnt/code` — the App's own source code, not the
target project's. In a deployed Extension the App and the user's project run in different
containers, so `/mnt/code` will always be wrong.

**Fix:** Remove the `/mnt/code` and `/mnt` fallbacks. Require a valid `browseCode` API
response. Fail with a user-facing error if no repository locations are returned.

---

## 5. MLflow / Experiments Context

**Problem:** `MLFLOW_TRACKING_URI` is never validated at startup. If unset, MLflow defaults
to a local file store rather than the Domino-managed tracking server, so experiment scans
silently return nothing.

`DOMINO_PROJECT_ID` is read from the container environment to filter MLflow artifacts
(`artifact_scanner.py:105`), but there is no mechanism to target a *different* project's
MLflow data from the App container.

**Fix:**
- Validate `MLFLOW_TRACKING_URI` at startup; log a warning (or block job submission) if
  it is not set to a reachable URI.
- Pass the target `projectId` through to the job command so the scanner filters by the
  correct project, not the App's own `DOMINO_PROJECT_ID`.

---

## 6. Environment Variable Validation

**Problem:** No startup check ensures required env vars are present. The app starts and
accepts job submissions even when key variables are missing; failures only surface deep
in job execution.

Variables that need explicit startup validation:

| Variable | Used for |
|---|---|
| `DOMINO_API_HOST` | All Domino API calls |
| `DOMINO_API_PROXY` | API proxy in App container |
| `DOMINO_PROJECT_ID` | MLflow filtering (must match target project) |
| `DOMINO_DATASETS_DIR` | Job history database and output storage |
| `MLFLOW_TRACKING_URI` | Experiment scanning |
| `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` | LLM calls (one required) |
| `MODELDOCS_DEMO_MODE` | Should be explicit, not defaulted |

**Fix:** Add validation in `_on_startup()` (`web_app_studio.py:1052`) that checks required
vars and surfaces missing ones in the existing warnings banner.

---

## 7. Multi-Tenant Isolation

**Problem:** Job history is stored in a SQLite database at
`{DOMINO_DATASETS_DIR}/{DOMINO_PROJECT_NAME}/modeldocs.db` (`domino_job_store.py`).
In a shared deployment (one App serving multiple projects), all users hit the same process
and the database is scoped only by `owner_id` + `project_id` query params — values that
come from the client and are not server-verified beyond a JWT check.

**Fix:** Verify `project_id` membership server-side before allowing reads/writes.
Consider one database file per project rather than a shared file with row-level isolation.

---

## 8. Job Progress and Status Polling

**Problem:** In the real-job path, job status is tracked by a background `asyncio` task
(`_drain_process()`, `job_engine.py:250`) that watches the subprocess. When replaced with
a real Domino job, this mechanism no longer applies. The `/job-history` endpoint would
need to poll the Domino Jobs API (`GET /v4/jobs/{run_id}/status`) to get live status.

`domino_client.py` already has `get_job_status()` and related helpers; they just need
to be called from `domino_job_store._refresh_active_rows()`.

---

## 9. Inline Spec Written to /tmp Without Validation

**Problem:** When a user pastes a spec directly into the UI, it is written to
`/tmp/_inline_spec_{timestamp}.yaml` (`routes_job.py:113`) without schema validation.
An invalid YAML spec will only fail deep in the job subprocess, with no user-friendly error.

**Fix:** Parse and validate the YAML against the `DocumentSpec` model before writing to
disk. Return a 400 with the validation error message.

---

## 10. Compliance Template Wiring

**Problem:** The compliance report template (`compliance_report_spec.yaml`) is loaded
client-side and submitted as inline YAML. There is no server-side enforcement that the
submitted spec matches the template's required structure (sections, rendering rules, hints).
A user could submit a malformed or stripped-down spec and get a degraded report with no
warning.

**Fix:** After fixing inline spec validation (gap 9), add a check that required section
names from the compliance template are present in the submitted spec.

---

## Summary

| Gap | Effort | Blocking |
|---|---|---|
| Demo mode default | Low | Yes |
| Real job submission via Domino API | High | Yes |
| Output storage (dataset, not /tmp) | High | Yes |
| Code root resolution (no /mnt/code fallback) | Medium | Yes |
| MLflow URI validation + project targeting | Medium | Yes |
| Env var startup validation | Low | No |
| Multi-tenant isolation | Medium | No |
| Job status polling from Domino API | Medium | No |
| Inline spec validation | Low | No |
| Compliance template enforcement | Low | No |
