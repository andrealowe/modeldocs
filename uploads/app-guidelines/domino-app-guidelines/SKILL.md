---
name: domino-app-guidelines
description: Guidance and reference material for building apps and Domino Extensions that run on the Domino Data Lab platform. Use this skill whenever the user wants to build, scaffold, design, style, or debug a Domino app or Domino Extension — including FastAPI back-ends with Ant Design front-ends loaded via CDN, Domino-themed UI, calls to the Domino Platform (v4) or Governance APIs, or deployment via `app.sh`. Also use when the user asks about Domino design principles, UX writing, Domino color tokens, typography, Storybook components, the Domino top-nav/logo, or anything about making an app "look like Domino." Trigger even when the user doesn't say the word "skill" — phrases like "build me a Domino app", "I need an extension for my project", "Domino-style dashboard", or "call the Domino jobs API from my app" should all activate this skill.
---

# Domino App Guidelines

This skill bundles everything needed to build apps and Extensions that run on the Domino Data Lab platform and match Domino's design system. It pulls together the engineering stack guidance, the UX/design guidelines, the Domino logo, and the OpenAPI specs for the two main Domino API surfaces.

## What counts as a "Domino app" here

Two closely related things:

1. **Domino apps** — a Python back-end (FastAPI) with a lightweight HTML/CSS/JS front-end, deployed inside a Domino project via `app.sh` and run behind Domino's nginx proxy on port 8888.
2. **Domino Extensions** — a flavor of Domino app that appears as a link/surface inside other Domino entities (project sidebar, dataset page, model details, etc.) and receives context via URL parameters. They use "Enhanced Identity Propagation" and still call the Domino API with a bearer token.

The two overlap heavily — same stack, same theming, same APIs. Extensions differ mainly in how they get their context (URL params) and how they are deployed/surfaced inside Domino.

## How to use this skill

Always start by reading `references/how-to-build-apps.md` before scaffolding or editing a Domino app — it has the concrete specs (CDN tags, script load order, `ConfigProvider` theme object, auth pattern, env vars, nginx-proxy gotchas, `app.sh`). Treat that file as the build recipe.

When the work touches UI, UX copy, color choices, button hierarchy, layout, or anything visual, also read `references/design-principles.md` (or the relevant section of it — it's long; use the table of contents below). This is the Domino Design System in one file: UX principles, color tokens, typography, spacing, components, accessibility.

When the work involves calling Domino APIs, search the two OpenAPI specs rather than reading them end-to-end — both are large JSON files intended for grep/lookup, not linear reading:

- `references/swagger.json` — **Domino Platform API v4** (754 paths). Base path `/v4/`. Covers Jobs, Projects, Users, Workspaces, Model Products (Apps), Datasets, and more. Also contains the Beta Apps API under `/api/apps/beta/` — this is the only API that distinguishes normal apps from agent apps via the `configurationType` field.
- `references/governance_swagger.json` — **Domino Governance API v1.0** (36 paths). Base path `/api/governance/v1/`. Covers bundles, policies, approvals, evidence.

To find an endpoint, grep the spec for the resource name (e.g., `"projects"`, `"bundles"`, `"modelProducts"`) or the HTTP path fragment, then read the surrounding JSON to get parameters and response shapes. Don't try to load the whole file into context.

## Reference files at a glance

| File | What it's for | When to load |
|---|---|---|
| `references/how-to-build-apps.md` | Build recipe — stack, theming, auth, env vars, Extensions, `app.sh` | Any app scaffolding, setup, or deployment question |
| `references/design-principles.md` | Domino Design System — UX principles, colors, typography, buttons, tables, forms, writing | Anything UI/UX/visual/copy-related |
| `references/swagger.json` | Platform API v4 + Beta Apps API | When the app needs to read/write Domino entities |
| `references/governance_swagger.json` | Governance API v1 | When the app interacts with bundles/policies/approvals |
| `assets/domino-logo.svg` | Official Domino logo | Drop into the app's top navigation bar (render at 32px height) |

## Quick-reference: the things people get wrong most often

These are the sharp edges that come up repeatedly — skim them before writing code, then go to `how-to-build-apps.md` for the full context.

**CDN vs. vendored dependencies.** Domino environments sometimes block external CDNs. Download React, Ant Design, dayjs, Highcharts etc. into `static/vendor/` at setup time and reference them locally. When `<script>` tags silently return HTML error pages instead of JS, you get `undefined` errors at runtime — vendoring avoids that whole class of problem.

**Script load order.** Ant Design calls `dayjs.extend()` during initialization, so `dayjs.min.js` must load before `antd.min.js`. Put all `<script>` tags at the end of `<body>` in explicit dependency order (React → dayjs → antd → highcharts → your app code).

**Absolute URLs break inside Domino's nginx proxy.** The proxy rewrites the root URL, so `fetch('/api/foo')` won't land where you expect. Use relative paths or construct URLs dynamically from `window.location`.

**Re-acquire the access token on every API call.** The token from `http://localhost:8899/access-token` expires very quickly. Don't cache it — fetch it fresh each call. For local dev, honor `API_KEY_OVERRIDE` env var and send `X-Domino-Api-Key` instead.

**Three API base paths, easy to confuse:**
- Platform v4 → `{DOMINO_API_HOST}/v4/...` (no `/api/` prefix)
- Governance → `{DOMINO_API_HOST}/api/governance/v1/...`
- Beta Apps → `{DOMINO_API_HOST}/api/apps/beta/...`

**Distinguishing normal apps from agent apps** requires the Beta Apps API's `configurationType` field (`STANDARD` vs `AISYSTEM`). The v4 `/modelProducts` endpoint returns `appExtension.appType: "Shiny"` for everything, which is not useful for this. The Beta Apps API also doesn't support server-side filtering by `configurationType` — filter client-side.

**Design system minimums:** one Primary button per screen (solid fill, `#3B3BD3`). Everything else is Secondary / Tertiary / Link. Use Inter (or fall back to Lato → Helvetica → Arial). Minimum touch targets 24×24 desktop / 44×44 mobile. Body text ≥14px, 16px preferred. Tables: truncated cells get tooltips showing full content.

**Top nav bar specs:** 44px height, `#2E2E38` background, white text, logo at 32px height from `assets/domino-logo.svg`.

**Running the app:** `uvicorn app:app --host 0.0.0.0 --port 8888` from `app.sh`. Errors to stdout so they show up in Domino's logs. Avoid inline CSS/JS — use static files so debugging and caching work.

## Theme object (drop-in)

For a Domino-branded Ant Design app, wrap everything in `ConfigProvider` with this theme. Full explanation and component-level overrides are in `how-to-build-apps.md`:

```javascript
const dominoTheme = {
  token: {
    colorPrimary: '#543FDE', colorPrimaryHover: '#3B23D1', colorPrimaryActive: '#311EAE',
    colorText: '#2E2E38', colorTextSecondary: '#65657B', colorTextTertiary: '#8F8FA3',
    colorSuccess: '#28A464', colorWarning: '#CCB718', colorError: '#C20A29', colorInfo: '#0070CC',
    colorBgContainer: '#FFFFFF', colorBgLayout: '#FAFAFA', colorBorder: '#E0E0E0',
    fontFamily: 'Inter, Lato, Helvetica Neue, Helvetica, Arial, sans-serif',
    fontSize: 14, borderRadius: 4, borderRadiusLG: 8,
  },
  components: {
    Button: { primaryShadow: 'none', defaultShadow: 'none' },
    Table: { headerBg: '#FAFAFA', rowHoverBg: '#F5F5F5' },
  },
};
```

Two notes about colors: the theme above comes from the engineering guide (used by app developers via Ant Design). The UX design system in `design-principles.md` uses a slightly different tokens table centered on `#3B3BD3` as the primary blue for buttons. When in doubt, follow `design-principles.md` for anything user-facing and visual, and `how-to-build-apps.md` for the working `ConfigProvider` config. The Storybook (link inside the references) is the ultimate source of truth if the two disagree.

## Suggested workflow

1. Read `how-to-build-apps.md` to get the stack and auth pattern right.
2. Scaffold the FastAPI app, `app.sh`, and an `index.html` that vendors its JS/CSS locally.
3. Wrap the React root in `ConfigProvider` with the Domino theme.
4. Build the nav bar using `assets/domino-logo.svg`.
5. For each API call, grep the relevant swagger to confirm the exact path, method, params, and response shape — don't guess.
6. Before declaring the UI done, walk the relevant sections of `design-principles.md` (button hierarchy, empty states, error copy, table behavior, accessibility) to catch common issues.
